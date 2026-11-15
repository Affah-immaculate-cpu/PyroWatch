"""
Generate SYNTHETIC demo fire detections that look like NASA FIRMS CSV exports.

WARNING: This data is fake. It exists only so the dashboard has something to
show before you download real FIRMS data. Never present it as real satellite
observations.

Run from the project folder:
    python scripts/generate_demo_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

# --- Settings you can change -------------------------------------------------
SEED = 42                      # same seed -> same fake data every time
START = "2025-11-01"           # West African dry season roughly Nov - Mar
END = "2026-03-31"
N_FIRE_EVENTS = 260            # how many fake "fires" to invent
# Rough West Africa bounding box (land-heavy part, south of the Sahara)
LAT_MIN, LAT_MAX = 5.0, 14.0
LON_MIN, LON_MAX = -16.0, 10.0
# -----------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
MODIS_DIR = ROOT / "data" / "raw" / "modis"
VIIRS_DIR = ROOT / "data" / "raw" / "viirs"

rng = np.random.default_rng(SEED)
days = pd.date_range(START, END, freq="D")


def hhmm(base_hhmm: int, jitter_minutes: int) -> int:
    """Return a valid HHMM time near base_hhmm (e.g. 1330 -> 1312 or 1347)."""
    minutes = (base_hhmm // 100) * 60 + base_hhmm % 100
    minutes += int(rng.integers(-jitter_minutes, jitter_minutes + 1))
    return (minutes // 60) * 100 + minutes % 60


def seasonal_weight(day: pd.Timestamp) -> float:
    """More fires in Dec-Feb (peak dry season), fewer at the edges."""
    peak = pd.Timestamp("2026-01-10")
    distance_in_days = abs((day - peak).days)
    return float(np.exp(-(distance_in_days / 45) ** 2))


weights = np.array([seasonal_weight(d) for d in days])
weights = weights / weights.sum()

modis_rows, viirs_rows = [], []

for _ in range(N_FIRE_EVENTS):
    # Each fake fire has a centre, a start day and a duration.
    lat0 = rng.uniform(LAT_MIN, LAT_MAX)
    lon0 = rng.uniform(LON_MIN, LON_MAX)
    start_day = days[rng.choice(len(days), p=weights)]
    duration = int(rng.integers(1, 8))
    intensity = rng.gamma(2.0, 12.0)          # typical FRP scale in MW

    for d in range(duration):
        day = start_day + pd.Timedelta(days=d)
        if day > days[-1]:
            break
        # The fire drifts a little each day.
        lat = lat0 + rng.normal(0, 0.003 * (d + 1))
        lon = lon0 + rng.normal(0, 0.003 * (d + 1))

        # MODIS (Terra ~10:30 / Aqua ~13:30 local overpasses)
        for sat, base_time in (("T", 1030), ("A", 1330)):
            if rng.random() < 0.55:
                modis_rows.append({
                    "latitude": round(lat + rng.normal(0, 0.008), 4),
                    "longitude": round(lon + rng.normal(0, 0.008), 4),
                    "brightness": round(rng.normal(320, 12), 1),
                    "scan": round(rng.uniform(1.0, 2.5), 1),
                    "track": round(rng.uniform(1.0, 1.6), 1),
                    "acq_date": day.strftime("%Y-%m-%d"),
                    "acq_time": hhmm(base_time, 20),
                    "satellite": sat,
                    "instrument": "MODIS",
                    "confidence": int(np.clip(rng.normal(70, 18), 0, 100)),
                    "version": "6.1NRT",
                    "bright_t31": round(rng.normal(300, 6), 1),
                    "frp": round(max(1.0, intensity * rng.lognormal(0, 0.5)), 1),
                    "daynight": "D",
                })

        # VIIRS (finer resolution -> usually several pixels per fire)
        for sat in ("N", "N20", "N21"):
            if rng.random() < 0.7:
                for _pixel in range(int(rng.integers(1, 4))):
                    viirs_rows.append({
                        "latitude": round(lat + rng.normal(0, 0.004), 4),
                        "longitude": round(lon + rng.normal(0, 0.004), 4),
                        "bright_ti4": round(rng.normal(335, 10), 1),
                        "scan": round(rng.uniform(0.35, 0.7), 2),
                        "track": round(rng.uniform(0.35, 0.7), 2),
                        "acq_date": day.strftime("%Y-%m-%d"),
                        "acq_time": hhmm(1330, 40),
                        "satellite": sat,
                        "instrument": "VIIRS",
                        "confidence": rng.choice(["l", "n", "h"], p=[0.1, 0.7, 0.2]),
                        "version": "2.0NRT",
                        "bright_ti5": round(rng.normal(298, 5), 1),
                        "frp": round(max(0.5, intensity * 0.4 * rng.lognormal(0, 0.6)), 1),
                        "daynight": "D",
                    })

MODIS_DIR.mkdir(parents=True, exist_ok=True)
VIIRS_DIR.mkdir(parents=True, exist_ok=True)

modis = pd.DataFrame(modis_rows).sort_values(["acq_date", "acq_time"])
viirs = pd.DataFrame(viirs_rows).sort_values(["acq_date", "acq_time"])
modis.to_csv(MODIS_DIR / "DEMO_SYNTHETIC_modis_west_africa.csv", index=False)
viirs.to_csv(VIIRS_DIR / "DEMO_SYNTHETIC_viirs_west_africa.csv", index=False)

print(f"Wrote {len(modis):,} fake MODIS rows and {len(viirs):,} fake VIIRS rows.")
print("Remember: this is SYNTHETIC demo data, not real FIRMS observations.")
