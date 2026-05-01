from db import get_db

db = get_db()

print("--- Database Status ---")
res = db.query("SELECT count(*) FROM tickers WHERE market = %s", ('NSE',), fetch='one')
print(f"Tickers (NSE): {res[0] if res else 0}")

print(f"Stock Fundamentals: {db.get_fundamentals_count()} rows (IBKR-curated)")
print(f"Prices Daily: {db.get_price_data_count()} rows")
print(f"Current Market Data: {db.get_current_market_count()} rows")
