from pathlib import Path

import pandas as pd


data_folder = Path(__file__).resolve().parent / "data" / "training"
csv_files = sorted(data_folder.rglob("*.csv"))

if not csv_files:
    print(f"No CSV files found in {data_folder}. Check the folder path.")
else:
    print(f"Found {len(csv_files)} CSV file(s).")

    for file in csv_files:
        print()
        print("FILE:", file.name)

        df = pd.read_csv(file)

        print("Rows and columns:", df.shape)

        print("\nColumn names:")
        print(df.columns.tolist())

        print("\nFirst five records:")
        print(df.head())

        print("\nMissing values:")
        print(df.isnull().sum())

        print("\nDuplicate records:", df.duplicated().sum())
