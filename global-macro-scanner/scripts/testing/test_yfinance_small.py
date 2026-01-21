"""
test_yfinance_small.py

Test YFinance bulk download with just a few major NSE tickers to verify the approach works.
"""

import asyncio
import sys
sys.path.append('.')

from scripts.etl.yfinance.test_raw_ingestion import ingest_multi_ohlcv

async def test_small_bulk():
    """Test with just 5 major NSE tickers that should exist on Yahoo Finance."""

    # Test with major, well-known NSE stocks
    test_tickers = [
        "RELIANCE.NSE",
        "TCS.NSE",
        "HDFCBANK.NSE",
        "ICICIBANK.NSE",
        "INFY.NSE"
    ]

    print("Testing YFinance bulk download with 5 major NSE tickers...")
    print(f"Tickers: {test_tickers}")
    print("Converting to .NS format: RELIANCE.NS, TCS.NS, HDFCBANK.NS, ICICIBANK.NS, INFY.NS")

    try:
        await ingest_multi_ohlcv(test_tickers, period="1y")  # Shorter period for testing
        print("Test completed successfully!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_small_bulk())