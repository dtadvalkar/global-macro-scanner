#!/usr/bin/env python3
"""
IBKR Fundamentals Collection Script

Collects IBKR fundamentals data (ReportSnapshot, ReportRatios, ContractDetails)
that changes infrequently (quarterly or less frequent).

This script focuses ONLY on fundamentals data collection.
Market data collection is handled separately by collect_ibkr_market_data.py

USAGE:
    python collect_ibkr_fundamentals.py [tickers...]
    python collect_ibkr_fundamentals.py --all-from-fd  # Use all tickers from FinanceDatabase
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

async def fetch_ibkr_fundamentals_only(symbol: str, port: int):
    """
    Fetch ONLY fundamentals data from IBKR (no market data).
    This includes: ReportSnapshot, ReportRatios, ContractDetails
    """
    from ib_insync import IB, Stock, util
    import random

    # Using a random clientId between 1000-9999 to avoid "already in use" errors
    client_id = random.randint(1000, 9999)
    print(f"   -> Connecting for fundamentals only (ID: {client_id})...")
    ib = IB()
    results = {
        "xml_snapshot": None,
        "xml_ratios": None,
        "contract_details": None,
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

        # Fundamental Data (One-Time - Quarterly Updates)
        print("   -> Requesting ReportSnapshot...")
        try:
            results["xml_snapshot"] = await asyncio.wait_for(
                ib.reqFundamentalDataAsync(qualified[0], reportType='ReportSnapshot'),
                timeout=20
            )
            print(f"   -> Snapshot received ({len(results['xml_snapshot'])} bytes)")
        except Exception as e:
            print(f"   ! ReportSnapshot failed: {e}")
            results["error"] = f"ReportSnapshot failed: {e}"
            return results

        print("   -> Requesting ReportRatios...")
        try:
            results["xml_ratios"] = await asyncio.wait_for(
                ib.reqFundamentalDataAsync(qualified[0], reportType='ReportRatios'),
                timeout=20
            )
            print(f"   -> Ratios received ({len(results['xml_ratios'])} bytes)")
        except Exception as e:
            print(f"   ! ReportRatios failed: {e}")
            results["error"] = f"ReportRatios failed: {e}"
            return results

        # Contract Details (Static - rarely changes)
        print("   -> Fetching Contract Details...")
        try:
            cds = await asyncio.wait_for(ib.reqContractDetailsAsync(qualified[0]), timeout=10)
            if cds:
                results["contract_details"] = util.tree(cds[0])
                print("   -> Contract details captured.")
            else:
                print("   ! No contract details received.")
                results["error"] = "No contract details"
                return results
        except Exception as e:
            print(f"   ! Contract details failed: {e}")
            results["error"] = f"Contract details failed: {e}"
            return results

        results["success"] = True
        print("   ✅ Fundamentals collection complete.")

    except asyncio.TimeoutError:
        print(f"   ! IBKR Connection or request timed out.")
        results["error"] = "Timeout"
    except Exception as e:
        print(f"   ! IBKR Error: {e}")
        results["error"] = str(e)
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("   -> Disconnected from IBKR.")
    return results

async def save_fundamentals_to_db(ticker: str, fundamentals_data: dict):
    """Save fundamentals data to ibkr_fundamentals table."""
    print(f"[DB] Saving fundamentals for {ticker}...")

    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # Update only the fundamentals columns, preserve existing market data
    cur.execute("""
        INSERT INTO ibkr_fundamentals (ticker, xml_snapshot, xml_ratios, contract_details, last_updated)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (ticker) DO UPDATE SET
            xml_snapshot = EXCLUDED.xml_snapshot,
            xml_ratios = EXCLUDED.xml_ratios,
            contract_details = EXCLUDED.contract_details,
            last_updated = EXCLUDED.last_updated
    """, (
        ticker,
        fundamentals_data.get('xml_snapshot'),
        fundamentals_data.get('xml_ratios'),
        json.dumps(clean_dict(fundamentals_data.get('contract_details'))),
        datetime.now()
    ))

    conn.commit()
    cur.close()
    conn.close()
    print(f"   ✅ Saved fundamentals for {ticker}")

async def collect_fundamentals_for_tickers(tickers: list):
    """Collect fundamentals for a list of tickers."""
    print(f"\n[IBKR FUNDAMENTALS] Starting collection for {len(tickers)} tickers...")
    print("=" * 70)

    successful = 0
    failed = 0

    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Processing {ticker}...")

        # Extract base symbol (remove .NSE suffix for IBKR)
        base_symbol = ticker.split('.')[0]

        # Collect fundamentals
        fundamentals = await fetch_ibkr_fundamentals_only(base_symbol, IBKR_PORT)

        if fundamentals["success"]:
            await save_fundamentals_to_db(ticker, fundamentals)
            successful += 1
        else:
            print(f"   ❌ Failed: {fundamentals['error']}")
            failed += 1

    print(f"\n[SUMMARY] Fundamentals Collection Complete:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(".1f"

def get_all_fd_tickers():
    """Get all tickers from raw_fd_nse table."""
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    cur.execute("SELECT ticker FROM raw_fd_nse ORDER BY ticker")
    tickers = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()
    return tickers

def get_universe_tickers():
    """Get all tickers from our investment universe (raw_fd_nse table)."""
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    cur.execute("SELECT ticker FROM raw_fd_nse ORDER BY ticker")
    tickers = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()
    return tickers

async def main():
    """Main function to handle command line arguments."""
    import sys

    if len(sys.argv) == 1:
        print("Usage:")
        print("  python collect_ibkr_fundamentals.py TICKER1 TICKER2 ...")
        print("  python collect_ibkr_fundamentals.py --all-universe")
        return

    if sys.argv[1] == "--all-universe":
        tickers = get_universe_tickers()
        print(f"Found {len(tickers)} tickers in investment universe")
    else:
        tickers = sys.argv[1:]

    await collect_fundamentals_for_tickers(tickers)

if __name__ == "__main__":
    asyncio.run(main())