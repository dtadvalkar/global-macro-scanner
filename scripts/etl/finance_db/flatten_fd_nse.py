"""
flatten_fd_nse.py - FinanceDatabase NSE Data Flattening

Flattens raw FinanceDatabase JSON data from raw_fd_nse table into
a structured stock_fundamentals_fd table for analysis and filtering.

Based on FinanceDatabase structure with fields like:
- Company info: name, city, country, currency, exchange
- Industry: industry, industry_group, sector
- Identifiers: isin, cusip, figi
- Financial: market_cap (Large/Mid/Small Cap)
- Narrative: summary, website
"""

import math

from db import get_db


def init_fd_fundamentals_table():
    """Creates the stock_fundamentals_fd table with FinanceDatabase-specific schema."""
    print("[DB] Creating stock_fundamentals_fd table...")
    db = get_db()
    db.execute_file('schema/stock_fundamentals_fd.sql')
    print("   stock_fundamentals_fd table ready.")

def clean_value(val):
    """Clean values for database insertion."""
    if isinstance(val, float) and math.isnan(val):
        return None
    if isinstance(val, str) and val.strip() == '':
        return None
    return val

def flatten_fd_data():
    """Extract and flatten FinanceDatabase data into stock_fundamentals_fd table."""
    print("[FD] Starting FinanceDatabase data flattening...")
    db = get_db()

    rows = db.query("SELECT ticker, raw_data FROM raw_fd_nse ORDER BY ticker")
    if not rows:
        print("   ❌ No data found in raw_fd_nse table.")
        return

    print(f"   Processing {len(rows)} tickers from FinanceDatabase...")

    # Prepare flattened data for bulk insert
    batch_data = []

    for ticker, raw_data in rows:
        try:
            # Handle different data structures in raw_fd_nse
            if isinstance(raw_data, dict):
                # Check if ticker is a key in the dict (nested structure)
                if ticker in raw_data:
                    company_data = raw_data[ticker]
                else:
                    # Direct company data dict
                    company_data = raw_data
            else:
                # Fallback for unexpected data types
                company_data = {}

            # Extract fields with proper cleaning
            record = {
                'ticker': ticker,
                'company_name': clean_value(company_data.get('name')),
                'city': clean_value(company_data.get('city')),
                'state': clean_value(company_data.get('state')),
                'country': clean_value(company_data.get('country')),
                'currency': clean_value(company_data.get('currency')),
                'exchange': clean_value(company_data.get('exchange')),
                'market': clean_value(company_data.get('market')),
                'website': clean_value(company_data.get('website')),
                'isin': clean_value(company_data.get('isin')),
                'cusip': clean_value(company_data.get('cusip')),
                'figi': clean_value(company_data.get('figi')),
                'composite_figi': clean_value(company_data.get('composite_figi')),
                'shareclass_figi': clean_value(company_data.get('shareclass_figi')),
                'industry': clean_value(company_data.get('industry')),
                'industry_group': clean_value(company_data.get('industry_group')),
                'sector': clean_value(company_data.get('sector')),
                'market_cap_category': clean_value(company_data.get('market_cap')),
                'zipcode': clean_value(company_data.get('zipcode')),
                'summary': clean_value(company_data.get('summary'))
            }

            batch_data.append((
                record['ticker'],
                record['company_name'],
                record['city'],
                record['state'],
                record['country'],
                record['currency'],
                record['exchange'],
                record['market'],
                record['website'],
                record['isin'],
                record['cusip'],
                record['figi'],
                record['composite_figi'],
                record['shareclass_figi'],
                record['industry'],
                record['industry_group'],
                record['sector'],
                record['market_cap_category'],
                record['zipcode'],
                record['summary']
            ))

        except Exception as e:
            print(f"   Error processing {ticker}: {e}")
            continue

    if batch_data:
        try:
            print(f"[DB] Bulk inserting {len(batch_data)} flattened records into stock_fundamentals_fd...")
            db.execute_values_file('etl/stock_fundamentals_fd_upsert.sql', batch_data)
            print(f"   Successfully flattened {len(batch_data)} FinanceDatabase records.")
        except Exception as e:
            print(f"   ❌ Bulk insert failed: {e}")
    else:
        print("   ⚠️ No valid data to insert.")

def audit_fd_flattened():
    """Audit the flattened FinanceDatabase data."""
    print("[AUDIT] Checking stock_fundamentals_fd table...")
    db = get_db()

    count = db.query("SELECT COUNT(*) FROM stock_fundamentals_fd", fetch='one')[0]
    print(f"   Total records: {count}")

    if count > 0:
        samples = db.query(
            "SELECT ticker, company_name, sector, industry, market_cap_category, country "
            "FROM stock_fundamentals_fd WHERE company_name IS NOT NULL LIMIT 5"
        )
        print("   Sample records:")
        for ticker, name, sector, industry, mcap, country in samples:
            print(f"      {ticker}: {name} ({sector}/{industry}) - {mcap} - {country}")

        mcap_dist = db.query(
            "SELECT market_cap_category, COUNT(*) AS count "
            "FROM stock_fundamentals_fd WHERE market_cap_category IS NOT NULL "
            "GROUP BY market_cap_category ORDER BY count DESC"
        )
        print("   Market Cap Distribution:")
        for category, cnt in mcap_dist:
            print(f"      {category}: {cnt} companies")

if __name__ == "__main__":
    init_fd_fundamentals_table()
    flatten_fd_data()
    audit_fd_flattened()
    print("\nFinanceDatabase flattening complete!")