"""
test_yfinance_collection.py

Test YFinance OHLCV data collection with a small subset of tickers.
"""

import asyncio
import sys
sys.path.append('.')

from scripts.etl.yfinance.test_raw_ingestion import collect_yfinance_for_ticker_list

async def test_yfinance_collection():
    """Test YFinance data collection with a small subset of tickers."""

    # Test with just 3 tickers from stock_fundamentals
    test_tickers = ["RELIANCE.NSE", "INFY.NSE", "TCS.NSE"]

    print("Testing YFinance data collection with 3 tickers...")
    print(f"Tickers: {test_tickers}")
    print("Will convert to: RELIANCE.NS, INFY.NS, TCS.NS")

    await collect_yfinance_for_ticker_list(test_tickers, period="1mo")  # Quick test with 1 month

    print("\nTest completed! Check prices_daily table for results.")

if __name__ == "__main__":
    asyncio.run(test_yfinance_collection())