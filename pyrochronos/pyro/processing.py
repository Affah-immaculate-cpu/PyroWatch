from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
TRAINING_DIR = ROOT / "data" / "training"
PROCESSED_DIR = ROOT / "data" / "processed"
DEMO_BACKUP_DIR = ROOT / "data" / "demo_backup"
DEMO_PREFIX = "DEMO_SYNTHETIC"

# FIRMS exports sometimes use slightly different column names. Map them here.
COLUMN_ALIASES = {
    "lat": "latitude",
    "lon": "longitude",
    "lng": "longitude",
    "date": "acq_date",
    "time": "acq_time",
}


def read_folder(folder: Path, sensor: str) -> pd.DataFrame:
    """Read every CSV in one folder and tag rows with the sensor name."""
    frames = []
    for csv_path in sorted(folder.glob("*.csv")):
        df = pd.read_csv(csv_path)
        df.columns = [c.strip().lower() for c in df.columns]
        df = df.rename(columns=COLUMN_ALIASES)
        df["sensor"] = detect_sensor(df, default=sensor)
        df["source_file"] = csv_path.name
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def detect_sensor(df: pd.DataFrame, default: str) -> str:
    """Trust the file's own columns over the folder it was put in."""
    if "instrument" in df.columns and df["instrument"].notna().any():
        value = str(df["instrument"].dropna().iloc[0]).upper()
        if value in ("MODIS", "VIIRS"):
            return value
    if "bright_ti4" in df.columns:
        return "VIIRS"
    if "brightness" in df.columns:
        return "MODIS"
    return default


def sensor_of_csv(header_columns) -> str | None:
    """Guess MODIS/VIIRS from a CSV header (used when saving uploads)."""
    cols = {c.strip().lower() for c in header_columns}
    if "bright_ti4" in cols:
        return "VIIRS"
    if "brightness" in cols:
        return "MODIS"
    return None


def list_raw_files() -> pd.DataFrame:
    """Every CSV currently in data/raw, with size and whether it's demo data."""
    rows = []
    for sensor in ("modis", "viirs"):
        for p in sorted((RAW_DIR / sensor).glob("*.csv")):
            rows.append({"folder": sensor, "file": p.name,
                        "size_kb": round(p.stat().st_size / 1024, 1),
                        "demo": p.name.startswith(DEMO_PREFIX),
                        "modified": p.stat().st_mtime})
    return pd.DataFrame(rows, columns=["folder", "file", "size_kb", "demo", "modified"])


def list_training_files() -> pd.DataFrame:
    """Every CSV in data/training, kept separate from dashboard source files."""
    rows = []
    for sensor in ("modis", "viirs"):
        for path in sorted((TRAINING_DIR / sensor).glob("*.csv")):
            rows.append({
                "folder": sensor,
                "file": path.name,
                "size_kb": round(path.stat().st_size / 1024, 1),
                "modified": path.stat().st_mtime,
            })
    return pd.DataFrame(rows, columns=["folder", "file", "size_kb", "modified"])


def data_fingerprint() -> tuple:
    """Changes whenever a raw CSV is added, removed or edited (used as a cache key)."""
    files = list_raw_files()
    return tuple(zip(files["file"], files["modified"]))


def training_fingerprint() -> tuple:
    """Changes whenever a training CSV is added, removed or edited."""
    files = list_training_files()
    return tuple(zip(files["folder"], files["file"], files["size_kb"], files["modified"]))


def move_demo_files(to_backup: bool = True) -> int:
    """Move demo CSVs out of data/raw (or back in). Nothing is deleted."""
    moved = 0
    for sensor in ("modis", "viirs"):
        src = (RAW_DIR if to_backup else DEMO_BACKUP_DIR) / sensor
        dst = (DEMO_BACKUP_DIR if to_backup else RAW_DIR) / sensor
        dst.mkdir(parents=True, exist_ok=True)
        for p in src.glob(f"{DEMO_PREFIX}*.csv"):
            p.replace(dst / p.name)
            moved += 1
    return moved


