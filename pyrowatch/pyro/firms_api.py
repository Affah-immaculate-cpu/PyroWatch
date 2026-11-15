"""
Download real fire detections from the NASA FIRMS "area" API.

Analogy: the FIRMS API is a library counter. Your MAP_KEY is your library
card, the "source" is which shelf (MODIS or a VIIRS satellite), the area is
the map region, and you can only borrow a few days of records per trip —
so for a long date range we make several trips and staple the pages together.

API pattern:
  /api/area/csv/{MAP_KEY}/{SOURCE}/{west,south,east,north}/{DAY_RANGE}/{START_DATE}
returns detections from START_DATE to START_DATE + DAY_RANGE - 1.

Get a free MAP_KEY at https://firms.modaps.eosdis.nasa.gov/api/map_key/
Keep it secret: never put it in code that goes to GitHub.
"""

import io
import time
from datetime import date, timedelta

import pandas as pd
import requests

BASE = "https://firms.modaps.eosdis.nasa.gov"
MAX_DAYS_PER_REQUEST = 5   # conservative; some FIRMS docs allow more

# NRT = near real-time (recent weeks). SP = standard processing (older, final).
SOURCES = {
    "VIIRS_SNPP_NRT": "VIIRS",
    "VIIRS_NOAA20_NRT": "VIIRS",
    "VIIRS_NOAA21_NRT": "VIIRS",
    "MODIS_NRT": "MODIS",
    "VIIRS_SNPP_SP": "VIIRS",
    "VIIRS_NOAA20_SP": "VIIRS",
    "MODIS_SP": "MODIS",
}

# Bounding boxes as (west, south, east, north) in degrees.
AREAS = {
    "Ghana": (-3.3, 4.6, 1.3, 11.2),
    "West Africa": (-18.0, 4.0, 16.0, 16.0),
    "Côte d'Ivoire": (-8.7, 4.3, -2.4, 10.8),
    "Nigeria": (2.6, 4.2, 14.7, 13.9),
}


class FirmsError(Exception):
    """Raised when FIRMS returns an error message instead of CSV data."""


def _get(url: str, timeout: int = 60) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_chunk(map_key: str, source: str, bbox, start: date, days: int) -> pd.DataFrame:
    """One API call: `days` days (1..MAX_DAYS_PER_REQUEST) starting at `start`."""
    area = ",".join(str(v) for v in bbox)
    url = f"{BASE}/api/area/csv/{map_key}/{source}/{area}/{days}/{start:%Y-%m-%d}"
    text = _get(url)
    first_line = text.splitlines()[0] if text.strip() else ""
    # On errors FIRMS often replies with a plain sentence such as "Invalid MAP_KEY."
    if "latitude" not in first_line:
        raise FirmsError(text.strip()[:200] or "Empty reply from FIRMS")
    return pd.read_csv(io.StringIO(text))


def fetch_range(map_key: str, source: str, bbox, start: date, end: date,
                on_progress=None, pause_seconds: float = 0.5) -> pd.DataFrame:
    """
    Fetch every day from `start` to `end` (inclusive), in chunks.
    `on_progress(done_days, total_days)` is called after each chunk if given.
    """
    if end < start:
        raise ValueError("End date must be on or after start date.")
    total = (end - start).days + 1
    frames, cursor, done = [], start, 0
    while cursor <= end:
        days = min(MAX_DAYS_PER_REQUEST, (end - cursor).days + 1)
        frames.append(fetch_chunk(map_key, source, bbox, cursor, days))
        cursor += timedelta(days=days)
        done += days
        if on_progress:
            on_progress(done, total)
        time.sleep(pause_seconds)          # be polite to the server
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    df["firms_source"] = source
    return df


def output_filename(source: str, bbox, start: date, end: date) -> str:
    w, s, e, n = bbox
    return f"FIRMS_{source}_{w}_{s}_{e}_{n}_{start:%Y%m%d}-{end:%Y%m%d}.csv"
