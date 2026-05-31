import re
import pandas as pd
import os

SQL_FILE = "data/raw/scriptticker.sql"
OUTPUT_DIR = "data/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TABLES = [
    "companies", "analysis", "balancesheet",
    "profitandloss", "cashflow", "prosandcons", "documents"
]

def parse_sql_dump(sql_file):
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    results = {}
    for table in TABLES:
        print(f"Extracting table: {table}")
        pattern = rf"INSERT INTO `?{table}`?\s*\(([^)]+)\)\s*VALUES\s*([\s\S]+?)(?=INSERT INTO|--|$)"
        matches = re.findall(pattern, content, re.IGNORECASE)

        if not matches:
            print(f"  WARNING: No data found for table '{table}'")
            continue

        columns = [c.strip().strip('`').strip('"') for c in matches[0][0].split(',')]
        rows = []

        for _, values_block in matches:
            row_pattern = r'\(([^()]*(?:\([^()]*\)[^()]*)*)\)'
            row_matches = re.findall(row_pattern, values_block)
            for row in row_matches:
                values = re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", row)
                cleaned = []
                for v in values:
                    v = v.strip().strip("'")
                    if v.upper() in ('NULL', 'null', 'Null', ''):
                        v = None
                    cleaned.append(v)
                if len(cleaned) == len(columns):
                    rows.append(cleaned)

        df = pd.DataFrame(rows, columns=columns)
        output_path = os.path.join(OUTPUT_DIR, f"{table}.csv")
        df.to_csv(output_path, index=False)
        print(f"  Saved {len(df)} rows → {output_path}")
        results[table] = df

    return results

if __name__ == "__main__":
    print("=== ETL Script 1: Extract from SQL Dump ===")
    if not os.path.exists(SQL_FILE):
        print(f"ERROR: SQL file not found at {SQL_FILE}")
        print("Please place your scriptticker.sql file in data/raw/")
    else:
        data = parse_sql_dump(SQL_FILE)
        print("\n=== Extraction Complete ===")
        for table, df in data.items():
            print(f"{table}: {len(df)} rows, {len(df.columns)} columns")
            print(f"  Columns: {list(df.columns)}\n")
