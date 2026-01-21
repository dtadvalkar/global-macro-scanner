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
from db import get_db

# Force UTF-8 encoding for stdout to support emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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

    # Get all tickers with market data from dedicated table
    rows = db.query("""
        SELECT
            ticker,
            last_price,
            bid_price,
            ask_price,
            volume,
            market_data->>'open' as open_price,
            market_data->>'high' as high_price,
            market_data->>'low' as low_price,
            market_data->>'close' as close_price,
            last_updated
        FROM ibkr_market_data
        WHERE market_data IS NOT NULL
        ORDER BY ticker
    """)

    total_tickers = len(rows) if rows else 0

    print(f"📊 Found {total_tickers} tickers with IBKR market data")

    if total_tickers == 0:
        print("❌ No market data found to flatten")
        cur.close()
        conn.close()
        return

    # Process each ticker
    flattened_data = []

    for row in rows:
        try:
            # Data is already extracted from the query
            ticker, last_price, bid_price, ask_price, volume, open_price, high_price, low_price, close_price, last_updated = row

            # Only include if we have at least a last price
            if last_price is not None:
                flattened_data.append((
                    ticker,
                    last_price,
                    close_price,
                    open_price,
                    high_price,
                    low_price,
                    volume
                ))
                print(f"  ✓ {ticker}: last={last_price}")
            else:
                print(f"  ⚠ {ticker}: no valid price data")

        except Exception as e:
            print(f"  ❌ Error processing {ticker}: {e}")
            continue

    # Bulk insert flattened data
    if flattened_data:
        print(f"\n💾 Inserting {len(flattened_data)} records into current_market_data...")

        # Clear existing data first (since this is current market state)
        db.truncate_table("current_market_data")

        # Prepare data for bulk insert
        columns = ['ticker', 'last_price', 'close_price', 'open_price', 'high_price', 'low_price', 'volume']
        data_dicts = []
        for row in flattened_data:
            data_dicts.append(dict(zip(columns, row)))

        # Insert new data using db interface
        inserted = db.bulk_insert("current_market_data", data_dicts)
        print(f"✅ Successfully flattened {inserted} IBKR market data records")

        # Show summary
        result = db.query("SELECT COUNT(*), AVG(last_price), MIN(last_price), MAX(last_price) FROM current_market_data WHERE last_price IS NOT NULL AND last_price > 0", fetch='one')
        if result:
            count, avg_price, min_price, max_price = result
            print("\nSummary:")
            print(f"   Records: {count}")
            if count > 0:
                print(f"   Avg Price: {avg_price:.2f}" if avg_price else "   Avg Price: N/A")
                if min_price and max_price:
                    print(f"   Price Range: {min_price:.2f} - {max_price:.2f}")
                else:
                    print("   Price Range: N/A")
        else:
            print("\nSummary:")
            print("   No valid price data found")
    else:
        print("❌ No valid data to insert")

    print("\n" + "="*50)
    print("🎯 IBKR market data flattening complete!")
    print("📍 Data stored in: current_market_data table")
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