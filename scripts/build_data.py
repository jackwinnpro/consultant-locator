"""Process consultants + orders Excel exports, join, filter to active, geocode.

Reads Flight exports from data/raw/:
  - "All Consultants zip codes*.xlsx"
  - "All Orders_KK*.xlsx"

Writes:
  - data/consultants.json  (active consultants with lat/lng)
  - data/us_zips.json      (nationwide zip → [lat, lng] lookup for the artifact)

"Active" = 3+ distinct orders in the past 6 months.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import zipcodes

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_DIR = REPO_ROOT / "data"

MIN_ORDERS_6MO = 3
LOOKBACK_DAYS = 183  # ~6 months


def find_latest(pattern: str) -> Path:
    """Return the most-recently-modified file matching pattern in data/raw/."""
    matches = sorted(RAW_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No files matching {pattern!r} in {RAW_DIR}")
    return matches[0]


def load_consultants(path: Path) -> pd.DataFrame:
    """Load the Grid sheet of the consultants Excel export. Header is on row 3 (index 2)."""
    df = pd.read_excel(path, engine="calamine", sheet_name="Grid", header=2)
    df.columns = [
        "person_id", "first", "last", "company", "phone", "email",
        "street1", "street2", "city", "state", "zip", "country",
        "join_date", "dob", "type",
    ]
    return df


def load_orders(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, engine="calamine", sheet_name="Grid")
    df["CommissionDate"] = pd.to_datetime(df["Commission Date"], errors="coerce")
    return df


def active_consultants(orders: pd.DataFrame, today: date) -> pd.DataFrame:
    cutoff = datetime.combine(today, datetime.min.time()) - timedelta(days=LOOKBACK_DAYS)
    recent = orders[orders["CommissionDate"] >= cutoff].copy()

    counts = (
        recent.groupby("CommissionPersonDisplayID")["Order ID"]
        .nunique().reset_index().rename(columns={"Order ID": "order_count"})
    )
    last = (
        recent.groupby("CommissionPersonDisplayID")["CommissionDate"]
        .max().reset_index().rename(columns={"CommissionDate": "last_order_date"})
    )
    active = counts[counts["order_count"] >= MIN_ORDERS_6MO].merge(last, on="CommissionPersonDisplayID")
    active["person_id"] = active["CommissionPersonDisplayID"].astype(str)
    return active


def clean_zip(z) -> str | None:
    if pd.isna(z):
        return None
    s = str(z).strip()
    if "-" in s:
        s = s.split("-")[0]
    if "." in s:
        s = s.split(".")[0]
    s = s.zfill(5)[:5]
    return s if s.isdigit() else None


def compose_record(row, zip_cache: dict) -> dict | None:
    z = row["zip5"]
    ll = zip_cache.get(z)
    if not ll:
        return None
    name = f"{row['first'] or ''} {row['last'] or ''}".strip()
    company = row["company"] if pd.notna(row["company"]) else ""
    street = str(row["street1"]) if pd.notna(row["street1"]) else ""
    s2 = row["street2"]
    if pd.notna(s2) and str(s2).strip() not in ("", "0"):
        street = (street + " " + str(s2)).strip()
    city = str(row["city"]) if pd.notna(row["city"]) else ""
    state = str(row["state"]) if pd.notna(row["state"]) else ""
    last_dt = row["last_order_date"]
    last_str = last_dt.strftime("%Y-%m-%d") if pd.notna(last_dt) else ""
    ctype = str(row["type"]) if pd.notna(row["type"]) else ""
    return {
        "name": name,
        "company": str(company).strip() if company else "",
        "street": street,
        "city": city,
        "state": state,
        "zip": z,
        "lat": ll[0],
        "lng": ll[1],
        "orders": int(row["order_count"]),
        "last": last_str,
        "type": ctype,
    }


def build_us_zip_lookup() -> dict:
    out = {}
    for z in zipcodes.list_all():
        zc, lat, lng = z.get("zip_code"), z.get("lat"), z.get("long")
        if zc and lat and lng and z.get("active"):
            try:
                out[zc] = [round(float(lat), 3), round(float(lng), 3)]
            except ValueError:
                pass
    return out


def main() -> None:
    today = date.today()
    print(f"Building against today = {today.isoformat()}")

    consultants_xlsx = find_latest("All Consultants zip codes*.xlsx")
    orders_xlsx = find_latest("All Orders_KK*.xlsx")
    print(f"Consultants: {consultants_xlsx.name}")
    print(f"Orders:      {orders_xlsx.name}")

    cons = load_consultants(consultants_xlsx)
    orders = load_orders(orders_xlsx)
    print(f"  consultants loaded: {len(cons):,}")
    print(f"  orders loaded:      {len(orders):,}")

    active = active_consultants(orders, today)
    print(f"  active (>={MIN_ORDERS_6MO} orders/6mo): {len(active):,}")

    cons["person_id_str"] = cons["person_id"].astype(str)
    joined = cons.merge(active, left_on="person_id_str", right_on="person_id",
                        how="inner", suffixes=("", "_o"))
    joined["zip5"] = joined["zip"].apply(clean_zip)
    print(f"  joined with address: {len(joined):,}")

    # Per-consultant zip lookup (cached)
    zip_cache: dict[str, tuple] = {}
    for z in joined["zip5"].dropna().unique():
        try:
            r = zipcodes.matching(z)
            if r:
                zip_cache[z] = (float(r[0]["lat"]), float(r[0]["long"]))
        except Exception:
            pass

    records = []
    dropped = 0
    for _, row in joined.iterrows():
        rec = compose_record(row, zip_cache)
        if rec is None:
            dropped += 1
        else:
            records.append(rec)
    print(f"  geocoded: {len(records):,}  (dropped {dropped} with unresolvable zip)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "consultants.json", "w") as f:
        json.dump(records, f, separators=(",", ":"))
    print(f"  wrote consultants.json ({os.path.getsize(OUT_DIR / 'consultants.json'):,} bytes)")

    us_zips = build_us_zip_lookup()
    with open(OUT_DIR / "us_zips.json", "w") as f:
        json.dump(us_zips, f, separators=(",", ":"))
    print(f"  wrote us_zips.json   ({len(us_zips):,} entries, "
          f"{os.path.getsize(OUT_DIR / 'us_zips.json'):,} bytes)")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print(f"Drop Flight exports into {RAW_DIR}/", file=sys.stderr)
        sys.exit(1)
