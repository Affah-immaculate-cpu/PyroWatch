"""
Download FIRMS detections from the command line (good for long date ranges).

Your MAP_KEY is read from the FIRMS_MAP_KEY environment variable, so it
never appears in your code or your terminal history file.

  PowerShell:  $env:FIRMS_MAP_KEY = "your-key"
  Git Bash:    export FIRMS_MAP_KEY="your-key"

Examples (run from the project folder):
  python scripts/fetch_firms.py --area Ghana --start 2026-10-01 --end 2026-11-14
  python scripts/fetch_firms.py --area West\\ Africa --sources MODIS_NRT VIIRS_SNPP_NRT --start 2026-11-01 --end 2026-11-14
  python scripts/fetch_firms.py --bbox -3.3 4.6 1.3 11.2 --sources VIIRS_SNPP_SP --start 2025-11-01 --end 2026-03-31
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyro import firms_api  # noqa: E402
from pyro.processing import RAW_DIR  # noqa: E402

parser = argparse.ArgumentParser(description="Download NASA FIRMS fire detections.")
parser.add_argument("--area", choices=list(firms_api.AREAS), default="Ghana")
parser.add_argument("--bbox", nargs=4, type=float, metavar=("WEST", "SOUTH", "EAST", "NORTH"),
                    help="custom box; overrides --area")
parser.add_argument("--sources", nargs="+", choices=list(firms_api.SOURCES),
                    default=["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"])
parser.add_argument("--start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
parser.add_argument("--end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
args = parser.parse_args()

map_key = os.environ.get("FIRMS_MAP_KEY")
if not map_key:
    sys.exit("Set the FIRMS_MAP_KEY environment variable first (see the top of this file).")

bbox = tuple(args.bbox) if args.bbox else firms_api.AREAS[args.area]

for source in args.sources:
    print(f"\n{source}  box={bbox}  {args.start} → {args.end}")
    try:
        df = firms_api.fetch_range(
            map_key, source, bbox, args.start, args.end,
            on_progress=lambda done, total: print(f"  {done}/{total} days", end="\r"))
    except firms_api.FirmsError as err:
        print(f"  FIRMS error: {err}")
        continue
    if df.empty or len(df.columns) <= 1:
        print("  no detections")
        continue
    folder = RAW_DIR / firms_api.SOURCES[source].lower()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / firms_api.output_filename(source, bbox, args.start, args.end)
    df.to_csv(path, index=False)
    print(f"  saved {len(df):,} rows → {path.relative_to(RAW_DIR.parent.parent)}")

print("\nDone. Restart or refresh the Streamlit app to see the new data.")
