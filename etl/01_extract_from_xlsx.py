import pandas as pd
import os

RAW_DIR = "data/raw/n100"
OUTPUT_DIR = "data/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TABLES = ["companies", "analysis", "balancesheet", "profitandloss", "cashflow", "prosandcons", "documents"]

print("=== ETL Script 1: Extract from Excel files ===\n")

for table in TABLES:
    path = os.path.join(RAW_DIR, f"{table}.xlsx")
    if not os.path.exists(path):
        print(f"WARNING: {path} not found, skipping.")
        continue
    # Skip first row (title row), use second row as header
    df = pd.read_excel(path, header=1)
    out = os.path.join(OUTPUT_DIR, f"{table}.csv")
    df.to_csv(out, index=False)
    print(f"{table}: {len(df)} rows, {len(df.columns)} columns → saved to {out}")
    print(f"  Columns: {list(df.columns)}\n")

print("=== Extraction Complete ===")
