"""Convenience wrapper: run build_data then build_artifact."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

steps = [
    (HERE / "build_data.py", "ETL + geocode"),
    (HERE / "build_artifact.py", "Render HTML"),
]

for script, label in steps:
    print(f"\n=== {label} ({script.name}) ===")
    r = subprocess.run([sys.executable, str(script)])
    if r.returncode != 0:
        print(f"FAILED in {script.name}", file=sys.stderr)
        sys.exit(r.returncode)

print("\nDone. Open docs/index.html in a browser, or commit & push to deploy via GitHub Pages.")
