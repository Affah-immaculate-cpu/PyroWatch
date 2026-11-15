from pathlib import Path

import pandas as pd


data_folder = Path(__file__).resolve().parent / "data" / "training"
csv_files = sorted(data_folder.rglob("*.csv"))

if not csv_files:
    print(f"No CSV files found in {data_folder}. Check the folder path.")

for file in csv_files:
    print()
    print("FILE:", file.name)

    df = pd.read_csv(file)

    df["acq_date"] = pd.to_datetime(df["acq_date"])

    print("\nDATE COVERAGE")
    print("First date:", df["acq_date"].min())
    print("Last date:", df["acq_date"].max())

    print("\nGEOGRAPHIC COVERAGE")
    print("Minimum latitude:", df["latitude"].min())
    print("Maximum latitude:", df["latitude"].max())
    print("Minimum longitude:", df["longitude"].min())
    print("Maximum longitude:", df["longitude"].max())

    print("\nSATELLITE VALUES")
    print(df["satellite"].value_counts())

    print("\nINSTRUMENT VALUES")
    print(df["instrument"].value_counts())

    print("\nDAY/NIGHT DISTRIBUTION")
    print(df["daynight"].value_counts())

    print("\nCONFIDENCE VALUES")
    print(df["confidence"].value_counts().head(10))
