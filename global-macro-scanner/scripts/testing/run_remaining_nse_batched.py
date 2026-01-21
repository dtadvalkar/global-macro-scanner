"""
Run Batched IBKR Processing for Remaining NSE Companies

This script processes Mid Cap and Small Cap NSE companies in smaller batches
to handle failures more gracefully and provide better progress tracking.

Large Cap (64 companies) already processed successfully.
Remaining: 548 companies (Mid Cap: 158, Small Cap: 390)
"""

import asyncio
import psycopg2
from config import DB_CONFIG
from scripts.testing.test_raw_ingestion_parallel import main_ibkr_parallel

def get_remaining_tickers(batch_size=50):
    """Get remaining tickers in batches."""
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # Get all remaining tickers
    cur.execute("""
        SELECT ticker, company_name, market_cap_category
        FROM stock_fundamentals_fd
        WHERE market_cap_category IN ('Mid Cap', 'Small Cap')
        ORDER BY market_cap_category, ticker
    """)

    all_tickers_data = cur.fetchall()
    all_tickers = [row[0] for row in all_tickers_data]

    cur.close()
    conn.close()

    # Split into batches
    batches = []
    for i in range(0, len(all_tickers), batch_size):
        batch_tickers = all_tickers[i:i+batch_size]
        batch_data = [(t, n, c) for t, n, c in all_tickers_data if t in batch_tickers]
        batches.append((batch_tickers, batch_data))

    return batches, len(all_tickers)

async def run_batch_processing(batch_num, batch_tickers, total_batches):
    """Process a single batch."""
    print(f"\n{'='*60}")
    print(f"BATCH {batch_num}/{total_batches}: Processing {len(batch_tickers)} companies")
    print(f"{'='*60}")

    try:
        results = await main_ibkr_parallel(batch_tickers, max_concurrent=3)
        return len(batch_tickers), True
    except Exception as e:
        print(f"❌ Batch {batch_num} failed: {e}")
        return 0, False

async def run_remaining_batched():
    """Main function to run batched remaining NSE processing."""
    print("NSE Mid Cap + Small Cap IBKR Data Collection (Batched)")
    print("=" * 65)

    # Get batches
    batches, total_companies = get_remaining_tickers(batch_size=50)
    print(f"Total remaining companies: {total_companies}")
    print(f"Number of batches: {len(batches)} (50 companies each)")

    # Show batch summary
    print("\nBatch Summary:")
    for i, (batch_tickers, batch_data) in enumerate(batches, 1):
        categories = {}
        for _, _, cat in batch_data:
            categories[cat] = categories.get(cat, 0) + 1

        cat_str = ", ".join([f"{cat}: {count}" for cat, count in categories.items()])
        print(f"  Batch {i}: {len(batch_tickers)} companies ({cat_str})")

    # Confirmation
    print("\nWARNING: About to process remaining NSE companies in batches")
    print(f"   Total companies: {total_companies}")
    print(f"   Number of batches: {len(batches)}")
    print("   Expected time: ~15-20 minutes total (parallel processing)")
    print("   Data will be saved to: raw_ibkr_nse table")
    print("   Can be resumed if interrupted")

    response = input("\nContinue? (yes/no): ").lower().strip()
    if response not in ['yes', 'y']:
        print("Cancelled by user")
        return

    print("\nStarting batched IBKR processing...")
    total_processed = 0
    successful_batches = 0

    start_time = asyncio.get_event_loop().time()

    for batch_num, (batch_tickers, _) in enumerate(batches, 1):
        print(f"\nProcessing Batch {batch_num}/{len(batches)}...")

        batch_processed, batch_success = await run_batch_processing(
            batch_num, batch_tickers, len(batches)
        )

        total_processed += batch_processed
        if batch_success:
            successful_batches += 1

        # Progress update
        print(f"Batch {batch_num} complete")
        print(f"   Progress: {total_processed}/{total_companies} companies")

    end_time = asyncio.get_event_loop().time()
    total_seconds = end_time - start_time

    # Final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total time: {total_seconds:.1f} seconds ({total_seconds/60:.1f} minutes)")
    print(f"Companies processed: {total_processed}")
    print(f"Batches completed: {successful_batches}/{len(batches)}")

    # Verification
    print("\nFinal Verification:")
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # Check final counts
    cur.execute("SELECT COUNT(*) FROM raw_ibkr_nse")
    final_total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM raw_ibkr_nse WHERE LENGTH(xml_snapshot) > 0")
    final_xml = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM raw_ibkr_nse WHERE mkt_data IS NOT NULL")
    final_mkt = cur.fetchone()[0]

    cur.close()
    conn.close()

    print(f"   Total IBKR records: {final_total}")
    print(f"   Records with XML fundamentals: {final_xml}")
    print(f"   Records with market data: {final_mkt}")

    new_records = final_total - 64  # Subtract original Large Cap
    print(f"   New records added: {new_records}")
    print(f"   Overall success rate: {new_records}/{total_companies} ({new_records/total_companies*100:.1f}%)" if new_records > 0 else "   No new records added")

if __name__ == "__main__":
    asyncio.run(run_remaining_batched())