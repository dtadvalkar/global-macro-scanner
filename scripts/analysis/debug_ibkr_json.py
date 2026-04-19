"""
debug_ibkr_json.py

Debug the actual JSON structure in raw_ibkr_nse.mkt_data to understand
why only 3 records are being successfully processed.
"""

from config import DB_CONFIG
import psycopg2
import json
import sys
import io

# Force UTF-8 encoding for stdout to support emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = psycopg2.connect(
    dbname=DB_CONFIG['db_name'],
    user=DB_CONFIG['db_user'],
    password=DB_CONFIG['db_pass'],
    host=DB_CONFIG['db_host'],
    port=DB_CONFIG['db_port']
)
cur = conn.cursor()

# Get a few sample records that worked vs failed
print("Checking IBKR market data JSON structure...")
print("="*60)

# Check the successful ones first
cur.execute("SELECT c.ticker, r.mkt_data FROM current_market_data c JOIN raw_ibkr_nse r ON c.ticker = r.ticker")
successful_records = cur.fetchall()

print("✅ SUCCESSFUL RECORDS (3 total):")
for i, (ticker, mkt_data_json) in enumerate(successful_records, 1):
    print(f"\n{i}. {ticker}:")
    try:
        mkt_data = json.loads(mkt_data_json) if isinstance(mkt_data_json, str) else mkt_data_json
        print(f"   JSON Type: {type(mkt_data)}")
        print(f"   Keys: {list(mkt_data.keys()) if isinstance(mkt_data, dict) else 'Not a dict'}")

        if isinstance(mkt_data, dict) and 'Ticker' in mkt_data:
            ticker_data = mkt_data['Ticker']
            print(f"   Ticker data keys: {list(ticker_data.keys()) if isinstance(ticker_data, dict) else type(ticker_data)}")
            if isinstance(ticker_data, dict):
                print(f"   Sample values: last={ticker_data.get('last')}, close={ticker_data.get('close')}, open={ticker_data.get('open')}")
    except Exception as e:
        print(f"   ERROR parsing JSON: {e}")

# Check some failed ones
cur.execute("SELECT ticker, mkt_data FROM raw_ibkr_nse WHERE mkt_data IS NOT NULL AND ticker NOT IN (SELECT ticker FROM current_market_data) LIMIT 5")
failed_records = cur.fetchall()

print(f"\n❌ FAILED RECORDS (sample of {len(failed_records)}):")
for i, (ticker, mkt_data_json) in enumerate(failed_records, 1):
    print(f"\n{i}. {ticker}:")
    try:
        mkt_data = json.loads(mkt_data_json) if isinstance(mkt_data_json, str) else mkt_data_json
        print(f"   JSON Type: {type(mkt_data)}")
        print(f"   Keys: {list(mkt_data.keys()) if isinstance(mkt_data, dict) else 'Not a dict'}")

        if isinstance(mkt_data, dict):
            if 'Ticker' in mkt_data:
                ticker_data = mkt_data['Ticker']
                print(f"   Ticker data: {ticker_data}")
            else:
                print(f"   No 'Ticker' key. Available keys: {list(mkt_data.keys())}")
                # Show first few items of the dict
                for key, value in list(mkt_data.items())[:3]:
                    print(f"      {key}: {type(value)} = {str(value)[:100]}...")
    except Exception as e:
        print(f"   ERROR parsing JSON: {e}")
        print(f"   Raw JSON (first 200 chars): {str(mkt_data_json)[:200]}")

conn.close()

print("\n" + "="*60)
print("ANALYSIS:")
print("- Compare successful vs failed JSON structures")
print("- Identify the correct field names and nesting")
print("- Fix the extraction logic accordingly")