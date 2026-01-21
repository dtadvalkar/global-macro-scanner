#!/usr/bin/env python3
"""
Retry failed fundamentals collection for the 214 failed tickers

This script implements:
1. Detailed error logging for each failure
2. Exponential backoff retry logic
3. Partial data recovery (market data preserved)
4. Progress tracking and reporting
"""

import asyncio
import json
import psycopg2
from ib_insync import IB, Stock, util
from config import DB_CONFIG
import sys
import io
import time
import logging
from datetime import datetime

# Force UTF-8 encoding for stdout to support emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fundamentals_retry.log'),
        logging.StreamHandler()
    ]
)

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

async def retry_ibkr_fundamentals(ticker: str, port: int, max_retries: int = 3):
    """
    Retry fundamentals collection for a single ticker with detailed logging
    """
    base_symbol = ticker.split('.')[0]

    for attempt in range(max_retries):
        logging.info(f"[{ticker}] Attempt {attempt + 1}/{max_retries}")

        # Exponential backoff: 1s, 2s, 4s
        if attempt > 0:
            delay = 2 ** (attempt - 1)
            logging.info(f"[{ticker}] Waiting {delay}s before retry...")
            await asyncio.sleep(delay)

        results = {
            "xml_snapshot": None,
            "xml_ratios": None,
            "error": None,
            "success": False,
            "attempt": attempt + 1
        }

        ib = IB()
        try:
            logging.info(f"[{ticker}] Connecting (attempt {attempt + 1})...")
            await asyncio.wait_for(ib.connectAsync('127.0.0.1', port, clientId=1000 + attempt), timeout=15)

            contract = Stock(base_symbol, 'NSE', 'INR')
            logging.info(f"[{ticker}] Qualifying contract...")
            qualified = await asyncio.wait_for(ib.qualifyContractsAsync(contract), timeout=15)

            if not qualified:
                results["error"] = "Contract not qualified"
                logging.warning(f"[{ticker}] Contract qualification failed")
                continue

            logging.info(f"[{ticker}] Contract qualified: {qualified[0].localSymbol}")

            # Try ReportSnapshot
            logging.info(f"[{ticker}] Requesting ReportSnapshot...")
            try:
                results["xml_snapshot"] = await asyncio.wait_for(
                    ib.reqFundamentalDataAsync(qualified[0], reportType='ReportSnapshot'),
                    timeout=30
                )
                logging.info(f"[{ticker}] ReportSnapshot received ({len(results['xml_snapshot'])} bytes)")
            except Exception as e:
                logging.error(f"[{ticker}] ReportSnapshot failed: {e}")
                results["error"] = f"ReportSnapshot: {e}"
                continue

            # Try ReportRatios
            logging.info(f"[{ticker}] Requesting ReportRatios...")
            try:
                results["xml_ratios"] = await asyncio.wait_for(
                    ib.reqFundamentalDataAsync(qualified[0], reportType='ReportRatios'),
                    timeout=30
                )
                logging.info(f"[{ticker}] ReportRatios received ({len(results['xml_ratios'])} bytes)")
                results["success"] = True
                logging.info(f"[{ticker}] Fundamentals collection SUCCESS!")
                break

            except Exception as e:
                logging.error(f"[{ticker}] ReportRatios failed: {e}")
                results["error"] = f"ReportRatios: {e}"
                continue

        except asyncio.TimeoutError:
            results["error"] = f"Timeout on attempt {attempt + 1}"
            logging.error(f"[{ticker}] Timeout on attempt {attempt + 1}")
        except Exception as e:
            results["error"] = f"Connection error: {e}"
            logging.error(f"[{ticker}] Connection error: {e}")
        finally:
            if ib.isConnected():
                ib.disconnect()
                logging.info(f"[{ticker}] Disconnected from IBKR")

    return results

async def update_fundamentals_in_db(ticker: str, fundamentals_data: dict):
    """Update only the fundamentals columns in raw_ibkr_nse table."""
    logging.info(f"[{ticker}] Updating database...")

    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # Update only fundamentals, preserve existing market data
    cur.execute("""
        UPDATE raw_ibkr_nse
        SET xml_snapshot = %s, xml_ratios = %s, last_updated = %s
        WHERE ticker = %s
    """, (
        fundamentals_data.get('xml_snapshot'),
        fundamentals_data.get('xml_ratios'),
        datetime.now(),
        ticker
    ))

    updated = cur.rowcount > 0
    if updated:
        logging.info(f"[{ticker}] Database updated successfully")
    else:
        logging.warning(f"[{ticker}] Ticker not found in database")

    conn.commit()
    cur.close()
    conn.close()
    return updated

def get_failed_tickers():
    """Get list of tickers that failed fundamentals collection."""
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT rib.ticker
        FROM raw_ibkr_nse rib
        LEFT JOIN stock_fundamentals sf ON rib.ticker = sf.ticker
        WHERE sf.ticker IS NULL
        ORDER BY rib.ticker
    """)

    tickers = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tickers

async def main():
    """Main retry function."""
    print("IBKR FUNDAMENTALS RETRY SCRIPT")
    print("=" * 50)
    logging.info("Starting fundamentals retry process")

    # Get failed tickers
    failed_tickers = get_failed_tickers()
    total_failed = len(failed_tickers)

    if not failed_tickers:
        print("No failed tickers found!")
        return

    print(f"Found {total_failed} tickers to retry")
    logging.info(f"Processing {total_failed} failed tickers")

    successful = 0
    failed_again = 0

    IBKR_PORT = 7496  # Live account

    for i, ticker in enumerate(failed_tickers, 1):
        print(f"\n[{i}/{total_failed}] Retrying {ticker}...")
        logging.info(f"Processing {ticker} ({i}/{total_failed})")

        # Retry fundamentals collection
        fundamentals = await retry_ibkr_fundamentals(ticker, IBKR_PORT)

        if fundamentals["success"]:
            # Update database
            updated = await update_fundamentals_in_db(ticker, fundamentals)
            if updated:
                successful += 1
                print(f"✅ {ticker} - SUCCESS!")
            else:
                failed_again += 1
                print(f"❌ {ticker} - Database update failed")
        else:
            failed_again += 1
            print(f"❌ {ticker} - Failed after retries: {fundamentals['error']}")

    # Final summary
    print(f"\n{'='*50}")
    print("RETRY RESULTS SUMMARY:")
    print(f"Total attempted: {total_failed}")
    print(f"✅ Recovered: {successful}")
    print(f"❌ Still failed: {failed_again}")
    print(".1f")

    logging.info(f"Retry complete: {successful} recovered, {failed_again} still failed")

    if successful > 0:
        print("\nNext steps:")
        print("1. Run: python scripts/etl/ibkr/flatten_ibkr_final.py")
        print("2. Check if recovered tickers now appear in stock_fundamentals")

if __name__ == "__main__":
    asyncio.run(main())