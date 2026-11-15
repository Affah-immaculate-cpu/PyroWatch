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
    "frp",
    "satellite",
    "latitude",
    "longitude",
    "acq_date",
    "confidence",
}
missing_columns = required_columns - set(fire_data.columns)
if missing_columns:
    raise ValueError(
        "Training CSV files are missing required columns: "
        + ", ".join(sorted(missing_columns))
    )

fire_data["frp"] = pd.to_numeric(fire_data["frp"], errors="coerce")
valid_frp = fire_data.dropna(subset=["frp"])
if valid_frp.empty:
    raise SystemExit("No numeric FRP values were found in the training CSV files.")

print(f"Analyzed {len(csv_files)} training CSV file(s).")
print("\nFRP STATISTICS")
print(valid_frp["frp"].describe())

print("\nFRP STATISTICS BY SATELLITE")
print(
    valid_frp.groupby("satellite")["frp"]
    .agg(["count", "mean", "median", "min", "max"])
    .round(2)
)

print("\nTOP 10 HIGHEST FRP RECORDS")
print(
    valid_frp.nlargest(10, "frp")[
        ["latitude", "longitude", "acq_date", "satellite", "frp", "confidence"]
    ]
)
