"""
Test IBKR Processing Timing with Small Batch

Tests timing with just 10-20 Mid Cap companies to validate performance.
"""

import asyncio
import time
import psycopg2
from config import DB_CONFIG
from scripts.testing.test_raw_ingestion_parallel import main_ibkr_parallel

def get_test_batch(size=20):
    """Get a small test batch of Mid Cap companies."""
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT ticker, company_name
        FROM stock_fundamentals_fd
        WHERE market_cap_category = 'Mid Cap'
        ORDER BY ticker
        LIMIT %s
    """, (size,))

    results = cur.fetchall()
    tickers = [row[0] for row in results]

    cur.close()
    conn.close()

    return tickers, results

async def test_small_batch():
    """Test timing with small batch."""
    print("Testing IBKR Processing Timing - Small Batch")
    print("=" * 50)

    # Get test batch
    test_tickers, company_data = get_test_batch(20)
    print(f"Test batch: {len(test_tickers)} Mid Cap companies")

    # Show sample
    print("\nTest companies:")
    for ticker, name in company_data[:5]:
        print(f"  {ticker}: {name}")
    if len(company_data) > 5:
        print(f"  ... and {len(company_data) - 5} more")

    print("\nStarting test...")
    start_time = time.time()

    # Run with 3 concurrent connections
    results = await main_ibkr_parallel(test_tickers, max_concurrent=3)

    end_time = time.time()
    total_seconds = end_time - start_time

    print("\nTIMING RESULTS:")
    print(f"  Companies processed: {len(test_tickers)}")
    print(f"  Total time: {total_seconds:.1f} seconds ({total_seconds/60:.1f} minutes)")
    print(f"  Average per company: {total_seconds/len(test_tickers):.1f} seconds")
    print(f"  Projected for 600: {(600/len(test_tickers)) * total_seconds:.0f} seconds ({(600/len(test_tickers)) * total_seconds/60:.1f} minutes)")

    # Check results
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM raw_ibkr_nse WHERE ticker IN %s", (tuple(test_tickers),))
    new_records = cur.fetchone()[0]

    cur.close()
    conn.close()

    print(f"  New IBKR records: {new_records}")
    print(f"  Success rate: {new_records}/{len(test_tickers)} ({new_records/len(test_tickers)*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(test_small_batch())