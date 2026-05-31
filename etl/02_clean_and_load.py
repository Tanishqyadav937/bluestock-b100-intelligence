import pandas as pd
import numpy as np
import re

# Use psycopg2 directly instead of SQLAlchemy
import psycopg2
from psycopg2.extras import execute_values

DB = dict(host='localhost', port=5432, dbname='bluestock_dw', user='tanishqyadav')

def get_conn():
    return psycopg2.connect(**DB)

def clean_numeric(val):
    if pd.isna(val): return None
    try: return float(str(val).replace(',','').replace('%','').strip())
    except: return None

def standardize_year(y):
    if pd.isna(y): return None
    y = str(y).strip()
    if y == 'TTM': return 'TTM'
    m = re.search(r'(\d{4})', y)
    if m: return f"Mar {m.group(1)}"
    return y

def load_df(df, table, conn):
    cols = list(df.columns)
    df = df.where(pd.notnull(df), None)
    rows = [tuple(r) for r in df.itertuples(index=False)]
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        col_defs = ', '.join([f'"{c}" TEXT' for c in cols])
        cur.execute(f"CREATE TABLE {table} ({col_defs})")
        execute_values(cur, f"INSERT INTO {table} ({','.join(cols)}) VALUES %s", rows)
    conn.commit()
    print(f"✓ {table}: {len(df)} rows loaded")

RAW = "data/raw"
print("=== ETL: Clean & Load ===\n")
conn = get_conn()
print("✓ Connected to PostgreSQL\n")

# Companies
df = pd.read_csv(f"{RAW}/companies.csv")
df_out = pd.DataFrame({
    'symbol': df['id'].astype(str),
    'company_name': df['company_name'].str.strip(),
    'face_value': df['face_value'].apply(clean_numeric).astype(str),
    'book_value': df['book_value'].apply(clean_numeric).astype(str),
    'roce_pct': df['roce_percentage'].apply(clean_numeric).astype(str),
    'roe_pct': df['roe_percentage'].apply(clean_numeric).astype(str),
    'website': df['website'].astype(str),
    'nse_url': df['nse_profile'].astype(str),
    'bse_url': df['bse_profile'].astype(str),
    'sector': 'Unknown'
})
load_df(df_out, 'dim_company', conn)

# Profit & Loss
df = pd.read_csv(f"{RAW}/profitandloss.csv")
df['year_label'] = df['year'].apply(standardize_year)
for c in ['sales','expenses','operating_profit','opm_percentage','other_income',
          'interest','depreciation','profit_before_tax','tax_percentage','net_profit','eps','dividend_payout']:
    df[c] = df[c].apply(clean_numeric)
df['npm'] = df.apply(lambda r: r['net_profit']/r['sales']*100 if r['sales'] else None, axis=1)
df['icr'] = df.apply(lambda r: r['operating_profit']/r['interest'] if r['interest'] else None, axis=1)
df_out = pd.DataFrame({
    'symbol': df['company_id'].astype(str), 'year_label': df['year_label'],
    'sales': df['sales'].astype(str), 'expenses': df['expenses'].astype(str),
    'operating_profit': df['operating_profit'].astype(str), 'opm_pct': df['opm_percentage'].astype(str),
    'other_income': df['other_income'].astype(str), 'interest': df['interest'].astype(str),
    'depreciation': df['depreciation'].astype(str), 'net_profit': df['net_profit'].astype(str),
    'eps': df['eps'].astype(str), 'dividend_payout_pct': df['dividend_payout'].astype(str),
    'net_profit_margin_pct': df['npm'].astype(str), 'interest_coverage': df['icr'].astype(str)
})
load_df(df_out, 'fact_profit_loss', conn)

# Balance Sheet
df = pd.read_csv(f"{RAW}/balancesheet.csv")
df['year_label'] = df['year'].apply(standardize_year)
for c in ['equity_capital','reserves','borrowings','other_liabilities','total_liabilities',
          'fixed_assets','cwip','investments','other_asset','total_assets']:
    df[c] = df[c].apply(clean_numeric)
df['dte'] = df.apply(lambda r: r['borrowings']/((r['equity_capital'] or 0)+(r['reserves'] or 0)) if ((r['equity_capital'] or 0)+(r['reserves'] or 0))!=0 else None, axis=1)
df_out = pd.DataFrame({
    'symbol': df['company_id'].astype(str), 'year_label': df['year_label'],
    'equity_capital': df['equity_capital'].astype(str), 'reserves': df['reserves'].astype(str),
    'borrowings': df['borrowings'].astype(str), 'total_assets': df['total_assets'].astype(str),
    'debt_to_equity': df['dte'].astype(str)
})
load_df(df_out, 'fact_balance_sheet', conn)

# Cash Flow
df = pd.read_csv(f"{RAW}/cashflow.csv")
df['year_label'] = df['year'].apply(standardize_year)
for c in ['operating_activity','investing_activity','financing_activity','net_cash_flow']:
    df[c] = df[c].apply(clean_numeric)
df['fcf'] = df['operating_activity'].fillna(0) + df['investing_activity'].fillna(0)
df_out = pd.DataFrame({
    'symbol': df['company_id'].astype(str), 'year_label': df['year_label'],
    'operating_activity': df['operating_activity'].astype(str),
    'investing_activity': df['investing_activity'].astype(str),
    'financing_activity': df['financing_activity'].astype(str),
    'net_cash_flow': df['net_cash_flow'].astype(str),
    'free_cash_flow': df['fcf'].astype(str)
})
load_df(df_out, 'fact_cash_flow', conn)

# Analysis
df = pd.read_csv(f"{RAW}/analysis.csv")
df_out = pd.DataFrame({
    'symbol': df['company_id'].astype(str),
    'compounded_sales_growth': df['compounded_sales_growth'].astype(str),
    'compounded_profit_growth': df['compounded_profit_growth'].astype(str),
    'stock_price_cagr': df['stock_price_cagr'].astype(str),
    'roe': df['roe'].astype(str)
})
load_df(df_out, 'fact_analysis', conn)

# Pros & Cons
df = pd.read_csv(f"{RAW}/prosandcons.csv")
df_out = pd.DataFrame({
    'symbol': df['company_id'].astype(str),
    'pros': df['pros'].astype(str),
    'cons': df['cons'].astype(str)
})
load_df(df_out, 'fact_pros_cons', conn)

conn.close()
print("\n=== All data loaded successfully! ===")
