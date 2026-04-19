"""
Analyze NSE Market Cap Categories and Prepare for Filtering

This script helps analyze the FinanceDatabase market cap categories and
prepares data for manual filtering. It shows:
- Distribution of market cap categories
- Sample companies by category
- Currency information
- Export options for filtering

Run this after orchestrate_ibkr_pipeline.py to analyze the data.
"""

import psycopg2
from config import DB_CONFIG
import csv

def analyze_market_cap_categories():
    """Analyze and display market cap category distribution."""
    print("📊 NSE Market Cap Category Analysis")
    print("=" * 50)

    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # Get total count
    cur.execute("SELECT COUNT(*) FROM stock_fundamentals_fd")
    total_count = cur.fetchone()[0]
    print(f"Total NSE companies: {total_count:,}")

    # Market cap category distribution
    cur.execute("""
        SELECT market_cap_category, COUNT(*) as count,
               ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
        FROM stock_fundamentals_fd
        WHERE market_cap_category IS NOT NULL
        GROUP BY market_cap_category
        ORDER BY count DESC
    """)
    categories = cur.fetchall()

    print("
📈 Market Cap Category Distribution:"    print("<15")
    for category, count, percentage in categories:
        print("<15")

    # Currency distribution
    cur.execute("""
        SELECT currency, COUNT(*) as count
        FROM stock_fundamentals_fd
        WHERE currency IS NOT NULL
        GROUP BY currency
        ORDER BY count DESC
    """)
    currencies = cur.fetchall()

    print("
💱 Currency Distribution:"    print("<10")
    for currency, count in currencies:
        print("<10")

    # Sample companies by category
    print("
📋 Sample Companies by Category:"    for category, _, _ in categories[:3]:  # Top 3 categories
        cur.execute("""
            SELECT ticker, company_name, sector
            FROM stock_fundamentals_fd
            WHERE market_cap_category = %s AND company_name IS NOT NULL
            ORDER BY company_name
            LIMIT 5
        """, (category,))

        samples = cur.fetchall()
        print(f"\n{category} ({len(samples)} samples):")
        for ticker, name, sector in samples:
            print(f"   {ticker:<15} {name[:30]:<30} {sector or 'N/A'}")

    cur.close()
    conn.close()

def export_for_filtering(filename="nse_for_filtering.csv"):
    """Export data suitable for manual filtering."""
    print(f"\n📄 Exporting data to {filename} for manual filtering...")

    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT ticker, company_name, market_cap_category, sector, industry,
               country, currency, city, exchange
        FROM stock_fundamentals_fd
        ORDER BY market_cap_category, ticker
    """)
    rows = cur.fetchall()

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ticker', 'company_name', 'market_cap_category', 'sector',
                        'industry', 'country', 'currency', 'city', 'exchange'])

        for row in rows:
            # Clean data for CSV
            clean_row = []
            for item in row:
                if item is None:
                    clean_row.append('')
                else:
                    clean_row.append(str(item).replace(',', ';'))  # Avoid CSV comma issues
            writer.writerow(clean_row)

    print(f"✅ Exported {len(rows)} records to {filename}")
    print("   💡 Use this file to:")
    print("      - Review market cap categories")
    print("      - Identify companies needing USD conversion")
    print("      - Apply your filtering criteria")
    print("      - Create filtered_tickers.csv for IBKR processing")

    cur.close()
    conn.close()

def show_filtering_recommendations():
    """Show recommendations for filtering."""
    print("
🎯 Filtering Recommendations:"    print("1. Review market cap categories - are they accurate?")
    print("2. Check currency distribution - mostly INR as expected")
    print("3. Consider: Do you trust FD's market cap categories?")
    print("4. Alternative: Convert market caps to USD using current exchange rates")
    print("5. Decision: Filter by category labels OR convert to USD values")

    print("
📊 Next Steps:"    print("1. Run: python analyze_nse_market_caps.py")
    print("2. Review exported CSV file")
    print("3. Decide on filtering approach")
    print("4. Create filtered_tickers.csv")
    print("5. Run IBKR processing for selected tickers")

if __name__ == "__main__":
    analyze_market_cap_categories()
    export_for_filtering()
    show_filtering_recommendations()
    print("\n🏆 Analysis complete! Ready for manual filtering.")