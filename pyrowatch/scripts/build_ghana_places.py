"""
Build data/boundaries/ghana_places.csv: Ghana towns used to label alerts
("near Kumbungu · Tamale area") so you can search alerts by town name.

Source: GeoNames (geonames.org), CC BY 4.0. Credit it in the app and slides.

Usage:
    python scripts/build_ghana_places.py               # downloads GH.zip
    python scripts/build_ghana_places.py path/GH.txt   # use a file you already have
"""

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "boundaries" / "ghana_places.csv"
URL = "https://download.geonames.org/export/dump/GH.zip"
COLUMNS = ["id", "name", "asciiname", "alternatenames", "latitude", "longitude",
           "feature_class", "feature_code", "country", "cc2", "admin1", "admin2",
           "admin3", "admin4", "population", "elevation", "dem", "timezone", "modified"]
ADMIN_SEATS = {"PPLC", "PPLA", "PPLA2"}   # capital, regional and district seats


def read_geonames(path: str | None) -> pd.DataFrame:
    if path:
        source = path
    else:
        print(f"Downloading {URL} …")
        zipped = zipfile.ZipFile(io.BytesIO(requests.get(URL, timeout=120).content))
        source = io.BytesIO(zipped.read("GH.txt"))
    return pd.read_csv(source, sep="\t", names=COLUMNS, quoting=3, dtype=str,
                       keep_default_na=False, encoding="utf-8")


def main() -> None:
    df = read_geonames(sys.argv[1] if len(sys.argv) > 1 else None)
    df = df[(df["feature_class"] == "P") & (df["country"] == "GH")].copy()
    df["population"] = pd.to_numeric(df["population"], errors="coerce").fillna(0).astype(int)
    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)
    n_alt = df["alternatenames"].apply(lambda s: s.count(",") + 1 if s else 0)

    # Major town: big enough, or an administrative seat.
    df["major"] = (df["population"] >= 5000) | df["feature_code"].isin(ADMIN_SEATS)
    # Local place: major, or well-known enough to have 3+ alternate spellings.
    keep = df[df["major"] | (n_alt >= 3)]
    keep = keep[["name", "latitude", "longitude", "population", "major"]]
    keep = keep.sort_values(["major", "population"], ascending=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    keep.to_csv(OUT, index=False)
    print(f"Saved {len(keep):,} places ({int(keep['major'].sum())} major towns) -> {OUT}")


if __name__ == "__main__":
    main()
