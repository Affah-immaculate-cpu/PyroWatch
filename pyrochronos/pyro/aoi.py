"""Area of interest: keep only detections inside a chosen area."""
import json
from pathlib import Path

import pandas as pd
import shapely
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_DIR = ROOT / "data" / "boundaries"
NAME_KEYS = ("shapeName", "name", "NAME", "ADM1_EN", "ADM0_EN", "region")


def load_boundary(path: str):
    """Read a GeoJSON file -> (list of shapes, list of names), one per region."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("type") == "FeatureCollection":
        features = data["features"]
    elif data.get("type") == "Feature":
        features = [data]
    else:
        features = [{"type": "Feature", "geometry": data, "properties": {}}]

    shapes, names = [], []
    for f in features:
        if not f.get("geometry"):
            continue
        geom = shape(f["geometry"])
        if not geom.is_valid:
            geom = geom.buffer(0)  # repairs small drawing errors
        if geom.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        props = f.get("properties") or {}
        name = next((str(props[k]) for k in NAME_KEYS if k in props), f"Area {len(shapes) + 1}")
        shapes.append(geom)
        names.append(name)
    if not shapes:
        raise ValueError(f"No polygons found in {Path(path).name}")
    return shapes, names


def box_shape(bbox):
    return box(*bbox)  # (west, south, east, north) -> rectangle


def merge(shapes):
    return unary_union(shapes)  # several regions -> one shape


def inside(df: pd.DataFrame, geom) -> pd.Series:
    """True for each row whose point is inside geom (fast, vectorised)."""
    hits = shapely.contains_xy(geom, df["longitude"].to_numpy(), df["latitude"].to_numpy())
    return pd.Series(hits, index=df.index)


def to_geojson(geom) -> dict:
    return mapping(geom)  # for drawing the outline on a map
