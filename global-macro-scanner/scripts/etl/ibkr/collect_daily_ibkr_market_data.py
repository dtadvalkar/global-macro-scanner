"""
collect_daily_ibkr_market_data.py

FREQUENT MARKET DATA COLLECTION: Daily/hourly script to collect CURRENT MARKET DATA ONLY from IBKR
for all NSE tickers in stock_fundamentals table.

ARCHITECTURE:
- This script collects FREQUENTLY CHANGING market data (OHLCV, volume, bid/ask)
- Fundamentals data is collected separately by collect_ibkr_fundamentals.py (quarterly)
- Market data updates the mkt_data column in raw_ibkr_nse table

⚡ FAST & EFFICIENT:
- Only requests market data snapshots (OHLCV, volume)
- Preserves existing fundamentals data (xml_snapshot, xml_ratios, contract_details)
- Designed for frequent execution (daily/hourly during market hours)

SCHEDULING:
- Run daily before screening to ensure fresh data
- Can run hourly during market hours for real-time data
- Fundamentals: Quarterly via schedule_quarterly_fundamentals.py

USAGE:
    python collect_daily_ibkr_market_data.py
"""

import asyncio
import sys
import os
# import io  # Removed due to subprocess issues
import json
import time
from datetime import datetime, timezone

# Add project root to path for imports
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from db import get_db

# UTF-8 encoding removed due to subprocess issues

from config import DB_CONFIG
import psycopg2
# Local definitions to avoid import issues
IBKR_PORT = 7496  # Live account port

def get_universe_tickers():
    """Get all tickers from raw_fd_nse universe table."""
    try:
        conn = psycopg2.connect(dbname=DB_CONFIG['db_name'], user=DB_CONFIG['db_user'], password=DB_CONFIG['db_pass'], host=DB_CONFIG['db_host'], port=DB_CONFIG['db_port'])
        cur = conn.cursor()
        cur.execute("SELECT ticker FROM raw_fd_nse ORDER BY ticker")
        tickers = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return tickers
    except Exception as e:
        print(f"Error getting universe tickers: {e}")
        return []

def get_screening_universe_tickers():
    """Get all tickers from stock_fundamentals_fd for valid market cap categories."""
    try:
        conn = psycopg2.connect(dbname=DB_CONFIG['db_name'], user=DB_CONFIG['db_user'], password=DB_CONFIG['db_pass'], host=DB_CONFIG['db_host'], port=DB_CONFIG['db_port'])
        cur = conn.cursor()
        cur.execute("""
            SELECT ticker FROM stock_fundamentals_fd
            WHERE market_cap_category IN ('Large Cap','Mid Cap','Small Cap')
            ORDER BY ticker
        """)
        tickers = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return tickers
    except Exception as e:
        print(f"Error getting screening universe tickers: {e}")
        return []

async def fetch_ibkr_market_data_only(symbol: str, port: int):
    """Fetch only market data snapshot from IBKR (no fundamentals - we already have them)"""
    from ib_insync import IB, Stock, util
    import random

    # Using a random clientId between 1000-9999 to avoid "already in use" errors
    client_id = random.randint(1000, 9999)
    print(f"   -> Connecting for market data only (ID: {client_id})...")
    ib = IB()
    results = {"mkt_data": None, "contract_details": None, "error": None}

    try:
        print("   -> Connecting...")
        await asyncio.wait_for(ib.connectAsync('127.0.0.1', port, clientId=client_id), timeout=10)

        contract = Stock(symbol, 'NSE', 'INR')
        qualified = await asyncio.wait_for(ib.qualifyContractsAsync(contract), timeout=15)

        if not qualified:
            results["error"] = "Contract not qualified"
            return results

        print(f"   -> Contract qualified: {qualified[0].localSymbol}")

        # Market Data Only (what we need for daily screening)
        ib.reqMarketDataType(3)
        print("   -> Requesting MktData Snapshot...")
        ticker = ib.reqMktData(qualified[0], "", snapshot=True)

        # Wait for market data to arrive
        for i in range(12):
            await asyncio.sleep(0.5)
            if ticker.last > 0:
                print(f"   -> MktData received: Last={ticker.last}")
                break
            if i % 4 == 0: print("      ... waiting for price ...")

        results["mkt_data"] = util.tree(ticker)

        # Optional: Contract details for validation
        print("   -> Fetching Contract Details...")
        try:
            cds = await asyncio.wait_for(ib.reqContractDetailsAsync(qualified[0]), timeout=5)
            if cds:
                results["contract_details"] = util.tree(cds[0])
                print("   -> Contract details captured.")
        except:
            print("   -> Contract details failed (non-critical)")

    except asyncio.TimeoutError:
        print(f"   -> IBKR Connection or request timed out.")
        results["error"] = "Timeout"
    except Exception as e:
        print(f"   -> IBKR Error: {e}")
        results["error"] = str(e)
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("   -> Disconnected from IBKR.")
    return results

