# Context for Claude Code sessions

This file is a fast on-ramp for a Claude Code session working in this repo.
Read this first, then check README.md for user-facing docs.

## What this is

An internal Jack Winn Pro tool: a static HTML page that lets the team type
a zip code and see the closest "actively ordering" consultants (3+ orders in
past 6 months). Hosted on GitHub Pages. Rebuilt from Flight data.

Kelsy (kelsy@jackwinncolor.com) is the primary user. She runs operations for
Jack Winn Pro — not a developer, but comfortable running a couple of shell
commands per week.

## Architecture (three files, no framework)

```
data/raw/*.xlsx  ──build_data.py──▶  data/{consultants,us_zips}.json
                                              │
                                              ▼
                src/template.html ──build_artifact.py──▶ docs/index.html
```

- `build_data.py` — pandas + calamine + zipcodes. Joins two Excel exports from
  Flight, filters to 3+ orders in past 6 months, geocodes zips. Output:
  `data/consultants.json` (≈200KB) + `data/us_zips.json` (≈1MB, nationwide
  lookup).
- `build_artifact.py` — aggregates the full zip list to ~933 three-digit
  centroids, packs consultants into 8-field tuples, inlines both as JSON in
  the HTML template. Output is self-contained (~85KB).
- `src/template.html` — plain HTML+CSS+JS. No build tooling. Placeholders
  `__ZIP3_JSON__`, `__CONSULTANTS_JSON__`, `__CONSULTANT_COUNT__`,
  `__UPDATED__`, `__TODAY_MS__` are substituted at build time.

## Data model

**Consultant tuple (client-side):**
`[name, company, city, state, zip, orders, last_days_ago, type_code]`

- `type_code`: `0 = Ambassador`, `1 = Professional`
- `last_days_ago`: integer days between today (build day) and last order.
  Negative values mean "in the future" — used for special pinned records.
- lat/lng are NOT in the tuple; the client derives them from
  `ZIP3_INDEX[zip.slice(0,3)]`.

**Active filter:** `≥3 distinct orders in the past 183 days`, keyed by
`CommissionPersonDisplayID` in the Orders export.

## Flight exports

Two Excel files from flight.jackwinnpro.com (Izenda reports):

1. **Consultants + addresses** — Report ID `8f234ccd-a857-41b6-850e-a6267dc9ab03`
   (Enrollment Info). No date filter. Save as `data/raw/All Consultants zip codes.xlsx`.
2. **Orders, past 6 months** — Report ID `b2a8d44d-a17b-46bb-8f44-ac3fdff297a0`
   (All Orders_KK). Commission Date filtered to `today - 183 days → today+1`.
   Save as `data/raw/All Orders_KK.xlsx`.

Flight UI quirks are documented in `.claude/skills/commissions/SKILL.md` at
the repo root of Kelsy's Cowork folder (not in this repo). Same skill drives
the separate weekly commissions workflow.

## Phases

**Phase 1 (shipped):** Kelsy runs `python scripts/build.py` locally after
dropping fresh Excel exports into `data/raw/`, commits `docs/index.html`,
pushes. Pages auto-deploys.

**Phase 2 (stubbed):** `scripts/flight_export.py` should log in with
Playwright and pull both files unattended. `.github/workflows/weekly-refresh.yml`
is wired up but has `if: false`. When implementing:
- Flight auth likely uses a standard username/password form; no MFA today
  (confirm before building).
- Izenda filter interaction is fiddly — look at the commissions skill for
  the click-order notes.
- Headless Chromium in GitHub Actions works fine for this; no need for a
  separate VPS.

## Things to not touch without thinking

- **Zip-3 centroid aggregation** is a deliberate size trade-off. Don't revert
  to full-zip coords unless you also re-solve the page-weight problem.
- **`data/raw/` is gitignored** because it contains consultant PII. Do NOT
  commit raw exports. The Phase-2 workflow runs them in-memory during CI and
  only commits `docs/index.html`.
- **No network calls from the page.** The whole point is that team members
  can use this instantly, offline, without a backend. Don't add fetch calls.

## Pending work

If Kelsy asks for any of the following, tasks are:

- **Add per-salon contact info to the results** — the Excel export has
  phone + email; they're currently dropped in `compose_record`. Adding them
  bumps the artifact size ~30KB; worth it if that's what the team wants.
- **Swap to county or metro-area buckets** — if zip-3 accuracy isn't enough,
  look at aggregating by USPS SCF (3-digit zip is already that) or by metro.
- **Phase 2 Flight automation** — see `scripts/flight_export.py`.
- **Password-protect the page** — move hosting to Netlify/Vercel with the
  built-in site password, or put a Cloudflare Access policy in front of
  GitHub Pages.
