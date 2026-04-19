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

import psycopg2
from psycopg2.extras import execute_values
from config import DB_CONFIG
import math

def init_fd_fundamentals_table():
    """Creates the stock_fundamentals_fd table with FinanceDatabase-specific schema."""
    print("[DB] Creating stock_fundamentals_fd table...")

    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # FinanceDatabase-specific flattened schema
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_fundamentals_fd (
            ticker                   TEXT PRIMARY KEY,

            -- Basic Company Information
            company_name             TEXT,
            city                     TEXT,
            state                    TEXT,
            country                  TEXT,
            currency                 TEXT,
            exchange                 TEXT,
            market                   TEXT,
            website                  TEXT,

            -- 🆔 Identifiers
            isin                     TEXT,
            cusip                    TEXT,
            figi                     TEXT,
            composite_figi           TEXT,
            shareclass_figi          TEXT,

            -- 🏭 Industry Classification
            industry                 TEXT,
            industry_group           TEXT,
            sector                   TEXT,

            -- 💰 Financial Information
            market_cap_category      TEXT,  -- "Large Cap", "Mid Cap", "Small Cap"
            zipcode                  TEXT,

            -- 📝 Company Description
            summary                  TEXT,

            -- 🕒 Metadata
            last_updated             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
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

    # Connect to database
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # Get all raw FD data
    cur.execute("SELECT ticker, raw_data FROM raw_fd_nse ORDER BY ticker")
    rows = cur.fetchall()

    if not rows:
        print("   ❌ No data found in raw_fd_nse table.")
        cur.close()
        conn.close()
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

    # Bulk insert the flattened data
    if batch_data:
        try:
            print(f"[DB] Bulk inserting {len(batch_data)} flattened records into stock_fundamentals_fd...")
            execute_values(
                cur,
                """
                INSERT INTO stock_fundamentals_fd (
                    ticker, company_name, city, state, country, currency, exchange, market, website,
                    isin, cusip, figi, composite_figi, shareclass_figi,
                    industry, industry_group, sector, market_cap_category, zipcode, summary
                ) VALUES %s
                ON CONFLICT (ticker) DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    city = EXCLUDED.city,
                    state = EXCLUDED.state,
                    country = EXCLUDED.country,
                    currency = EXCLUDED.currency,
                    exchange = EXCLUDED.exchange,
                    market = EXCLUDED.market,
                    website = EXCLUDED.website,
                    isin = EXCLUDED.isin,
                    cusip = EXCLUDED.cusip,
                    figi = EXCLUDED.figi,
                    composite_figi = EXCLUDED.composite_figi,
                    shareclass_figi = EXCLUDED.shareclass_figi,
                    industry = EXCLUDED.industry,
                    industry_group = EXCLUDED.industry_group,
                    sector = EXCLUDED.sector,
                    market_cap_category = EXCLUDED.market_cap_category,
                    zipcode = EXCLUDED.zipcode,
                    summary = EXCLUDED.summary,
                    last_updated = CURRENT_TIMESTAMP
                """,
                batch_data
            )
            print(f"   Successfully flattened {len(batch_data)} FinanceDatabase records.")

        except Exception as e:
            print(f"   ❌ Bulk insert failed: {e}")
    else:
        print("   ⚠️ No valid data to insert.")

    conn.commit()
    cur.close()
    conn.close()

def audit_fd_flattened():
    """Audit the flattened FinanceDatabase data."""
    print("[AUDIT] Checking stock_fundamentals_fd table...")

    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # Count records
    cur.execute("SELECT COUNT(*) FROM stock_fundamentals_fd")
    count = cur.fetchone()[0]
    print(f"   Total records: {count}")

    if count > 0:
        # Sample data
        cur.execute("""
            SELECT ticker, company_name, sector, industry, market_cap_category, country
            FROM stock_fundamentals_fd
            WHERE company_name IS NOT NULL
            LIMIT 5
        """)
        samples = cur.fetchall()

        print("   Sample records:")
        for row in samples:
            ticker, name, sector, industry, mcap, country = row
            print(f"      {ticker}: {name} ({sector}/{industry}) - {mcap} - {country}")

        # Market cap distribution
        cur.execute("""
            SELECT market_cap_category, COUNT(*) as count
            FROM stock_fundamentals_fd
            WHERE market_cap_category IS NOT NULL
            GROUP BY market_cap_category
            ORDER BY count DESC
        """)
        mcap_dist = cur.fetchall()

        print("   Market Cap Distribution:")
        for category, cnt in mcap_dist:
            print(f"      {category}: {cnt} companies")

    cur.close()
    conn.close()

if __name__ == "__main__":
    init_fd_fundamentals_table()
    flatten_fd_data()
    audit_fd_flattened()
    print("\nFinanceDatabase flattening complete!")