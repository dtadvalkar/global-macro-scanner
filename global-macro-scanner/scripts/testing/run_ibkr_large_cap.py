"""
Run IBKR Processing for Large Cap NSE Companies Only

Processes only the 64 Large Cap companies from FinanceDatabase filtering.
This is a manageable batch for initial testing of the IBKR pipeline.
"""

import asyncio
import psycopg2
from config import DB_CONFIG
import importlib

def get_large_cap_tickers():
    """Get list of Large Cap tickers from stock_fundamentals_fd."""
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
    rows = cur.fetchall()

    tickers = [ticker for ticker, _ in rows]
    companies = [(ticker, name) for ticker, name in rows]

    cur.close()
    conn.close()

    return tickers, companies

async def run_ibkr_for_large_cap():
    """Run IBKR processing for Large Cap tickers only."""
    print("🏦 Processing Large Cap NSE Companies via IBKR")
    print("=" * 55)

    # Get Large Cap tickers
    tickers, companies = get_large_cap_tickers()
    print(f"📊 Found {len(tickers)} Large Cap companies")

    # Show sample
    print("\nSample Large Cap companies:")
    for ticker, name in companies[:10]:
        print(f"  {ticker:<15} {name}")
    if len(companies) > 10:
        print(f"  ... and {len(companies) - 10} more")

    # Confirm before proceeding
    print(f"\n⚠️  This will process {len(tickers)} tickers via IBKR")
    print("   Estimated time: 60-90 minutes (1-1.5 hours)")
    print("   Each ticker: ~60-90 seconds")

    response = input("\nContinue? (yes/no): ").lower().strip()
    if response not in ['yes', 'y']:
        print("❌ Cancelled by user")
        return

    # Import and run IBKR processing
    print("
🚀 Starting IBKR processing..."    ingestion_module = importlib.import_module("test_raw_ingestion")
    await ingestion_module.main_ibkr_only(tickers)

    print("
✅ IBKR processing complete!"    print(f"   Processed {len(tickers)} Large Cap companies")
    print("   Check raw_ibkr_nse table for results"

if __name__ == "__main__":
    asyncio.run(run_ibkr_for_large_cap())