async def collect_daily_ibkr_market_data():
    """Collect current market data from IBKR for all fundamentals tickers."""

    print("="*70)
    print("DAILY IBKR MARKET DATA COLLECTION")
    print("="*70)
    print("Purpose: Collect current market snapshots for all universe tickers")
    print("Target: All tickers in raw_fd_nse table (1,936 tickers)")
    print("Storage: ibkr_market_data table (refreshed daily)")
    print("="*70)

    # Get high quality screening universe tickers
    try:
        screening_tickers = get_screening_universe_tickers()
        total_tickers = len(screening_tickers)
        print(f"Found {total_tickers} tickers in stock_fundamentals")
    except Exception as e:
        print(f"❌ Error getting tickers: {e}")
        return False

    if total_tickers == 0:
        print("❌ No tickers found in stock_fundamentals table!")
        return False

    # Show sample tickers
    print(f"Sample tickers: {screening_tickers[:3]}...")
    print(f"All tickers will be converted to IBKR format (.NSE suffix)")

    # Check market hours (rough check)
    now = datetime.now(timezone.utc)
    # NSE is typically 9:15 AM to 3:30 PM IST (3:45 to 10:00 UTC)
    # This is a rough check - in production you'd want more sophisticated market hours logic
    if not (3 <= now.hour <= 10):
        print("⚠️  WARNING: NSE market may be closed")
        print("   Current UTC time:", now.strftime("%H:%M UTC"))
        print("   NSE trading hours: ~03:45-10:00 UTC")
        print("   Collection may return stale/limited data")

    print(f"\nStarting IBKR market data collection for {total_tickers} tickers...")
    print(f"IBKR Port: {IBKR_PORT}")
    start_time = asyncio.get_event_loop().time()

    try:
        success_count = 0
        error_count = 0

        # Process tickers sequentially to avoid overwhelming IBKR
        for i, ticker in enumerate(screening_tickers, 1):
            print(f"\n[{i}/{total_tickers}] Processing {ticker}...")

            try:
                # Convert ticker format (remove .NSE if present, IBKR expects base symbol)
                ibkr_symbol = ticker.split('.')[0]  # Remove .NSE suffix
                print(f"   Using IBKR symbol: {ibkr_symbol}")

                # Fetch IBKR market data only (no fundamentals - we already have them)
                ibkr_raw = await fetch_ibkr_market_data_only(ibkr_symbol, IBKR_PORT)

                if ibkr_raw.get('error'):
                    print(f"   ❌ Error: {ibkr_raw['error']}")
                    error_count += 1
                    continue

                if ibkr_raw.get('mkt_data'):
                    # Save to database using db interface
                    db = get_db()

                    # Insert/update market data in dedicated table
                    db.execute("""
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
                        json.dumps(ibkr_raw.get('mkt_data')) if ibkr_raw.get('mkt_data') else None,
                        ibkr_raw.get('mkt_data', {}).get('last'),
                        ibkr_raw.get('mkt_data', {}).get('bid'),
                        ibkr_raw.get('mkt_data', {}).get('ask'),
                        ibkr_raw.get('mkt_data', {}).get('volume'),
                        ibkr_raw.get('mkt_data', {}).get('avgVolume'),
                        datetime.now()
                    ))

                    print("   ✅ Data saved to ibkr_market_data")
                    success_count += 1
                else:
                    print("   ⚠️  No market data received")
                    error_count += 1

            except Exception as e:
                print(f"   ❌ Error processing {ticker}: {e}")
                error_count += 1

            # Small delay between requests to be respectful to IBKR
            await asyncio.sleep(0.5)

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        print(f"\nDuration: {duration:.1f} seconds")
        print("="*70)
        print("IBKR MARKET DATA COLLECTION COMPLETE")
        print("="*70)
        print(f"✅ Successfully collected data for {success_count}/{total_tickers} tickers")
        print(f"❌ Errors: {error_count} tickers")

        if success_count > 0:
            print("\nNext step: Run flatten_ibkr_market_data.py to update current_market_data table")
            return True
        else:
            print("❌ No data collected - check IBKR connection and market hours")
            return False

    except Exception as e:
        print(f"❌ Collection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(collect_daily_ibkr_market_data())
    sys.exit(0 if success else 1)