"""
Read FIRMS CSVs from data/raw/modis and data/raw/viirs, harmonize them,
and save the results to data/processed/.

Run from the project folder:
    python scripts/process_firms.py
"""

import sys
from pathlib import Path

# Let this script import the `pyro` package from the project folder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyro.processing import PROCESSED_DIR, harmonize, load_raw_hotspots, save_processed  # noqa: E402

raw = load_raw_hotspots()
if raw.empty:
    print("No CSV files found in data/raw/modis or data/raw/viirs.")
    print("Run `python scripts/generate_demo_data.py` or add FIRMS CSVs first.")
    sys.exit(1)

raw, groups = harmonize(raw, max_km=2.0, max_hours=24)
save_processed(raw, groups)

print(f"Read {len(raw):,} detections "
      f"({(raw['sensor'] == 'MODIS').sum():,} MODIS, {(raw['sensor'] == 'VIIRS').sum():,} VIIRS)")
print(f"Grouped into {len(groups):,} harmonized groups")
print(f"Saved to {PROCESSED_DIR}")
