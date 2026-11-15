from pathlib import Path

import pandas as pd


data_folder = Path(__file__).resolve().parent / "data" / "training"
csv_files = sorted(data_folder.rglob("*.csv"))

if not csv_files:
    raise SystemExit(f"No training CSV files found in {data_folder} or its subfolders.")

all_data = []

for file in csv_files:
    df = pd.read_csv(file)
    df["source_file"] = file.name
    all_data.append(df)

fire_data = pd.concat(all_data, ignore_index=True)

required_columns = {
    "latitude",
    "longitude",
    "acq_date",
    "satellite",
    "frp",
}
missing_columns = required_columns - set(fire_data.columns)
if missing_columns:
    raise ValueError(
        "Training CSV files are missing required columns: "
        + ", ".join(sorted(missing_columns))
    )

print("\nDATASET OVERVIEW")
print("Files analyzed:", len(csv_files))
print("Total records:", len(fire_data))
print("Total columns:", len(fire_data.columns))
print("\nColumns:")
print(fire_data.columns.tolist())

print("\nMISSING VALUES")
print(fire_data.isnull().sum())

print("\nDUPLICATE RECORDS")
print("Exact duplicates:", fire_data.duplicated().sum())

print("\nDATA TYPES")
print(fire_data.dtypes)

print("\nGEOGRAPHIC RANGE")
print("Latitude:")
print(fire_data["latitude"].describe())
print("\nLongitude:")
print(fire_data["longitude"].describe())

outside_ghana = fire_data[
    (fire_data["latitude"] < 4.5)
    | (fire_data["latitude"] > 11.5)
    | (fire_data["longitude"] < -3.5)
    | (fire_data["longitude"] > 1.5)
]
print("\nRecords outside approximate Ghana boundaries:", len(outside_ghana))

fire_data["acq_date"] = pd.to_datetime(fire_data["acq_date"], errors="coerce")
invalid_dates = fire_data["acq_date"].isna().sum()
print("\nDATE COVERAGE")
print("Invalid acquisition dates:", invalid_dates)
if invalid_dates < len(fire_data):
    valid_dates = fire_data.dropna(subset=["acq_date"])
    print("Earliest date:", valid_dates["acq_date"].min())
    print("Latest date:", valid_dates["acq_date"].max())
    print("\nRecords by year:")
    print(valid_dates["acq_date"].dt.year.value_counts().sort_index())
    print("\nRecords by month:")
    print(valid_dates["acq_date"].dt.month.value_counts().sort_index())

print("\nSATELLITE DISTRIBUTION")
print(fire_data["satellite"].value_counts(dropna=False))

fire_data["frp"] = pd.to_numeric(fire_data["frp"], errors="coerce")
print("\nFRP PERCENTILES")
print(fire_data["frp"].quantile([0.50, 0.75, 0.90, 0.95, 0.99, 0.999]))

print("\nEND OF DATA QUALITY REPORT")
