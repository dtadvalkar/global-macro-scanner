#!/usr/bin/env python3
"""
Create a dedicated market data table for IBKR market data

This separates market data (frequent updates) from fundamentals data (quarterly updates)
"""

import os
import psycopg2

os.environ['DB_PASS'] = 'postgres'

def create_market_data_table():
    """Create a dedicated table for IBKR market data"""
    conn = psycopg2.connect('dbname=market_scanner user=postgres password=postgres host=localhost port=5432')
    cur = conn.cursor()

    # Create market data table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ibkr_market_data (
            ticker TEXT PRIMARY KEY,
            market_data JSONB,
            last_price NUMERIC,
            bid_price NUMERIC,
            ask_price NUMERIC,
            volume BIGINT,
            avg_volume BIGINT,
            price_change_pct NUMERIC,
            data_timestamp TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_ibkr_market_data_ticker ON ibkr_market_data(ticker);
        CREATE INDEX IF NOT EXISTS idx_ibkr_market_data_timestamp ON ibkr_market_data(data_timestamp);
        CREATE INDEX IF NOT EXISTS idx_ibkr_market_data_updated ON ibkr_market_data(last_updated);
    """)

    print("OK Created ibkr_market_data table")

    # Migrate existing market data from raw_ibkr_nse
    cur.execute("""
        INSERT INTO ibkr_market_data (ticker, market_data, last_updated)
        SELECT ticker, mkt_data, last_updated
        FROM raw_ibkr_nse
        WHERE mkt_data IS NOT NULL
        ON CONFLICT (ticker) DO UPDATE SET
            market_data = EXCLUDED.market_data,
            last_updated = EXCLUDED.last_updated
    """)

    migrated_count = cur.rowcount
    print(f"OK Migrated {migrated_count} market data records")

    # Extract key fields from JSON for faster queries
    cur.execute("""
        UPDATE ibkr_market_data
        SET
            last_price = (market_data->>'last')::NUMERIC,
            bid_price = (market_data->>'bid')::NUMERIC,
            ask_price = (market_data->>'ask')::NUMERIC,
            volume = (market_data->>'volume')::BIGINT,
            avg_volume = (market_data->>'avgVolume')::BIGINT,
            data_timestamp = (market_data->>'timestamp')::TIMESTAMP
        WHERE market_data IS NOT NULL
    """)

    print("OK Extracted key fields from market data JSON")

    conn.commit()
    cur.close()
    conn.close()

    return migrated_count

def clean_raw_ibkr_table():
    """Remove market data from raw_ibkr_nse table (keeping only fundamentals)"""
    conn = psycopg2.connect('dbname=market_scanner user=postgres password=postgres host=localhost port=5432')
    cur = conn.cursor()

    # Remove market data column from raw_ibkr_nse
    cur.execute("ALTER TABLE raw_ibkr_nse DROP COLUMN IF EXISTS mkt_data")
    print("OK Removed mkt_data column from raw_ibkr_nse")

    # Rename table to be clearer about its purpose
    cur.execute("ALTER TABLE raw_ibkr_nse RENAME TO ibkr_fundamentals")
    print("OK Renamed raw_ibkr_nse to ibkr_fundamentals")

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    print("RESTRUCTURING IBKR DATA ARCHITECTURE")
    print("=" * 50)

    print("\n1. Creating dedicated market data table...")
    migrated = create_market_data_table()

    print("\n2. Cleaning up fundamentals table...")
    clean_raw_ibkr_table()

    print("\nOK RESTRUCTURING COMPLETE")
    print(f"   - Migrated {migrated} market data records")
    print("   - Separated fundamentals from market data")
    print("   - Created optimized table structure")

    print("\nNEW ARCHITECTURE:")
    print("   ibkr_fundamentals: Quarterly fundamentals data")
    print("   ibkr_market_data: Daily market data snapshots")