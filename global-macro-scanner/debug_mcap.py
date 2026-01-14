from storage.database import DatabaseManager
import json

db = DatabaseManager()
conn = db._get_connection()
cur = conn.cursor()

print("--- Source Breakdown ---")
cur.execute("SELECT data_source, count(*), count(market_cap_usd) FILTER (WHERE market_cap_usd > 0) as with_mcap FROM stock_fundamentals GROUP BY data_source")
for row in cur.fetchall():
    print(row)

print("\n--- FinanceDatabase Samples (Top 10) ---")
cur.execute("SELECT ticker, market_cap_usd, sector, industry FROM stock_fundamentals WHERE data_source = 'financedatabase' LIMIT 10")
for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
