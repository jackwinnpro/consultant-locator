"""PHASE 2 — Headless Flight export via Playwright.

Goal: replace the manual "click through Flight and download Excel" step so the
weekly-refresh workflow can run unattended. When this script succeeds it should
leave TWO files in data/raw/ for build_data.py to pick up:

  - All Consultants zip codes.xlsx   (active Professional + Ambassador list with addresses)
  - All Orders_KK.xlsx               (6 months of orders, for the active filter)

Flight uses Izenda for reports. The URLs below come from the existing
commissions skill (.claude/skills/commissions/SKILL.md). That skill does the
same navigate/filter/export dance manually; this script automates it.

============================================================================
SETUP CHECKLIST — complete before enabling weekly-refresh.yml
============================================================================

1. Credentials
   Add repo secrets: FLIGHT_USERNAME, FLIGHT_PASSWORD
   Local dev: put them in a .env file (gitignored) and load via python-dotenv.

2. Install
   pip install playwright python-dotenv
   playwright install chromium

3. Iterate locally with headless=False until the flow is stable:
     FLIGHT_USERNAME=... FLIGHT_PASSWORD=... python scripts/flight_export.py

4. Known Izenda quirks (from the commissions skill):
   - Filter column header must be clicked to expand the input
   - Date fields take two text inputs (from / to) in M/d/yyyy format
   - "Apply Filter" button is orange; wait for the grid to refresh
   - Export → CSV (XLSX export also works but pandas reads either format)
   - Filter bar uses ••• pagination — Commission Date may be hidden initially

5. Confirm the downloads land with predictable filenames (rename if needed).
============================================================================
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

# from playwright.sync_api import sync_playwright   # uncomment when implementing

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "data" / "raw"

FLIGHT_BASE = "https://flight.jackwinnpro.com"
LOGIN_URL = f"{FLIGHT_BASE}/Account/Login"

# Izenda report IDs (from .claude/skills/commissions/SKILL.md)
ORDERS_REPORT_ID = "b2a8d44d-a17b-46bb-8f44-ac3fdff297a0"   # All Orders_KK
# TODO: look up the consultants/enrollment report. The commissions skill uses
# "8f234ccd-a857-41b6-850e-a6267dc9ab03" (Enrollment Info) but confirm it has
# the address columns we need (street, city, state, zip).
CONSULTANTS_REPORT_ID = "8f234ccd-a857-41b6-850e-a6267dc9ab03"


def require_env() -> tuple[str, str]:
    user = os.environ.get("FLIGHT_USERNAME")
    pw = os.environ.get("FLIGHT_PASSWORD")
    if not (user and pw):
        sys.exit("ERROR: set FLIGHT_USERNAME and FLIGHT_PASSWORD (env or repo secrets).")
    return user, pw


def main() -> None:
    require_env()
    RAW.mkdir(parents=True, exist_ok=True)

    today = date.today()
    six_months_ago = today - timedelta(days=183)
    print(f"Exporting orders from {six_months_ago.strftime('%m/%d/%Y')} "
          f"to {today.strftime('%m/%d/%Y')}")

    raise NotImplementedError(
        "Playwright flow not implemented yet. Outline:\n"
        "  1. Launch Chromium, go to LOGIN_URL, fill #username / #password, submit.\n"
        "  2. Navigate to Reports/ViewReport?id=<ORDERS_REPORT_ID>.\n"
        "  3. Set 'Commission Date' filter to [six_months_ago, today], click Apply.\n"
        "  4. Wait for grid refresh, click Export → XLSX, save to data/raw/All Orders_KK.xlsx.\n"
        "  5. Navigate to Reports/ViewReport?id=<CONSULTANTS_REPORT_ID> (no date filter).\n"
        "  6. Click Export → XLSX, save to data/raw/All Consultants zip codes.xlsx.\n"
        "See .claude/skills/commissions/SKILL.md for UI interaction notes."
    )


if __name__ == "__main__":
    main()
