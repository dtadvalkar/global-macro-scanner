"""
collect_historical_yfinance.py

One-time script to collect 2 years of historical OHLCV data for all tickers
in stock_fundamentals table using bulk YFinance download.

This populates prices_daily table with historical data for analysis.
Run this once, then use daily updates going forward.

USAGE:
    python collect_historical_yfinance.py
"""

import asyncio
import sys
import os
import io

# Add current directory to path for imports
sys.path.append('.')

# Force UTF-8 encoding for stdout to support emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from scripts.etl.ibkr.test_raw_ingestion import get_fundamentals_tickers, ingest_multi_ohlcv

async def collect_historical_yfinance_data():
    """Collect 2 years of historical OHLCV data for all fundamentals tickers."""

    print("="*70)
    print("HISTORICAL YFINANCE DATA COLLECTION")
    print("="*70)
    print("Purpose: One-time bulk download of 2 years OHLCV data")
    print("Target: All tickers in stock_fundamentals table")
    print("Storage: prices_daily table with source='yf'")
    print("="*70)

    # Get all tickers from fundamentals
    try:
        fundamentals_tickers = get_fundamentals_tickers()
        total_tickers = len(fundamentals_tickers)
        print(f"Found {total_tickers} tickers in stock_fundamentals")
    except Exception as e:
        print(f"❌ Error getting tickers: {e}")
        return

    if total_tickers == 0:
        print("❌ No tickers found in stock_fundamentals table!")
        return

    # Show sample tickers
    print(f"Sample tickers: {fundamentals_tickers[:5]}")
    print(f"Will convert to YFinance format: {fundamentals_tickers[0]} -> {fundamentals_tickers[0].split('.')[0]}")

    # Confirm before proceeding with large download
    print(f"\nABOUT TO DOWNLOAD: 2 years × {total_tickers} tickers = ~{total_tickers * 500} data points")
    print("This is a ONE-SHOT bulk download to avoid rate limits")
    print("Estimated time: 5-15 minutes depending on network")

    # Proceed with download
    print("\nStarting bulk download...")
    start_time = asyncio.get_event_loop().time()

    try:
        await ingest_multi_ohlcv(fundamentals_tickers, period="2y")
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return

    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time

    print(f"Duration: {duration:.1f} seconds")
    print("="*70)
    print("HISTORICAL DATA COLLECTION COMPLETE")
    print("="*70)
    print("Next steps:")
    print("   1. Check prices_daily table: python check_progress.py")
    print("   2. Validate data quality in database")
    print("   3. Ready for daily updates (design when needed)")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(collect_historical_yfinance_data())