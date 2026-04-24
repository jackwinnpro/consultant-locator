# Consultant Locator

Internal tool for Jack Winn Pro. Team members type a zip code and see the
closest actively-ordering consultants (3+ orders in the past 6 months), sorted
by distance.

Hosted on GitHub Pages. Rebuilt weekly from Flight data.

---

## Repo layout

```
consultant-locator/
├── scripts/
│   ├── build_data.py          # Excel exports → data/consultants.json + data/us_zips.json
│   ├── build_artifact.py      # JSON + template.html → docs/index.html
│   ├── build.py               # Convenience: runs both in order
│   └── flight_export.py       # PHASE 2 stub — headless Flight pull
├── src/
│   └── template.html          # HTML template with __PLACEHOLDERS__
├── data/
│   ├── raw/                   # Flight exports land here (gitignored)
│   ├── consultants.json       # Intermediate (gitignored)
│   └── us_zips.json           # Intermediate (gitignored)
├── docs/
│   └── index.html             # Built output — what GitHub Pages serves
├── .github/workflows/
│   └── weekly-refresh.yml     # PHASE 2, disabled until flight_export.py is done
├── requirements.txt
├── README.md
└── CLAUDE.md
```

---

## First-time setup

1. Create a new GitHub repo (private is fine; GitHub Pages works on private
   repos with any paid plan).
2. Push this folder to `main`.
3. Repo Settings → Pages → **Source: Deploy from a branch**
   → Branch: `main`, folder: `/docs` → Save.
4. Wait ~1 minute; GitHub gives you a URL like
   `https://<org>.github.io/<repo>/`. Share that URL with the team.

---

## Manual refresh (Phase 1 — use this until Phase 2 is live)

Once a week, or whenever the data feels stale:

```bash
# 1. Pull fresh exports from Flight (manual, per the commissions skill steps)
#    Save as:
#      data/raw/All Consultants zip codes.xlsx
#      data/raw/All Orders_KK.xlsx
#    (The "(N)" suffix Flight adds to filenames is fine — the build picks the latest match.)

# 2. Build
pip install -r requirements.txt   # once per environment
python scripts/build.py

# 3. Review
open docs/index.html              # spot-check in a browser

# 4. Deploy
git add docs/index.html
git commit -m "Refresh $(date +%Y-%m-%d)"
git push
# GitHub Pages redeploys within ~30 seconds.
```

### Pulling the Excel files from Flight

Same Flight UI Kelsy already uses for commissions. For the locator we need two
reports:

| Save as                                 | Flight source                                                                                              |
|-----------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `All Consultants zip codes.xlsx`        | `/Reports/ViewReport?id=8f234ccd-a857-41b6-850e-a6267dc9ab03` — Enrollment Info. No date filter. Export XLSX. |
| `All Orders_KK.xlsx`                    | `/Reports/ViewReport?id=b2a8d44d-a17b-46bb-8f44-ac3fdff297a0` — All Orders_KK. Set **Commission Date** to the past 183 days (≈6 months). Export XLSX. |

See `.claude/skills/commissions/SKILL.md` for Izenda filter quirks.

---

## Automated refresh (Phase 2 — not yet enabled)

`weekly-refresh.yml` is wired up but disabled (`if: false`). Before turning it
on:

1. Fill in the Playwright flow in `scripts/flight_export.py`.
2. Add `FLIGHT_USERNAME` and `FLIGHT_PASSWORD` as repo secrets.
3. Test locally with `playwright install chromium && python scripts/flight_export.py`.
4. Once the local run produces both Excel files in `data/raw/`, delete the
   `if: false` line in `weekly-refresh.yml`.
5. Manually dispatch the workflow once from the Actions tab to confirm green,
   then the cron schedule takes over.

---

## How it works (short version)

- `build_data.py` joins consultants with 6 months of orders, keeps anyone with
  3+ distinct orders, and geocodes their zip to lat/lng via the `zipcodes`
  package.
- `build_artifact.py` aggregates the ~41k US zips into ~933 three-digit-prefix
  centroids (~30-mile accuracy) so the whole map fits in a single lean HTML
  file. Consultants get packed as 8-element arrays and lat/lng is derived
  client-side from each record's zip prefix.
- The template is pure HTML/CSS/JS — no frameworks, no build step, no network
  calls. Works offline once loaded.

---

## Known limitations

- **Distance accuracy** is coarse (~30 mi) because we aggregate to zip-3
  centroids. Sort order inside a metro area can be noisy. Good enough for
  "who's nearby" but don't use it for precise routing.
- **Flight data quality** — a few rows in the Flight export have mismatched
  state/zip pairs (e.g., "Denver, HI 80206"). They render whatever Flight
  returns. Fix in Flight upstream if it matters.
- **No auth on the hosted page.** Security is URL obscurity + GitHub's ability
  to unpublish. If that's not good enough, switch to a password-protected
  host (Netlify/Vercel password) and build/push the same `docs/index.html`.
