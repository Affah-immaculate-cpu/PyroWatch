"""Name the nearest Ghana town for a point, so alerts can be searched by town.

Place list: data/boundaries/ghana_places.csv, built by scripts/build_ghana_places.py
from GeoNames (geonames.org, CC BY 4.0).
"""

from pathlib import Path

import numpy as np
import pandas as pd

from pyro.processing import haversine_km

PLACES_FILE = Path(__file__).resolve().parents[1] / "data" / "boundaries" / "ghana_places.csv"


def load_places(path: Path = PLACES_FILE) -> pd.DataFrame:
    """Empty table if the file hasn't been built yet (labels then fall back to region only)."""
    if not path.exists():
        return pd.DataFrame(columns=["name", "latitude", "longitude", "population", "major"])
    return pd.read_csv(path)


def nearest(places: pd.DataFrame, lat: float, lon: float) -> tuple[str, float] | None:
    """(name, distance in km) of the closest place, or None if there are no places."""
    if places.empty:
        return None
    dist = haversine_km(lat, lon, places["latitude"].to_numpy(), places["longitude"].to_numpy())
    i = int(np.argmin(dist))
    return str(places["name"].iloc[i]), float(dist[i])


def describe(places: pd.DataFrame, lat: float, lon: float) -> str:
    """e.g. 'near Kumbungu (4 km) · 22 km from Tamale'. Empty string if no places."""
    local = nearest(places, lat, lon)
    if local is None:
        return ""
    major = nearest(places[places["major"].astype(bool)], lat, lon)
    text = f"near {local[0]} ({local[1]:.0f} km)"
    if major and major[0] != local[0]:
        text += f" · {major[1]:.0f} km from {major[0]}"
    return text
