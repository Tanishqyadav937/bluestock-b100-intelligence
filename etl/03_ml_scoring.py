import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import numpy as np

DB = dict(host='localhost', port=5432, dbname='bluestock_dw', user='tanishqyadav')
conn = psycopg2.connect(**DB)
print("=== ETL Script 3: ML Health Scoring ===\n")

def read(q): 
    with conn.cursor() as cur:
        cur.execute(q)
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)

pl = read("SELECT * FROM fact_profit_loss WHERE year_label != 'TTM'")
bs = read("SELECT * FROM fact_balance_sheet WHERE year_label != 'TTM'")
cf = read("SELECT * FROM fact_cash_flow WHERE year_label != 'TTM'")
co = read("SELECT symbol, roce_pct, roe_pct FROM dim_company")

for df in [pl, bs, cf, co]:
    for col in df.columns:
        if col not in ['symbol','year_label','health_label']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

pl_latest = pl.sort_values('year_label').groupby('symbol').last().reset_index()
bs_latest = bs.sort_values('year_label').groupby('symbol').last().reset_index()
cf_latest = cf.sort_values('year_label').groupby('symbol').last().reset_index()

def cagr_3y(df, col):
    rows = []
    for sym, grp in df.groupby('symbol'):
        grp = grp.dropna(subset=[col]).sort_values('year_label')
        if len(grp) >= 4:
            start = grp.iloc[-4][col]
            end = grp.iloc[-1][col]
            if start and start > 0 and end and end > 0:
                rows.append({'symbol': sym, f'{col}_cagr_3y': ((end/start)**(1/3)-1)*100})
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['symbol', f'{col}_cagr_3y'])

sales_cagr = cagr_3y(pl, 'sales')
profit_cagr = cagr_3y(pl, 'net_profit')

df = pl_latest[['symbol','opm_pct','net_profit_margin_pct','interest_coverage']].copy()
df = df.merge(bs_latest[['symbol','debt_to_equity']], on='symbol', how='left')
df = df.merge(cf_latest[['symbol','free_cash_flow']], on='symbol', how='left')
df = df.merge(co[['symbol','roce_pct','roe_pct']], on='symbol', how='left')
df = df.merge(sales_cagr, on='symbol', how='left')
df = df.merge(profit_cagr, on='symbol', how='left')

for col in df.columns:
    if col != 'symbol':
        df[col] = pd.to_numeric(df[col], errors='coerce')

def score(series, low, mid, high, reverse=False):
    def s(v):
        if pd.isna(v): return 5
        if reverse:
            if v <= low: return 20
            elif v <= mid: return 14
            elif v <= high: return 8
            else: return 2
        else:
            if v >= high: return 20
            elif v >= mid: return 14
            elif v >= low: return 8
            else: return 2
    return series.apply(s)

df['s_roe']   = score(df['roe_pct'], 10, 15, 20)
df['s_opm']   = score(df['opm_pct'], 10, 15, 20)
df['s_dte']   = score(df['debt_to_equity'], 0.5, 1.0, 2.0, reverse=True)
df['s_scagr'] = score(df['sales_cagr_3y'], 5, 10, 15)
df['s_fcf']   = score(df['free_cash_flow'], 0, 500, 2000)
df['total_score'] = df[['s_roe','s_opm','s_dte','s_scagr','s_fcf']].sum(axis=1)

def label(s):
    if s >= 85: return 'Excellent'
    elif s >= 70: return 'Good'
    elif s >= 50: return 'Average'
    elif s >= 35: return 'Weak'
    else: return 'Poor'

df['health_label'] = df['total_score'].apply(label)

print("Health label distribution:")
print(df['health_label'].value_counts().to_string())
print("\nTop 5 companies:")
print(df.nlargest(5,'total_score')[['symbol','total_score','health_label']].to_string())

df_out = df[['symbol','total_score','health_label','s_roe','s_opm','s_dte','s_scagr','s_fcf',
             'roe_pct','opm_pct','debt_to_equity','sales_cagr_3y','net_profit_cagr_3y','free_cash_flow']].copy()
df_out.columns = ['symbol','total_score','health_label','score_roe','score_opm','score_dte',
                  'score_sales_cagr','score_fcf','roe_pct','opm_pct','debt_to_equity',
                  'sales_cagr_3y','profit_cagr_3y','free_cash_flow']
df_out = df_out.astype(str)

with conn.cursor() as cur:
    cur.execute("DROP TABLE IF EXISTS fact_ml_scores")
    cur.execute("""CREATE TABLE fact_ml_scores (
        symbol TEXT, total_score TEXT, health_label TEXT,
        score_roe TEXT, score_opm TEXT, score_dte TEXT,
        score_sales_cagr TEXT, score_fcf TEXT,
        roe_pct TEXT, opm_pct TEXT, debt_to_equity TEXT,
        sales_cagr_3y TEXT, profit_cagr_3y TEXT, free_cash_flow TEXT
    )""")
    execute_values(cur, "INSERT INTO fact_ml_scores VALUES %s",
                   [tuple(r) for r in df_out.itertuples(index=False)])
conn.commit()
conn.close()
print(f"\n✓ fact_ml_scores: {len(df_out)} companies scored")
print("=== ML Scoring Complete! ===")
