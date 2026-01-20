#!/usr/bin/env python3
"""
IBKR Market Data Collection Script

Collects IBKR market data snapshots (OHLCV, volume, bid/ask)
that changes frequently during market hours.

This script focuses ONLY on market data collection.
Fundamentals collection is handled separately by collect_ibkr_fundamentals.py

USAGE:
    python collect_ibkr_market_data.py [tickers...]
    python collect_ibkr_market_data.py --all-from-fundamentals  # Use tickers from stock_fundamentals
"""

import asyncio
import json
import psycopg2
from ib_insync import IB, Stock, util
from config import DB_CONFIG
import sys
import io
from datetime import datetime
import random

# Force UTF-8 encoding for stdout to support emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add current directory to path for imports
sys.path.append('.')

def clean_dict(obj):
    """Recursively converts NaN values to None for JSON compatibility."""
    import math
    if isinstance(obj, dict):
        return {k: clean_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_dict(x) for x in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

# --- CONFIGURATION ---
IBKR_PORT = 7496  # Live account port

async def fetch_ibkr_market_data_only(symbol: str, port: int):
    """
    Fetch ONLY market data snapshot from IBKR (no fundamentals).
    This includes: OHLCV, volume, bid/ask, etc.
    """
    from ib_insync import IB, Stock, util
    import random

    # Using a random clientId between 1000-9999 to avoid "already in use" errors
    client_id = random.randint(1000, 9999)
    print(f"   -> Connecting for market data only (ID: {client_id})...")
    ib = IB()
    results = {
        "mkt_data": None,
        "error": None,
        "success": False
    }

    try:
        print("   -> Attempting connection...")
        await asyncio.wait_for(ib.connectAsync('127.0.0.1', port, clientId=client_id), timeout=10)
        print("   -> Connected. Qualifying contract...")

        contract = Stock(symbol, 'NSE', 'INR')
        try:
            # Added timeout to qualification which can sometimes hang on poor connection
            qualified = await asyncio.wait_for(ib.qualifyContractsAsync(contract), timeout=15)
        except asyncio.TimeoutError:
            print("   ! Contract qualification timed out.")
            results["error"] = "Contract qualification timeout"
            return results

        if not qualified:
            results["error"] = "Contract not qualified"
            return results

        print(f"   -> Contract qualified. Symbol: {qualified[0].localSymbol}")

        # Market Data (Frequent Updates - Daily/Hourly)
        ib.reqMarketDataType(3)  # Delayed data for paper account
        print("   -> Requesting MktData Snapshot...")

        ticker = ib.reqMktData(qualified[0], "", snapshot=True)

        # Explicitly wait for market data to arrive
        for i in range(12):  # Wait up to 6 seconds
            await asyncio.sleep(0.5)
            if ticker.last > 0:
                print(f"   -> MktData populated: Last={ticker.last}")
                break
            if i % 4 == 0:
                print("      ... waiting for price ...")

        if ticker.last > 0:
            results["mkt_data"] = util.tree(ticker)
            results["success"] = True
            print("   ✅ Market data collection complete.")
        else:
            results["error"] = "No market data received within timeout"
            print("   ❌ No market data received.")

    except asyncio.TimeoutError:
        print("   ! IBKR Connection or request timed out.")
        results["error"] = "Timeout"
    except Exception as e:
        print(f"   ! IBKR Error: {e}")
        results["error"] = str(e)
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("   -> Disconnected from IBKR.")
    return results

async def update_market_data_in_db(ticker: str, market_data: dict):
    """Update only the market data column in raw_ibkr_nse table."""
    print(f"[DB] Updating market data for {ticker}...")

    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # Insert/update market data in dedicated table
    cur.execute("""
        INSERT INTO ibkr_market_data (ticker, market_data, last_price, bid_price, ask_price, volume, avg_volume, last_updated)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker) DO UPDATE SET
            market_data = EXCLUDED.market_data,
            last_price = EXCLUDED.last_price,
            bid_price = EXCLUDED.bid_price,
            ask_price = EXCLUDED.ask_price,
            volume = EXCLUDED.volume,
            avg_volume = EXCLUDED.avg_volume,
            last_updated = EXCLUDED.last_updated
    """, (
        ticker,
        json.dumps(clean_dict(market_data)),
        market_data.get('last'),
        market_data.get('bid'),
        market_data.get('ask'),
        market_data.get('volume'),
        market_data.get('avgVolume'),
        datetime.now()
    ))

    conn.commit()
    cur.close()
    conn.close()
    print(f"   ✅ Updated market data for {ticker}")

async def collect_market_data_for_tickers(tickers: list):
    """Collect market data for a list of tickers."""
    print(f"\n[IBKR MARKET DATA] Starting collection for {len(tickers)} tickers...")
    print("=" * 70)

    successful = 0
    failed = 0

    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Processing {ticker}...")

        # Extract base symbol (remove .NSE suffix for IBKR)
        base_symbol = ticker.split('.')[0]

        # Collect market data only
        market_data = await fetch_ibkr_market_data_only(base_symbol, IBKR_PORT)

        if market_data["success"]:
            await update_market_data_in_db(ticker, market_data["mkt_data"])
            successful += 1
        else:
            print(f"   ❌ Failed: {market_data['error']}")
            failed += 1

    print(f"\n[SUMMARY] Market Data Collection Complete:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(".1f")

def get_universe_tickers():
    """Get all tickers from our investment universe."""
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()

        # Get all tickers from FinanceDatabase (our complete universe)
        cur.execute("SELECT ticker FROM raw_fd_nse ORDER BY ticker")
        tickers = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()
        return tickers
    except Exception as e:
        print(f"Error getting universe tickers: {e}")
        return []

def get_tickers_without_market_data():
    """Get tickers that don't have market data yet."""
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()

        # Find tickers in universe that don't have market data
        cur.execute("""
            SELECT fd.ticker
            FROM raw_fd_nse fd
            LEFT JOIN raw_ibkr_nse ib ON fd.ticker = ib.ticker
            WHERE ib.mkt_data IS NULL OR ib.ticker IS NULL
            ORDER BY fd.ticker
        """)
        tickers = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()
        return tickers
    except Exception as e:
        print(f"Error getting tickers without market data: {e}")
        return []

async def main():
    """Main function to handle command line arguments."""
    import sys

    if len(sys.argv) == 1:
        print("Usage:")
        print("  python collect_ibkr_market_data.py TICKER1 TICKER2 ...")
        print("  python collect_ibkr_market_data.py --all-universe")
        print("  python collect_ibkr_market_data.py --missing-market-data")
        return

    if sys.argv[1] == "--all-universe":
        tickers = get_universe_tickers()
        print(f"Found {len(tickers)} tickers in investment universe")
    elif sys.argv[1] == "--missing-market-data":
        tickers = get_tickers_without_market_data()
        print(f"Found {len(tickers)} tickers missing market data")
    else:
        tickers = sys.argv[1:]

    if not tickers:
        print("No tickers to process!")
        return

    await collect_market_data_for_tickers(tickers)

if __name__ == "__main__":
    asyncio.run(main())