def confidence_class(row) -> str:
    """
    Put MODIS (0-100) and VIIRS (l/n/h) confidence into a shared *display*
    label. The original value is kept in `confidence` because the two scales
    are NOT scientifically equivalent.
    """
    value = row["confidence"]
    if row["sensor"] == "VIIRS":
        return {"l": "low", "n": "nominal", "h": "high"}.get(str(value).lower(), "unknown")
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if value < 30:
        return "low"
    if value < 80:
        return "nominal"
    return "high"


def load_raw_hotspots() -> pd.DataFrame:
    """Read all MODIS + VIIRS CSVs and return one clean table."""
    modis = read_folder(RAW_DIR / "modis", "MODIS")
    viirs = read_folder(RAW_DIR / "viirs", "VIIRS")
    df = pd.concat([modis, viirs], ignore_index=True)
    if df.empty:
        return df

    required = {"latitude", "longitude", "acq_date"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV files are missing required columns: {missing}")

    # acq_time is HHMM in UTC, e.g. 1330 -> 13:30. Pad to 4 digits.
    if "acq_time" not in df.columns:
        df["acq_time"] = 0
    hhmm = df["acq_time"].fillna(0).astype(int).astype(str).str.zfill(4)
    df["datetime_utc"] = pd.to_datetime(
        df["acq_date"].astype(str) + " " + hhmm.str[:2] + ":" + hhmm.str[2:],
        errors="coerce",
    )
    df["date"] = df["datetime_utc"].dt.date

    if "frp" not in df.columns:
        df["frp"] = np.nan
    if "confidence" not in df.columns:
        df["confidence"] = np.nan
    if "satellite" not in df.columns:
        df["satellite"] = "unknown"

    df["confidence_class"] = df.apply(confidence_class, axis=1)
    # MODIS confidence is a number, VIIRS a letter -> store both as text.
    df["confidence"] = df["confidence"].astype(str)
    # The same detection can appear twice (e.g. overlapping downloads, or NRT
    # and SP versions of the same day). Keep one copy.
    key = [c for c in ("latitude", "longitude", "acq_date", "acq_time", "satellite")
        if c in df.columns]
    df = df.drop_duplicates(subset=key)

    before = len(df)
    df = df.dropna(subset=["latitude", "longitude", "datetime_utc"])
    if len(df) < before:
        print(f"Warning: dropped {before - len(df)} rows with missing/invalid location or time.")
    df = df.sort_values("datetime_utc").reset_index(drop=True)
    df["obs_id"] = np.arange(len(df))
    return df


def load_training_hotspots() -> pd.DataFrame:
    """Load FIRMS-format training CSVs without reading dashboard data in data/raw."""
    modis = read_folder(TRAINING_DIR / "modis", "MODIS")
    viirs = read_folder(TRAINING_DIR / "viirs", "VIIRS")
    df = pd.concat([modis, viirs], ignore_index=True)
    if df.empty:
        return df

    required = {"latitude", "longitude", "acq_date"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            "Training CSV files are missing required FIRMS columns: "
            f"{', '.join(sorted(missing))}"
        )

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["date"] = pd.to_datetime(df["acq_date"], errors="coerce").dt.normalize()
    before = len(df)
    df = df.dropna(subset=["latitude", "longitude", "date"])
    valid_coordinates = (
        df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)
    )
    df = df[valid_coordinates].copy()
    if len(df) < before:
        print(
            f"Warning: dropped {before - len(df)} training rows with invalid "
            "coordinates or dates."
        )
    if df.empty:
        raise ValueError("Training CSV files contain no valid FIRMS observations.")
    return df.reset_index(drop=True)


