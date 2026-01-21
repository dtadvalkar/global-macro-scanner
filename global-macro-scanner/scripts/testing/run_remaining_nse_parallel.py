"""
Run Parallel IBKR Processing for Remaining NSE Companies (Mid Cap + Small Cap)

This script processes Mid Cap and Small Cap NSE companies (548 total) using parallel processing.
Large Cap (64 companies) already processed successfully.

Expected runtime: ~17-18 minutes for 548 companies
"""

import asyncio
import psycopg2
from config import DB_CONFIG
from scripts.testing.test_raw_ingestion_parallel import main_ibkr_parallel

def get_remaining_tickers():
    """Get Mid Cap and Small Cap tickers from database."""
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT ticker, company_name, market_cap_category
        FROM stock_fundamentals_fd
        WHERE market_cap_category IN ('Mid Cap', 'Small Cap')
        ORDER BY market_cap_category, ticker
    """)

    tickers_data = cur.fetchall()
    tickers = [row[0] for row in tickers_data]

    # Group by category for reporting
    categories = {}
    for ticker, name, category in tickers_data:
        if category not in categories:
            categories[category] = []
        categories[category].append((ticker, name))

    cur.close()
    conn.close()

    return tickers, categories

def show_remaining_preview(categories):
    """Show preview of remaining companies."""
    total_count = sum(len(companies) for companies in categories.values())

    print(f"Remaining NSE Companies: {total_count}")
    print("=" * 50)

    for category, companies in categories.items():
        print(f"\n{category}: {len(companies)} companies")
        print("First 5:")
        for i, (ticker, name) in enumerate(companies[:5]):
            print(f"  {ticker:<15} {name}")
        if len(companies) > 5:
            print(f"  ... and {len(companies) - 5} more")

async def run_remaining_processing():
    """Main function to run remaining NSE processing."""
    print("NSE Mid Cap + Small Cap IBKR Data Collection")
    print("=" * 55)

    # Get tickers
    tickers, categories = get_remaining_tickers()
    print(f"Found {len(tickers)} remaining companies to process")

    # Show preview
    show_remaining_preview(categories)

    # Confirmation
    print("\nWARNING: About to process remaining NSE companies via IBKR")
    print(f"   Total companies: {len(tickers)}")
    print("   Expected time: ~17-18 minutes (parallel processing)")
    print("   Data will be saved to: raw_ibkr_nse table")
    print("   This will add to existing Large Cap data")

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
    print("\nREMAINING NSE PROCESSING COMPLETE")
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

    # Check total IBKR records now
    cur.execute("SELECT COUNT(*) FROM raw_ibkr_nse")
    total_ibkr = cur.fetchone()[0]

    # Check how many have XML data
    cur.execute("SELECT COUNT(*) FROM raw_ibkr_nse WHERE LENGTH(xml_snapshot) > 0")
    xml_count = cur.fetchone()[0]

    # Check market data availability
    cur.execute("SELECT COUNT(*) FROM raw_ibkr_nse WHERE mkt_data IS NOT NULL")
    mkt_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    print(f"   Total IBKR records: {total_ibkr}")
    print(f"   Records with XML fundamentals: {xml_count}")
    print(f"   Records with market data: {mkt_count}")

if __name__ == "__main__":
    asyncio.run(run_remaining_processing())