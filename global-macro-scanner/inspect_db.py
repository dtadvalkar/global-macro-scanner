
from storage.database import DatabaseManager

db = DatabaseManager()
conn = db._get_connection()

print("--- Database Status ---")
with conn.cursor() as cur:
    cur.execute("SELECT count(*) FROM tickers WHERE market='NSE'")
    res = cur.fetchone()
    nse_tickers = res[0] if res else 0
    print(f"Tickers (NSE): {nse_tickers}")

    # Check stock_fundamentals
    try:
        cur.execute("SELECT count(*) FROM stock_fundamentals")
        res = cur.fetchone()
        fundamentals = res[0] if res else 0
        
        cur.execute("SELECT count(*) FROM stock_fundamentals WHERE is_active = FALSE")
        res = cur.fetchone()
        inactive = res[0] if res else 0
        
        print(f"Stock Fundamentals: {fundamentals} total rows")
        print(f"  - Active: {fundamentals - inactive}")
        print(f"  - Inactive/Ignored: {inactive}")
    except Exception as e:
        print(f"Stock Fundamentals: Not found or error ({e})")