def haversine_km(lat1, lon1, lat2, lon2):
    """Distance between points on Earth in kilometres (works with arrays)."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def harmonize(raw: pd.DataFrame, max_km: float = 2.0, max_hours: float = 24.0):
    """
    DEMO heuristic: walk through detections in time order. If a detection is
    within `max_km` and `max_hours` of an open group's latest detection, it
    joins that group; otherwise it starts a new group.

    This is NOT a validated fire-incident algorithm. Two nearby fires can be
    merged, and one big fire can be split.

    Returns (raw_with_group_id, groups_table).
    """
    if raw.empty:
        return raw.assign(group_id=pd.Series(dtype=int)), pd.DataFrame()

    lats = raw["latitude"].to_numpy()
    lons = raw["longitude"].to_numpy()
    times = raw["datetime_utc"].to_numpy().astype("datetime64[s]").astype(np.int64)
    max_seconds = max_hours * 3600

    n = len(raw)
    group_ids = np.empty(n, dtype=int)
    # Each group remembers its latest point and time.
    g_lat, g_lon, g_time = np.empty(n), np.empty(n), np.empty(n, dtype=np.int64)
    n_groups = 0

    # Bucket nearby groups so each detection checks only its local 3x3 grid.
    # This preserves the full-search result while reducing comparisons.
    km_per_deg = 6371.0 * np.pi / 180
    cos_min = max(np.cos(np.radians(np.abs(lats).max())), 0.01)
    cell_lat = max_km / km_per_deg * 1.001
    cell_lon = max_km / (km_per_deg * cos_min) * 1.001
    buckets: dict[tuple[int, int], set[int]] = {}

    def cell_of(lat, lon):
        return int(np.floor(lat / cell_lat)), int(np.floor(lon / cell_lon))

    for i in range(n):
        ci, cj = cell_of(lats[i], lons[i])
        candidates = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                bucket = buckets.get((ci + di, cj + dj))
                if not bucket:
                    continue
                # Times are sorted, so a group too old now stays too old: drop it.
                stale = [g for g in bucket if times[i] - g_time[g] > max_seconds]
                bucket.difference_update(stale)
                candidates.extend(bucket)

        assigned = -1
        if candidates:
            cand = np.sort(np.fromiter(candidates, dtype=int))  # same tie-break order
            dist = haversine_km(lats[i], lons[i], g_lat[cand], g_lon[cand])
            best = int(np.argmin(dist))
            if dist[best] <= max_km:
                assigned = int(cand[best])
        if assigned == -1:
            assigned = n_groups
            n_groups += 1
        else:
            buckets[cell_of(g_lat[assigned], g_lon[assigned])].discard(assigned)
        g_lat[assigned], g_lon[assigned], g_time[assigned] = lats[i], lons[i], times[i]
        buckets.setdefault((ci, cj), set()).add(assigned)
        group_ids[i] = assigned

    raw = raw.copy()
    raw["group_id"] = group_ids

    groups = (
        raw.groupby("group_id")
        .agg(
            latitude=("latitude", "mean"),
            longitude=("longitude", "mean"),
            first_seen=("datetime_utc", "min"),
            last_seen=("datetime_utc", "max"),
            n_detections=("obs_id", "count"),
            # FRP is NOT additive across overlapping sensors -> use the max.
            max_frp=("frp", "max"),
            sensors=("sensor", lambda s: "+".join(sorted(set(s)))),
            satellites=("satellite", lambda s: ",".join(sorted(set(map(str, s))))),
        )
        .reset_index()
    )
    groups["date"] = groups["first_seen"].dt.date
    groups["duration_hours"] = (
        (groups["last_seen"] - groups["first_seen"]).dt.total_seconds() / 3600
    ).round(1)
    return raw, groups


def save_processed(raw: pd.DataFrame, groups: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw.to_csv(PROCESSED_DIR / "raw_hotspots.csv", index=False)
    groups.to_csv(PROCESSED_DIR / "harmonized_hotspots.csv", index=False)
