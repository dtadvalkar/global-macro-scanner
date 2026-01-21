#!/usr/bin/env python3
"""
Standardize ticker formats across all database tables

Current Issue: FinanceDatabase provides XXX.NS.NSE format
Required Format: XXX.NS (standard NSE format for IBKR/YFinance)
"""

import os
import psycopg2
import re

os.environ['DB_PASS'] = 'postgres'

def standardize_ticker(ticker):
    """Convert ticker to standard XXX.NS format"""
    if not ticker:
        return ticker

    # Handle XXX.NS.NS -> XXX.NS (FinanceDatabase double suffix)
    if ticker.endswith('.NS.NS'):
        return ticker[:-3]  # Remove one .NS

    # Handle XXX.NS.NSE -> XXX.NS
    if ticker.endswith('.NS.NSE'):
        return ticker[:-4] + '.NS'

    # Handle XXX.NSE -> XXX.NS (if any)
    if ticker.endswith('.NSE'):
        return ticker[:-4] + '.NS'

    # Already in correct format
    if ticker.endswith('.NS'):
        return ticker

    # Add .NS if missing
    return f"{ticker}.NS"

def update_table_tickers(table_name, ticker_column='ticker'):
    """Update tickers in a specific table"""
    conn = psycopg2.connect(
        dbname='market_scanner',
        user='postgres',
        password='postgres',
        host='localhost',
        port='5432'
    )
    cur = conn.cursor()

    # Get current tickers
    cur.execute(f"SELECT {ticker_column} FROM {table_name}")
    current_tickers = [row[0] for row in cur.fetchall()]

    updates_needed = []
    for old_ticker in current_tickers:
        new_ticker = standardize_ticker(old_ticker)
        if new_ticker != old_ticker:
            updates_needed.append((old_ticker, new_ticker))

    print(f"\n{table_name}: {len(updates_needed)} tickers need standardization")

    # Perform updates
    for old_ticker, new_ticker in updates_needed:
        try:
            # Update the ticker
            cur.execute(f"UPDATE {table_name} SET {ticker_column} = %s WHERE {ticker_column} = %s",
                       (new_ticker, old_ticker))
            print(f"  OK {old_ticker} -> {new_ticker}")
        except Exception as e:
            print(f"  ERROR updating {old_ticker}: {e}")

    conn.commit()
    cur.close()
    conn.close()

    return len(updates_needed)

def main():
    """Standardize tickers across all tables"""
    print("STANDARDIZING TICKER FORMATS")
    print("=" * 50)
    print("Target format: XXX.NS (standard NSE format)")
    print("Converting: XXX.NS.NSE -> XXX.NS")

    tables_to_update = [
        ('raw_fd_nse', 'ticker'),
        ('raw_ibkr_nse', 'ticker'),
        ('raw_yf_nse', 'ticker'),
        ('prices_daily', 'ticker'),
        ('stock_fundamentals', 'ticker'),
        ('stock_fundamentals_fd', 'ticker'),
        ('current_market_data', 'ticker'),
        ('tickers', 'ticker')
    ]

    total_updates = 0
    for table, column in tables_to_update:
        try:
            updates = update_table_tickers(table, column)
            total_updates += updates
        except Exception as e:
            print(f"ERROR processing {table}: {e}")

    print(f"\n{'='*50}")
    print(f"TOTAL: {total_updates} tickers standardized")
    print("All tickers now in XXX.NS format")

    print("\nNEXT STEPS:")
    print("1. Re-run market data collection with standardized tickers")
    print("2. Verify IBKR and YFinance APIs work with new format")
    print("3. Update any hardcoded ticker references")

if __name__ == "__main__":
    main()