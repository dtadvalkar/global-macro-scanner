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
    print("✅ current_market_data table ready")

def flatten_ibkr_market_data():
    """Extract market data from ibkr_market_data table and store in current_market_data."""

    print("🔄 Starting IBKR market data flattening...")
    print("="*50)

    db = get_db()

    # 1. Get watermark from current_market_data
    result = db.query("SELECT MAX(last_updated) FROM current_market_data", fetch='one')
    watermark = result[0] if result and result[0] else datetime(1970, 1, 1)
    
    print(f"🕒 Watermark (last processed): {watermark} (Type: {type(watermark)})")

    # 2. Query DELTA from ibkr_market_data
    # Use COALESCE to handle data in top-level columns or nested in JSON
    # Nested path observed: market_data -> 'Ticker' -> 'last'
    rows = db.query("""
        SELECT
            ticker,
            COALESCE(last_price, (market_data->'Ticker'->>'last')::numeric) as price,
            COALESCE(market_data->>'close', market_data->'Ticker'->>'close')::numeric as close,
            COALESCE(market_data->>'open', market_data->'Ticker'->>'open')::numeric as open,
            COALESCE(market_data->>'high', market_data->'Ticker'->>'high')::numeric as high,
            COALESCE(market_data->>'low', market_data->'Ticker'->>'low')::numeric as low,
            COALESCE(volume, (market_data->'Ticker'->>'volume')::numeric::bigint) as vol,
            last_updated
        FROM ibkr_market_data
        WHERE market_data IS NOT NULL
        AND last_updated > %s
        ORDER BY last_updated ASC
    """, (watermark,))
    
    if not rows:
        # Check if there are any rows in ibkr_market_data at all for debugging
        total_ibkr = db.query("SELECT COUNT(*) FROM ibkr_market_data", fetch='one')
        print(f"  [DEBUG] Total rows in ibkr_market_data: {total_ibkr[0]}")
        sample_time = db.query("SELECT MAX(last_updated) FROM ibkr_market_data", fetch='one')
        print(f"  [DEBUG] Max last_updated in ibkr_market_data: {sample_time[0]}")

    total_rows = len(rows) if rows else 0
    print(f"📊 Found {total_rows} new records in IBKR market data")

    if total_rows == 0:
        print("✅ No new market data to flatten. System is up to date.")
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
            print(f"  ❌ Error processing {ticker}: {e}")
            continue

    # 3. Upsert flattened data
    if flattened_data:
        print(f"\n💾 Upserting {len(flattened_data)} records into current_market_data...")

        # We use a manual UPSERT loop or a prepared statement to avoid truncating
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                upsert_sql = """
                    INSERT INTO current_market_data 
                    (ticker, last_price, close_price, open_price, high_price, low_price, volume, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker) 
                    DO UPDATE SET
                        last_price = EXCLUDED.last_price,
                        close_price = EXCLUDED.close_price,
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        volume = EXCLUDED.volume,
                        last_updated = EXCLUDED.last_updated
                    WHERE EXCLUDED.last_updated >= current_market_data.last_updated
                """
                batch = [
                    (d['ticker'], d['last_price'], d['close_price'], d['open_price'], 
                     d['high_price'], d['low_price'], d['volume'], d['last_updated'])
                    for d in flattened_data
                ]
                cur.executemany(upsert_sql, batch)
                conn.commit()
                inserted = cur.rowcount # This might not be accurate for upserts in all PG versions
        
        print(f"✅ Successfully flattened/updated {len(flattened_data)} records")

        # Show summary of the state
        result = db.query("SELECT COUNT(*) FROM current_market_data", fetch='one')
        print(f"\nSummary: current_market_data now has {result[0]} total records")
    else:
        print("❌ No valid data to insert")

    print("\n" + "="*50)
    print("🎯 IBKR market data flattening complete!")
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