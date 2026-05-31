import nbformat as nbf

nb = nbf.v4.new_notebook()
nb.cells = [
    nbf.v4.new_markdown_cell("# B100 Intelligence - Exploratory Data Analysis\n**Bluestock Fintech Capstone Project**"),
    nbf.v4.new_code_cell("""import psycopg2, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

conn = psycopg2.connect(host='localhost', port=5432, dbname='bluestock_dw', user='tanishqyadav')
def r(q):
    with conn.cursor() as c:
        c.execute(q)
        return pd.DataFrame(c.fetchall(), columns=[d[0] for d in c.description])
print('Connected to bluestock_dw!')
companies = r('SELECT * FROM dim_company')
print(f'Total companies: {len(companies)}')
companies[['symbol','company_name','roce_pct','roe_pct']].head(10)"""),
    nbf.v4.new_markdown_cell("## Health Label Distribution"),
    nbf.v4.new_code_cell("""scores = r('SELECT * FROM fact_ml_scores')
scores['total_score'] = pd.to_numeric(scores['total_score'])
print(scores['health_label'].value_counts())
print('Top 5:')
print(scores.nlargest(5,'total_score')[['symbol','total_score','health_label']])"""),
    nbf.v4.new_markdown_cell("## Revenue Trends"),
    nbf.v4.new_code_cell("""pl = r("SELECT * FROM fact_profit_loss WHERE year_label != 'TTM'")
pl['sales'] = pd.to_numeric(pl['sales'], errors='coerce')
pl['net_profit'] = pd.to_numeric(pl['net_profit'], errors='coerce')
top5 = scores.nlargest(5,'total_score')['symbol'].tolist()
print('Top 5 companies:', top5)
for sym in top5:
    d = pl[pl['symbol']==sym]
    print(f'{sym}: {len(d)} years of data')"""),
    nbf.v4.new_markdown_cell("## Debt Analysis"),
    nbf.v4.new_code_cell("""bs = r('SELECT * FROM fact_balance_sheet')
bs['debt_to_equity'] = pd.to_numeric(bs['debt_to_equity'], errors='coerce')
latest = bs.sort_values('year_label').groupby('symbol').last().reset_index()
low_debt = latest[latest['debt_to_equity'] < 1].dropna(subset=['debt_to_equity'])
print(f'Companies with D/E < 1: {len(low_debt)}')
print(low_debt[['symbol','debt_to_equity']].sort_values('debt_to_equity').head(10))
conn.close()
print('EDA Complete!')"""),
]

with open('notebooks/01_eda.ipynb', 'w') as f:
    nbf.write(nb, f)
print('Notebook created successfully!')
