import sys
import os
from datetime import datetime, timezone

# Add project root to path
root_dir = os.path.abspath(os.curdir)
sys.path.append(root_dir)

from db import get_db

def debug_query():
    db = get_db()
    
    # 1. Get watermark
    result = db.query("SELECT MAX(last_updated) FROM current_market_data", fetch='one')
    watermark = result[0] if result and result[0] else datetime(1970, 1, 1)
    
    print(f"DEBUG: Watermark from current_market_data: {watermark} (Type: {type(watermark)})")
    
    # 2. Get max from ibkr_market_data
    max_ibkr = db.query("SELECT MAX(last_updated) FROM ibkr_market_data", fetch='one')
    print(f"DEBUG: Max last_updated in ibkr_market_data: {max_ibkr[0]} (Type: {type(max_ibkr[0])})")
    
    # 3. Try the query
    q = """
        SELECT COUNT(*)
        FROM ibkr_market_data
        WHERE market_data IS NOT NULL
        AND last_updated > %s
    """
    count = db.query(q, (watermark,), fetch='one')
    print(f"DEBUG: Rows found with query: {count[0]}")
    
    # 4. If count is 0, try without market_data check
    if count[0] == 0:
        count_all = db.query("SELECT COUNT(*) FROM ibkr_market_data WHERE last_updated > %s", (watermark,), fetch='one')
        print(f"DEBUG: Rows found WITHOUT market_data check: {count_all[0]}")

if __name__ == "__main__":
    debug_query()
