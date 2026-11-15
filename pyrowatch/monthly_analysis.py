
from pathlib import Path
import pandas as pd

data_folder = Path(__file__).resolve().parent / "data" / "training"
csv_files = sorted(data_folder.rglob("*.csv"))

all_data = []

for file in csv_files:
    df = pd.read_csv(file)
    df["source_file"] = file.name
    all_data.append(df)

if not all_data:
    raise SystemExit(
        f"No training CSV files found in {data_folder} or its subfolders."
    )

fire_data = pd.concat(all_data, ignore_index=True)

required_columns = {"acq_date", "satellite"}
missing_columns = required_columns - set(fire_data.columns)
if missing_columns:
    raise ValueError(
        "Training CSV files are missing required columns: "
        + ", ".join(sorted(missing_columns))
    )

fire_data["acq_date"] = pd.to_datetime(fire_data["acq_date"], errors="coerce")
invalid_dates = fire_data["acq_date"].isna().sum()
if invalid_dates:
    print(f"Warning: skipping {invalid_dates:,} rows with invalid acquisition dates.")
    fire_data = fire_data.dropna(subset=["acq_date"])
if fire_data.empty:
    raise SystemExit("No rows with valid acquisition dates were found in the training CSVs.")

fire_data["month"] = fire_data["acq_date"].dt.month

monthly_counts = (
    fire_data
    .groupby(["month", "satellite"])
    .size()
    .unstack(fill_value=0)
)

print("\nMONTHLY FIRE DETECTIONS")
print(monthly_counts)

print("\nTOTAL DETECTIONS BY SATELLITE")
print(fire_data["satellite"].value_counts())

print("\nTOTAL RECORDS:", len(fire_data))
