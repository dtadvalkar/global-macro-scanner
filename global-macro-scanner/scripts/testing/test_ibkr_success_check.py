"""
Check which Large Cap companies are actually available in IBKR
"""

import psycopg2
from config import DB_CONFIG

def check_large_cap_availability():
    """Check which Large Cap companies have IBKR data."""
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # Get all Large Cap tickers
    cur.execute("""
        SELECT ticker, company_name
        FROM stock_fundamentals_fd
        WHERE market_cap_category = 'Large Cap'
        ORDER BY ticker
    """)

    large_cap_tickers = cur.fetchall()

    # Check which ones have IBKR data
    cur.execute("""
        SELECT ticker, LENGTH(xml_snapshot) as xml_size,
               CASE WHEN xml_snapshot IS NOT NULL THEN 1 ELSE 0 END as has_xml,
               CASE WHEN mkt_data IS NOT NULL THEN 1 ELSE 0 END as has_mkt
        FROM raw_ibkr_nse
        WHERE ticker IN (
            SELECT ticker FROM stock_fundamentals_fd WHERE market_cap_category = 'Large Cap'
        )
        ORDER BY ticker
    """)

    ibkr_data = cur.fetchall()
    ibkr_tickers = {row[0] for row in ibkr_data}

    cur.close()
    conn.close()

    print("=== LARGE CAP IBKR AVAILABILITY CHECK ===")
    print(f"Total Large Cap companies: {len(large_cap_tickers)}")
    print(f"Companies with IBKR data: {len(ibkr_data)}")
    print(f"Success rate: {len(ibkr_data)}/{len(large_cap_tickers)} ({len(ibkr_data)/len(large_cap_tickers)*100:.1f}%)")

    if ibkr_data:
        print("\nSuccessful companies:")
        total_xml_size = 0
        for ticker, xml_size, has_xml, has_mkt in ibkr_data:
            xml_size_val = xml_size or 0
            xml_mb = xml_size_val / 1024 / 1024
            print(f"  {ticker}: {xml_size_val:,} bytes ({xml_mb:.2f} MB) - XML:{has_xml}, Mkt:{has_mkt}")
            total_xml_size += xml_size_val

        print(f"\nTotal XML data: {total_xml_size:,} bytes ({total_xml_size/1024/1024:.2f} MB)")

    # Show companies without IBKR data
    missing_companies = [(t, n) for t, n in large_cap_tickers if t not in ibkr_tickers]

    if missing_companies:
        print(f"\nCompanies NOT available in IBKR ({len(missing_companies)}):")
        for i, (ticker, name) in enumerate(missing_companies[:20]):  # Show first 20
            print(f"  {ticker}: {name}")
        if len(missing_companies) > 20:
            print(f"  ... and {len(missing_companies) - 20} more")

if __name__ == "__main__":
    check_large_cap_availability()