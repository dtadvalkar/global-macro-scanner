"""
Orchestrates the multi-source data preparation pipeline for NSE universe:
 1. Ingests raw FinanceDatabase NSE data (full universe, fast).
 2. Flattens FD data into stock_fundamentals_fd table via flatten_fd_nse.py.
 3. Exports all tickers for manual filtering (user converts to USD, applies criteria).
 4. Placeholder for IBKR processing (manual after user filtering).
 5. Audits FD table and provides summary.

NOTE: IBKR processing is deferred until after manual filtering by user.
"""

import sys
import psycopg2
from config import DB_CONFIG
import importlib
import asyncio

# ---- CONFIGURATION ----
MARKET_CAP_THRESHOLD = 1_000_000_000  # Example: Only tickers with >$1B market cap
WRITE_FILTERED_TICKERS_TO = "data_files/processed/csv/filtered_tickers.csv"  # Set to None to disable writing

# ---- 1. Ingest FinanceDatabase Data ----
def run_fd_ingestion():
    """Trigger raw FinanceDatabase NSE data collection."""
    print("[1/6] STEP 1: FinanceDatabase NSE ingestion...")
    ingestion_module = importlib.import_module("test_raw_ingestion")
    try:
        if hasattr(ingestion_module, "main_fd_only"):
            asyncio.run(ingestion_module.main_fd_only())
        else:
            print("* NOTE: main_fd_only function not found. Refactor test_raw_ingestion.py if needed.")
            pass
    except Exception as e:
        print(f"FinanceDatabase ingestion failed: {e}")

# ---- 2. Flatten FinanceDatabase Data ----
def run_flatten_fd():
    print("[2/6] STEP 2: Flatten FD raw to stock_fundamentals_fd via flatten_fd_nse.py ...")
    flatten_module = importlib.import_module("flatten_fd_nse")
    flatten_module.flatten_fd_data()

# ---- 3. Export All Tickers for Manual Filtering ----
def export_all_tickers_for_filtering(output_csv="data_files/processed/csv/all_nse_tickers.csv"):
    print("[3/5] STEP 3: Export all NSE tickers for manual filtering...")
    conn = psycopg2.connect(
        dbname=DB_CONFIG["db_name"],
        user=DB_CONFIG["db_user"],
        password=DB_CONFIG["db_pass"],
        host=DB_CONFIG["db_host"],
        port=DB_CONFIG["db_port"]
    )
    cur = conn.cursor()

    # Get all tickers with their market cap categories
    cur.execute("""
        SELECT ticker, company_name, market_cap_category, sector, industry, country, currency
        FROM stock_fundamentals_fd
        ORDER BY ticker
    """)
    rows = cur.fetchall()

    all_tickers = [ticker for ticker, _, _, _, _, _, _ in rows]
    print(f"Total NSE tickers available: {len(all_tickers)}")

    # Show market cap category distribution
    cur.execute("""
        SELECT market_cap_category, COUNT(*) as count
        FROM stock_fundamentals_fd
        WHERE market_cap_category IS NOT NULL
        GROUP BY market_cap_category
        ORDER BY count DESC
    """)
    mcap_dist = cur.fetchall()

    print("📈 Market Cap Category Distribution:")
    for category, cnt in mcap_dist:
        print(f"   {category}: {cnt} companies")

    # Show sample records
    print("\n📋 Sample records:")
    for row in rows[:10]:  # Show first 10
        ticker, name, mcap_cat, sector, industry, country, currency = row
        print(f"   {ticker:<15} {name[:25]:<25} {mcap_cat or 'N/A':<12} {sector or 'N/A':<15} {currency or 'N/A'}")

    if len(rows) > 10:
        print(f"   ... and {len(rows) - 10} more")

    if output_csv:
        print(f"Writing all tickers to {output_csv}")
        with open(output_csv, "w") as f:
            f.write("ticker,company_name,market_cap_category,sector,industry,country,currency\n")
            for ticker, name, mcap_cat, sector, industry, country, currency in rows:
                f.write(f"{ticker},{name},{mcap_cat},{sector},{industry},{country},{currency}\n")

    cur.close()
    conn.close()
    return all_tickers

# ---- 4. Placeholder for IBKR Processing ----
def run_manual_ibkr_processing():
    """Placeholder for manual IBKR processing after user filtering."""
    print("[4/5] STEP 4: IBKR processing (manual after user filtering)...")
    print("   📝 User will manually:")
    print("      1. Review data_files/processed/csv/all_nse_tickers.csv")
    print("      2. Convert market caps to USD if needed")
    print("      3. Apply filtering criteria")
    print("      4. Run IBKR ingestion for selected tickers")
    print("      5. Run IBKR flattening")

# ---- 5. Audit FD Table ----
def run_audit():
    print("[5/5] STEP 5: Audit stock_fundamentals_fd table...")
    # FD audit
    fd_flatten_module = importlib.import_module("flatten_fd_nse")
    fd_flatten_module.audit_fd_flattened()

if __name__ == "__main__":
    # Step 1: Get raw FD data for all NSE stocks
    run_fd_ingestion()

    # Step 2: Flatten FD data into structured table
    run_flatten_fd()

    # Step 3: Export all tickers for manual filtering
    all_tickers = export_all_tickers_for_filtering()

    # Step 4: Manual IBKR processing placeholder
    run_manual_ibkr_processing()

    # Step 5: Audit FD table
    run_audit()

    print("\n🎉 Pipeline preparation complete!")
    print(f"   📊 Available NSE stocks: {len(all_tickers)}")
    print("   📁 FD data in: stock_fundamentals_fd")
    print("   📄 Exported to: data_files/processed/csv/all_nse_tickers.csv")
    print("   📊 Run: python analyze_nse_market_caps.py (to analyze market cap categories)")
    print("   👤 Next: Manually filter tickers, then run IBKR processing")
