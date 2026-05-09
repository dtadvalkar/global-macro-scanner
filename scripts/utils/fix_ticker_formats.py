"""
Fix Ticker Formats in stock_fundamentals_fd Table

Standardizes all NSE tickers to the correct format for IBKR compatibility.
Changes "xxxx.NS.NSE" format to "xxxx.NSE" format.

Destructive SQL (DELETE, UPDATE) is externalized to sql/etl/. Diagnostic
SELECTs are kept inline.
"""

from db import get_db


def fix_ticker_formats():
    """Fix ticker formats from xxxx.NS.NSE to xxxx.NSE."""
    print("Fixing ticker formats in stock_fundamentals_fd...")
    db = get_db()

    # Remove correctly formatted rows that conflict with the rename below.
    deleted_correct = db.execute_file(
        'etl/stock_fundamentals_fd_delete_correct_format.sql'
    )
    print(f"Removed {deleted_correct} correctly formatted duplicate tickers")

    # Drive the rename off the legacy-format ticker list.
    rows = db.query_file('etl/stock_fundamentals_fd_select_legacy_format.sql')
    print(f"Found {len(rows)} tickers to fix from .NS.NSE to .NSE format")

    updated_count = 0
    for (old_ticker,) in rows:
        new_ticker = old_ticker.replace('.NS.NSE', '.NSE')
        db.execute_file(
            'etl/stock_fundamentals_fd_rename_ticker.sql',
            (new_ticker, old_ticker),
        )
        updated_count += 1

    print(f"Updated {updated_count} tickers from xxxx.NS.NSE to xxxx.NSE format")

    sample_rows = db.query("SELECT ticker FROM stock_fundamentals_fd LIMIT 10")
    print("\nSample corrected tickers:")
    for (ticker,) in sample_rows:
        print(f"  {ticker}")

    categories = db.query(
        "SELECT market_cap_category, COUNT(*) AS count "
        "FROM stock_fundamentals_fd GROUP BY market_cap_category ORDER BY count DESC"
    )
    print("\nMarket cap distribution after fix:")
    for category, count in categories:
        print(f"  {category}: {count} companies")


def get_filtered_tickers():
    """Get filtered tickers excluding Nano and Micro Cap."""
    print("\nGetting filtered tickers (excluding Nano/Micro Cap)...")
    db = get_db()

    rows = db.query(
        "SELECT ticker, company_name, market_cap_category "
        "FROM stock_fundamentals_fd "
        "WHERE market_cap_category NOT IN ('Nano Cap', 'Micro Cap') "
        "ORDER BY market_cap_category, ticker"
    )
    print(f"Found {len(rows)} filtered tickers")

    filtered_categories = db.query(
        "SELECT market_cap_category, COUNT(*) AS count "
        "FROM stock_fundamentals_fd "
        "WHERE market_cap_category NOT IN ('Nano Cap', 'Micro Cap') "
        "GROUP BY market_cap_category ORDER BY count DESC"
    )
    print("Filtered distribution:")
    for category, count in filtered_categories:
        print(f"  {category}: {count} companies")

    with open('data_files/processed/csv/filtered_tickers.csv', 'w') as f:
        f.write("ticker,company_name,market_cap_category\n")
        for ticker, name, category in rows:
            f.write(f"{ticker},{name or ''},{category}\n")

    print("Exported filtered tickers to data_files/processed/csv/filtered_tickers.csv")
    print("\nSample filtered tickers:")
    for ticker, name, category in rows[:10]:
        print(f"  {ticker:<20} {(name[:30] if name else 'N/A'):<30} {category}")

    return [ticker for ticker, _, _ in rows]


if __name__ == "__main__":
    fix_ticker_formats()
    filtered_tickers = get_filtered_tickers()
    print(f"\nComplete! Ready for IBKR processing of {len(filtered_tickers)} filtered tickers")
    print("Filtered list saved to: data_files/processed/csv/filtered_tickers.csv")
