from config import DB_CONFIG
import psycopg2

# Map config keys to psycopg2 expected keys
conn = psycopg2.connect(
    dbname=DB_CONFIG['db_name'],
    user=DB_CONFIG['db_user'],
    password=DB_CONFIG['db_pass'],
    host=DB_CONFIG['db_host'],
    port=DB_CONFIG['db_port']
)
cur = conn.cursor()

print('Current prices_daily content:')
cur.execute("SELECT DISTINCT ticker, source, COUNT(*) as days FROM prices_daily GROUP BY ticker, source ORDER BY ticker")
rows = cur.fetchall()
for row in rows:
    print(f'  {row[0]} ({row[1]}): {row[2]} days')

cur.execute("SELECT COUNT(*) FROM prices_daily WHERE source='yf'")
yf_total = cur.fetchone()[0]
print(f'Total YFinance rows: {yf_total}')

cur.execute("SELECT source, COUNT(*) FROM prices_daily GROUP BY source")
source_rows = cur.fetchall()
print('Rows by source:')
for source, count in source_rows:
    print(f'  {source}: {count} rows')

cur.execute("SELECT COUNT(*) FROM prices_daily")
total_all = cur.fetchone()[0]
print(f'Total rows in prices_daily: {total_all}')

conn.close()