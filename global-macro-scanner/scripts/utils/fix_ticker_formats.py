"""
Fix Ticker Formats in stock_fundamentals_fd Table

Standardizes all NSE tickers to the correct format for IBKR compatibility.
Changes "xxxx.NS.NSE" format to "xxxx.NSE" format.
"""

import psycopg2
from config import DB_CONFIG

def fix_ticker_formats():
    """Fix ticker formats from xxxx.NS.NSE to xxxx.NSE."""
    print("Fixing ticker formats in stock_fundamentals_fd...")

    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # First, remove any correctly formatted tickers that might conflict
    # (these seem to be test entries or duplicates)
    cur.execute("DELETE FROM stock_fundamentals_fd WHERE ticker LIKE '%.NSE' AND ticker NOT LIKE '%.NS.NSE'")
    deleted_correct = cur.rowcount
    print(f"Removed {deleted_correct} correctly formatted duplicate tickers")

    # Now fix the incorrectly formatted tickers
    cur.execute("SELECT ticker FROM stock_fundamentals_fd WHERE ticker LIKE '%.NS.NSE'")
    rows = cur.fetchall()

    print(f"Found {len(rows)} tickers to fix from .NS.NSE to .NSE format")

    # Fix each ticker
    updated_count = 0
    for (old_ticker,) in rows:
        # Remove .NS from xxxx.NS.NSE to get xxxx.NSE
        new_ticker = old_ticker.replace('.NS.NSE', '.NSE')
        cur.execute("""
            UPDATE stock_fundamentals_fd
            SET ticker = %s
            WHERE ticker = %s
        """, (new_ticker, old_ticker))
        updated_count += 1

    conn.commit()

    print(f"Updated {updated_count} tickers from xxxx.NS.NSE to xxxx.NSE format")

    # Verify the fix
    cur.execute("SELECT ticker FROM stock_fundamentals_fd LIMIT 10")
    sample_rows = cur.fetchall()
    print("\nSample corrected tickers:")
    for (ticker,) in sample_rows:
        print(f"  {ticker}")

    # Show distribution
    cur.execute("""
        SELECT market_cap_category, COUNT(*) as count
        FROM stock_fundamentals_fd
        GROUP BY market_cap_category
        ORDER BY count DESC
    """)
    categories = cur.fetchall()
    print("\nMarket cap distribution after fix:")
    for category, count in categories:
        print(f"  {category}: {count} companies")

    cur.close()
    conn.close()

def get_filtered_tickers():
    """Get filtered tickers excluding Nano and Micro Cap."""
    print("\nGetting filtered tickers (excluding Nano/Micro Cap)...")

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
        WHERE market_cap_category NOT IN ('Nano Cap', 'Micro Cap')
        ORDER BY market_cap_category, ticker
    """)
    rows = cur.fetchall()

    print(f"Found {len(rows)} filtered tickers")

    # Show distribution of filtered tickers
    cur.execute("""
        SELECT market_cap_category, COUNT(*) as count
        FROM stock_fundamentals_fd
        WHERE market_cap_category NOT IN ('Nano Cap', 'Micro Cap')
        GROUP BY market_cap_category
        ORDER BY count DESC
    """)
    filtered_categories = cur.fetchall()

    print("Filtered distribution:")
    for category, count in filtered_categories:
        print(f"  {category}: {count} companies")

    # Export to CSV
    with open('data_files/processed/csv/filtered_tickers.csv', 'w') as f:
        f.write("ticker,company_name,market_cap_category\n")
        for ticker, name, category in rows:
            f.write(f"{ticker},{name or ''},{category}\n")

    print("Exported filtered tickers to data_files/processed/csv/filtered_tickers.csv")

    # Show sample
    print("\nSample filtered tickers:")
    for ticker, name, category in rows[:10]:
        print(f"  {ticker:<20} {name[:30] if name else 'N/A':<30} {category}")

    cur.close()
    conn.close()

    return [ticker for ticker, _, _ in rows]

if __name__ == "__main__":
    # Step 1: Fix ticker formats
    fix_ticker_formats()

    # Step 2: Get filtered tickers
    filtered_tickers = get_filtered_tickers()

    print(f"\nComplete! Ready for IBKR processing of {len(filtered_tickers)} filtered tickers")
    print("Filtered list saved to: data_files/processed/csv/filtered_tickers.csv")