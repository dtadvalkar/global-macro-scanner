"""
flatten_ibkr_market_data.py

Flattens IBKR market data from ibkr_market_data table into current_market_data table.
This creates structured current market state data separate from historical OHLCV bars.

Source: ibkr_market_data (dedicated market data table)
Target: current_market_data (structured current market snapshots)

Table: current_market_data (stores current market snapshots from IBKR)
- ticker (PK)
- last_price (current/last traded price)
- close_price (previous close)
- open_price (today's open)
- high_price (today's high)
- low_price (today's low)
- volume (trading volume)
- last_updated (timestamp)
"""

import json
import sys
import io
import os
from datetime import datetime, timezone

# Add project root to path so 'db' module can be found
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from db import get_db


def create_current_market_data_table():
    """Create the current_market_data table if it doesn't exist."""
    db = get_db()
    db.create_tables()
    print("[ok] current_market_data table ready")

def flatten_ibkr_market_data():
    """Extract market data from ibkr_market_data table and store in current_market_data."""

    print("[run] Starting IBKR market data flattening...")
    print("="*50)

    db = get_db()

    # 1. Get watermark from current_market_data
    result = db.query("SELECT MAX(last_updated) FROM current_market_data", fetch='one')
    watermark = result[0] if result and result[0] else datetime(1970, 1, 1)
    
    print(f"[time] Watermark (last processed): {watermark} (Type: {type(watermark)})")

    # 2. Query DELTA from ibkr_market_data (sql/etl/ibkr_market_data_delta.sql)
    rows = db.query_file('etl/ibkr_market_data_delta.sql', (watermark,))
    
    if not rows:
        # Check if there are any rows in ibkr_market_data at all for debugging
        total_ibkr = db.query("SELECT COUNT(*) FROM ibkr_market_data", fetch='one')
        print(f"  [DEBUG] Total rows in ibkr_market_data: {total_ibkr[0]}")
        sample_time = db.query("SELECT MAX(last_updated) FROM ibkr_market_data", fetch='one')
        print(f"  [DEBUG] Max last_updated in ibkr_market_data: {sample_time[0]}")

    total_rows = len(rows) if rows else 0
    print(f"[stats] Found {total_rows} new records in IBKR market data")

    if total_rows == 0:
        print("[ok] No new market data to flatten. System is up to date.")
        return

    # Process each ticker
    flattened_data = []
    processed_tickers = set()

    for row in rows:
        try:
            ticker, last_price, close_price, open_price, high_price, low_price, volume, last_updated = row

            # Clean ticker if it has double suffix like .NS.NS
            if ticker.count('.NS') > 1:
                ticker = ticker.replace('.NS.NS', '.NS')

            # Always include the record to ensure the watermark (last_updated) advances,
            # even if price data is currently missing from IBKR snapshots.
            flattened_data.append({
                'ticker': ticker,
                'last_price': last_price if last_price is not None else close_price,
                'close_price': close_price,
                'open_price': open_price,
                'high_price': high_price,
                'low_price': low_price,
                'volume': volume,
                'last_updated': last_updated
            })
            processed_tickers.add(ticker)

        except Exception as e:
            print(f"  [fail] Error processing {ticker}: {e}")
            continue

    # 3. Upsert flattened data (sql/etl/current_market_data_upsert.sql)
    if flattened_data:
        print(f"\n[db] Upserting {len(flattened_data)} records into current_market_data...")

        batch = [
            (d['ticker'], d['last_price'], d['close_price'], d['open_price'],
             d['high_price'], d['low_price'], d['volume'], d['last_updated'])
            for d in flattened_data
        ]
        db.execute_values_file('etl/current_market_data_upsert.sql', batch)

        print(f"[ok] Successfully flattened/updated {len(flattened_data)} records")

        # Show summary of the state
        result = db.query("SELECT COUNT(*) FROM current_market_data", fetch='one')
        print(f"\nSummary: current_market_data now has {result[0]} total records")
    else:
        print("[fail] No valid data to insert")

    print("\n" + "="*50)
    print("[done] IBKR market data flattening complete!")
    print("="*50)

def extract_numeric(value):
    """Extract numeric value from string or return None if invalid."""
    if value is None:
        return None
    try:
        # Handle string representations of numbers
        if isinstance(value, str):
            # Remove commas and convert
            clean_value = value.replace(',', '')
            return float(clean_value) if clean_value else None
        return float(value)
    except (ValueError, TypeError):
        return None

if __name__ == "__main__":
    create_current_market_data_table()
    flatten_ibkr_market_data()