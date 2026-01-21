"""
Parallel IBKR Processing for Multiple Tickers

Uses asyncio to process multiple tickers concurrently for better performance.
"""

import asyncio
import json
import random
import psycopg2
from psycopg2.extras import execute_values
from ib_insync import IB, Stock, util
from config import DB_CONFIG
import math

def clean_dict(obj):
    """Recursively converts NaN values to None for JSON compatibility."""
    if isinstance(obj, dict):
        return {k: clean_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_dict(x) for x in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

def get_suffixes(master_id: str):
    base = master_id.split('.')[0]
    return {
        "master": master_id,
        "ibkr": base,
        "yf": f"{base}.NS",
        "fd": f"{base}.NS" # FinanceDatabase NSE stocks use .NS suffix
    }

async def fetch_ibkr_raw_parallel(master_ticker: str, port: int, semaphore: asyncio.Semaphore):
    """Fetch IBKR data for a single ticker with semaphore for concurrency control."""
    async with semaphore:  # Limit concurrent connections
        client_id = random.randint(1000, 9999)
        suffixes = get_suffixes(master_ticker)
        ibkr_symbol = suffixes['ibkr']  # Extract base symbol for IBKR

        print(f"[IBKR] Processing: {master_ticker} -> {ibkr_symbol} (ID: {client_id})")

        ib = IB()
        results = {"xml_snapshot": None, "xml_ratios": None, "mkt_data": None, "contract_details": None, "error": None}

        try:
            await asyncio.wait_for(ib.connectAsync('127.0.0.1', port, clientId=client_id), timeout=10)

            contract = Stock(ibkr_symbol, 'NSE', 'INR')
            qualified = await asyncio.wait_for(ib.qualifyContractsAsync(contract), timeout=15)

            if not qualified:
                results["error"] = "Contract not qualified"
                return master_ticker, results

            # Get fundamentals data
            results["xml_snapshot"] = await asyncio.wait_for(
                ib.reqFundamentalDataAsync(qualified[0], reportType='ReportSnapshot'),
                timeout=30
            )

            results["xml_ratios"] = await asyncio.wait_for(
                ib.reqFundamentalDataAsync(qualified[0], reportType='ReportRatios'),
                timeout=30
            )

            # Get market data snapshot
            ib.reqMarketDataType(3)
            ticker = ib.reqMktData(qualified[0], "", snapshot=True)

            # Wait for market data (reduced from 12 to 6 iterations)
            for i in range(6):
                await asyncio.sleep(0.5)
                if ticker.last > 0:
                    break

            results["mkt_data"] = util.tree(ticker)
            results["contract_details"] = util.tree(qualified[0])

        except Exception as e:
            results["error"] = str(e)
        finally:
            if ib.isConnected():
                ib.disconnect()

        return master_ticker, results

async def save_ibkr_results(results_dict):
    """Save IBKR results to database."""
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    batch_data = []
    for ticker, data in results_dict.items():
        batch_data.append((
            ticker,
            data.get('xml_snapshot'),
            data.get('xml_ratios'),
            json.dumps(clean_dict(data.get('mkt_data'))),
            json.dumps(clean_dict(data.get('contract_details')))
        ))

    execute_values(
        cur,
        """
        INSERT INTO raw_ibkr_nse (ticker, xml_snapshot, xml_ratios, mkt_data, contract_details)
        VALUES %s
        ON CONFLICT (ticker) DO UPDATE SET
            xml_snapshot = EXCLUDED.xml_snapshot,
            xml_ratios = EXCLUDED.xml_ratios,
            mkt_data = EXCLUDED.mkt_data,
            contract_details = EXCLUDED.contract_details,
            last_updated = CURRENT_TIMESTAMP
        """,
        batch_data
    )

    conn.commit()
    cur.close()
    conn.close()

async def main_ibkr_parallel(tickers, max_concurrent=5):
    """
    Process multiple tickers in parallel.

    Args:
        tickers: List of ticker symbols (e.g., ['RELIANCE.NSE', 'TCS.NSE'])
        max_concurrent: Maximum concurrent IBKR connections (default: 5)
    """
    print(f"Starting parallel IBKR processing for {len(tickers)} tickers")
    print(f"   Max concurrent connections: {max_concurrent}")

    semaphore = asyncio.Semaphore(max_concurrent)
    port = 7496

    # Create tasks for all tickers (pass master ticker, not IBKR symbol)
    tasks = [
        fetch_ibkr_raw_parallel(master_ticker, port, semaphore)
        for master_ticker in tickers
    ]

    # Run all tasks concurrently
    print(f"   Executing {len(tasks)} tasks...")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    results_dict = {}
    success_count = 0

    for result in results:
        if isinstance(result, Exception):
            print(f"   Task failed: {result}")
            continue

        master_ticker, data = result
        results_dict[master_ticker] = data

        if data.get('error'):
            print(f"   {master_ticker}: {data['error']}")
        else:
            xml_size = len(data.get('xml_snapshot') or '')
            print(f"   {master_ticker}: {xml_size} bytes")
            success_count += 1

    # Save to database
    await save_ibkr_results(results_dict)

    print("\nSUMMARY:")
    print(f"   Total tickers: {len(tickers)}")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {len(tickers) - success_count}")

    return results_dict

# For testing
if __name__ == "__main__":
    # Test with a few tickers
    test_tickers = ['RELIANCE.NSE', 'TCS.NSE', 'INFY.NSE']
    asyncio.run(main_ibkr_parallel(test_tickers, max_concurrent=3))