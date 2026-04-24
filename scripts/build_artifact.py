"""Read data/consultants.json + data/us_zips.json, render src/template.html into docs/index.html.

Data shrinkage (so the page stays lean):
  - Aggregate us_zips → ~933 zip3-prefix centroids (~30mi accuracy) instead of 41,695 full zips
  - Consultants rendered as array-of-arrays with 8 fields (no street, no lat/lng)
  - lat/lng derived client-side from ZIP3_INDEX[zip.slice(0, 3)]
  - type encoded as 0=Ambassador, 1=Professional

Result: ~85KB total HTML containing ~900 consultants.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
TEMPLATE = REPO_ROOT / "src" / "template.html"
OUT = REPO_ROOT / "docs" / "index.html"

STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN",
    "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "District of Columbia": "DC", "Puerto Rico": "PR",
}


def aggregate_zip3(us_zips: dict) -> dict:
    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for z, (lat, lng) in us_zips.items():
        groups[z[:3]].append((lat, lng))
    return {
        z3: [round(sum(c[0] for c in pts) / len(pts), 2),
             round(sum(c[1] for c in pts) / len(pts), 2)]
        for z3, pts in groups.items()
    }


def type_code(t: str) -> int:
    if not t:
        return 0
    return 1 if t.lower().startswith("p") else 0


def normalize_state(s: str) -> str:
    if not s:
        return ""
    if s in STATE_ABBR:
        return STATE_ABBR[s]
    if len(s) > 2:
        return STATE_ABBR.get(s.title(), s)
    return s


def days_ago(s: str, today: date) -> int:
    if not s:
        return -1
    try:
        y, m, d = map(int, s.split("-"))
        return (today - date(y, m, d)).days
    except Exception:
        return -1


def compact_consultants(consultants: list, today: date) -> str:
    rows = []
    for c in consultants:
        rows.append([
            c["name"],
            c.get("company") or "",
            c["city"],
            normalize_state(c.get("state", "")),
            c["zip"],
            c["orders"],
            days_ago(c.get("last", ""), today),
            type_code(c.get("type", "")),
        ])
    # Newline-separated for readability + diff-friendliness
    return "[\n" + ",\n".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False)
                              for r in rows) + "\n]"


def main() -> None:
    today = date.today()
    print(f"Building artifact as of {today.isoformat()}")

    with open(DATA_DIR / "consultants.json") as f:
        consultants = json.load(f)
    with open(DATA_DIR / "us_zips.json") as f:
        us_zips = json.load(f)

    zip3 = aggregate_zip3(us_zips)
    zip3_json = json.dumps({k: zip3[k] for k in sorted(zip3)}, separators=(",", ":"))
    print(f"  ZIP3 index: {len(zip3):,} entries, {len(zip3_json):,} bytes")

    cons_json = compact_consultants(consultants, today)
    print(f"  Consultants: {len(consultants):,} records, {len(cons_json):,} bytes")

    today_ms = f"Date.UTC({today.year}, {today.month - 1}, {today.day})"
    updated = today.strftime("%B %-d, %Y") if os.name != "nt" else today.strftime("%B %#d, %Y")

    html = TEMPLATE.read_text()
    html = html.replace("__ZIP3_JSON__", zip3_json)
    html = html.replace("__CONSULTANTS_JSON__", cons_json)
    html = html.replace("__CONSULTANT_COUNT__", str(len(consultants)))
    html = html.replace("__UPDATED__", updated)
    html = html.replace("__TODAY_MS__", today_ms)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"  wrote {OUT.relative_to(REPO_ROOT)} ({os.path.getsize(OUT):,} bytes)")


if __name__ == "__main__":
    main()
