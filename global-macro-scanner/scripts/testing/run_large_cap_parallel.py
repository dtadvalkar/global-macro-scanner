"""
Run Parallel IBKR Processing for All 64 Large Cap NSE Companies

This script processes all Large Cap NSE companies using optimized parallel processing:
- Retrieves 64 Large Cap tickers from stock_fundamentals_fd table
- Processes them concurrently (3 at a time) for maximum speed
- Saves all results to raw_ibkr_nse table
- Expected runtime: ~2 minutes for all 64 companies

Usage: python run_large_cap_parallel.py
"""

import asyncio
import psycopg2
from config import DB_CONFIG
from scripts.testing.test_raw_ingestion_parallel import main_ibkr_parallel

def get_large_cap_tickers():
    """Get all Large Cap tickers from database."""
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
        WHERE market_cap_category = 'Large Cap'
        ORDER BY ticker
    """)

    tickers = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    return tickers

def show_large_cap_preview():
    """Show preview of Large Cap companies."""
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # Get total count
    cur.execute("SELECT COUNT(*) FROM stock_fundamentals_fd WHERE market_cap_category = 'Large Cap'")
    count = cur.fetchone()[0]

    # Show first 10 and last 5
    cur.execute("""
        (SELECT ticker, company_name, 'FIRST' as position
         FROM stock_fundamentals_fd
         WHERE market_cap_category = 'Large Cap'
         ORDER BY ticker
         LIMIT 10)
        UNION ALL
        (SELECT ticker, company_name, 'LAST' as position
         FROM stock_fundamentals_fd
         WHERE market_cap_category = 'Large Cap'
         ORDER BY ticker DESC
         LIMIT 5)
        ORDER BY position, ticker
    """)

    companies = cur.fetchall()
    cur.close()
    conn.close()

    print(f"Large Cap NSE Companies: {count}")
    print("=" * 60)

    print("First 10:")
    for i, (ticker, name, position) in enumerate(companies):
        if position == 'FIRST':
            print("2d")

    print("...")

    print("Last 5:")
    for ticker, name, position in companies:
        if position == 'LAST':
            print("2d")

async def run_large_cap_processing():
    """Main function to run Large Cap IBKR processing."""
    print("NSE Large Cap IBKR Data Collection")
    print("=" * 50)

    # Get tickers
    tickers = get_large_cap_tickers()
    print(f"Found {len(tickers)} Large Cap companies")

    # Show preview
    show_large_cap_preview()

    # Confirmation
    print(f"\nWARNING: About to process {len(tickers)} Large Cap companies via IBKR")
    print("   Expected time: ~2 minutes (parallel processing)")
    print("   Data will be saved to: raw_ibkr_nse table")
    print("   This will overwrite any existing IBKR data for these tickers")

    response = input("\nContinue? (yes/no): ").lower().strip()
    if response not in ['yes', 'y']:
        print("Cancelled by user")
        return

    print("\nStarting parallel IBKR processing...")
    print(f"   Processing {len(tickers)} tickers with 3 concurrent connections...")

    # Run parallel processing
    start_time = asyncio.get_event_loop().time()
    results = await main_ibkr_parallel(tickers, max_concurrent=3)
    end_time = asyncio.get_event_loop().time()

    total_seconds = end_time - start_time

    # Summary
    print("\nLARGE CAP PROCESSING COMPLETE")
    print(f"   Companies processed: {len(tickers)}")
    print(f"   Total time: {total_seconds:.1f} seconds ({total_seconds/60:.1f} minutes)")
    print(f"   Average per company: {total_seconds/len(tickers):.1f} seconds")
    print("   Data saved to: raw_ibkr_nse table")

    # Quick verification
    print("\nVerification:")
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM raw_ibkr_nse WHERE xml_snapshot IS NOT NULL")
    xml_count = cur.fetchone()[0]

    cur.execute("SELECT SUM(LENGTH(xml_snapshot)) FROM raw_ibkr_nse WHERE xml_snapshot IS NOT NULL")
    total_bytes = cur.fetchone()[0] or 0

    cur.close()
    conn.close()

    print(f"   Records with XML data: {xml_count}")
    print(f"   Total XML data size: {total_bytes:,} bytes ({total_bytes/1024/1024:.1f} MB)")

if __name__ == "__main__":
    asyncio.run(run_large_cap_processing())