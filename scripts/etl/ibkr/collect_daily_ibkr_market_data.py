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
            SELECT ticker FROM stock_fundamentals
            ORDER BY ticker
        """)
        tickers = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return tickers
    except Exception as e:
        print(f"Error getting screening universe tickers: {e}")
        return []

async def fetch_market_data_batch(ib, symbols, port):
    """Fetch market data for a batch of symbols using an existing IB connection."""
    from ib_insync import Stock, util
    
    results = {}
    for symbol in symbols:
        ticker_result = {"mkt_data": None, "contract_details": None, "error": None}
        try:
            # IBKR symbols for NSE usually don't have the .NS suffix
            clean_symbol = symbol.split('.')[0]
            contract = Stock(clean_symbol, 'NSE', 'INR')
            qualified = await ib.qualifyContractsAsync(contract)

            if not qualified:
                ticker_result["error"] = "Contract not qualified"
                results[symbol] = ticker_result
                continue

            # Market Data Only
            ib.reqMarketDataType(3)
            ticker = ib.reqMktData(qualified[0], "", snapshot=True)
            
            # Wait briefly for data
            for _ in range(10):
                await asyncio.sleep(0.1)
                if ticker.last > 0:
                    break
            
            ticker_result["mkt_data"] = util.tree(ticker)
            results[symbol] = ticker_result
            
        except Exception as e:
            ticker_result["error"] = str(e)
            results[symbol] = ticker_result
            
    return results

async def collect_daily_ibkr_market_data():
    """Collect current market data from IBKR using a persistent connection."""
    from ib_insync import IB
    import random
    
    print("="*70)
    print("DAILY IBKR MARKET DATA COLLECTION")
    print("="*70)

    try:
        screening_tickers = get_screening_universe_tickers()
        total_tickers = len(screening_tickers)
        print(f"Found {total_tickers} tickers for collection.")
    except Exception as e:
        print(f"Error getting tickers: {e}")
        return False

    if total_tickers == 0:
        return False

    ib = IB()
    client_id = random.randint(1000, 9999)
    print(f"Connecting to IBKR (Port: {IBKR_PORT}, ID: {client_id})...")
    
    try:
        await ib.connectAsync('127.0.0.1', IBKR_PORT, clientId=client_id)
        print("[OK] Connected to IBKR")
        
        success_count = 0
        error_count = 0
        db = get_db()

        for i, ticker in enumerate(screening_tickers, 1):
            if i % 10 == 0:
                print(f"Progress: {i}/{total_tickers}...")
            
            try:
                # Process single ticker with the active connection
                clean_symbol = ticker.split('.')[0]
                from ib_insync import Stock, util
                contract = Stock(clean_symbol, 'NSE', 'INR')
                qualified = await ib.qualifyContractsAsync(contract)

                if not qualified:
                    error_count += 1
                    continue

                ib.reqMarketDataType(3)
                mkt_ticker = ib.reqMktData(qualified[0], "", snapshot=True)
                
                # Wait for data (shorter wait since we are in a loop)
                for _ in range(5):
                    await asyncio.sleep(0.2)
                    if mkt_ticker.last > 0: break
                
                mkt_data = util.tree(mkt_ticker)
                
                # Save to database
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
                    json.dumps(mkt_data),
                    mkt_data.get('last'),
                    mkt_data.get('bid'),
                    mkt_data.get('ask'),
                    mkt_data.get('volume'),
                    mkt_data.get('avgVolume'),
                    datetime.now(timezone.utc)
                ))
                success_count += 1
                
            except Exception as e:
                error_count += 1
            
            # Tiny throttle
            await asyncio.sleep(0.02)

        print(f"\nCollection Complete: {success_count} success, {error_count} failed.")
        return success_count > 0

    finally:
        if ib.isConnected():
            ib.disconnect()
            print("Disconnected from IBKR")

if __name__ == "__main__":
    success = asyncio.run(collect_daily_ibkr_market_data())
    sys.exit(0 if success else 1)