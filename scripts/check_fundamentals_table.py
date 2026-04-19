#!/usr/bin/env python3
"""
Check what was stored in stock_fundamentals table after NSE demo
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_CONFIG
import psycopg2

def check_fundamentals_table():
    print('CHECKING STOCK_FUNDAMENTALS TABLE AFTER NSE DEMO')
    print('=' * 60)

    # Normalize config
    config = DB_CONFIG.copy()
    key_mapping = {
        'db_name': 'database',
        'db_user': 'user',
        'db_pass': 'password',
        'db_host': 'host',
        'db_port': 'port'
    }

    for old_key, new_key in key_mapping.items():
        if old_key in config:
            config[new_key] = config.pop(old_key)

    try:
        conn = psycopg2.connect(**config)
        cur = conn.cursor()

        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'stock_fundamentals'
            )
        """)

        table_exists = cur.fetchone()[0]

        if table_exists:
            # Get record count
            cur.execute('SELECT COUNT(*) FROM stock_fundamentals')
            count = cur.fetchone()[0]
            print(f'stock_fundamentals table exists with {count} records')

            if count > 0:
                # Show all records (should be just RELIANCE.NS)
                cur.execute("""
                    SELECT ticker, symbol, exchange, market_cap_usd, sector,
                           industry, currency, last_updated, data_source
                    FROM stock_fundamentals
                """)

                rows = cur.fetchall()
                print('\nRECORDS STORED:')
                print('=' * 30)

                for row in rows:
                    ticker, symbol, exchange, mcap, sector, industry, currency, updated, source = row

                    # Format market cap
                    if mcap:
                        if mcap >= 1000000000:  # Billions
                            mcap_str = f'${mcap/1000000000:.1f}B'
                        else:  # Millions
                            mcap_str = f'${mcap/1000000:.1f}M'
                    else:
                        mcap_str = 'N/A'

                    print(f'Ticker: {ticker}')
                    print(f'  Symbol: {symbol}')
                    print(f'  Exchange: {exchange}')
                    print(f'  Market Cap: {mcap_str}')
                    print(f'  Sector: {sector}')
                    print(f'  Industry: {industry}')
                    print(f'  Currency: {currency}')
                    print(f'  Data Source: {source}')
                    print(f'  Last Updated: {updated}')
                    print()

                print('SUCCESS! The stock_fundamentals table now contains:')
                print('- Market cap data for filtering small stocks')
                print('- Sector/industry for future analysis')
                print('- Source tracking (IBKR vs YFinance)')
                print('- Timestamps for data freshness')

            # Show table structure
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'stock_fundamentals'
                ORDER BY ordinal_position
            """)

            columns = cur.fetchall()
            print('\nTABLE COLUMNS:')
            print('=' * 20)
            for col_name, col_type in columns:
                print(f'  {col_name}: {col_type}')

        else:
            print('stock_fundamentals table does not exist')
            print('Run the demo script to populate it')

        cur.close()
        conn.close()

    except Exception as e:
        print(f'Database error: {e}')

if __name__ == '__main__':
    check_fundamentals_table()