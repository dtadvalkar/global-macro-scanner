#!/usr/bin/env python3
"""
Check tickers table content and show stocks to ignore
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_CONFIG
import psycopg2

def check_tickers_data():
    print('CHECKING TICKERS TABLE CONTENT')
    print('=' * 50)

    # Normalize config
    config = DB_CONFIG.copy()
    # Map to psycopg2 expected keys
    if 'db_name' in config:
        config['database'] = config.pop('db_name')
    if 'db_user' in config:
        config['user'] = config.pop('db_user')
    if 'db_pass' in config:
        config['password'] = config.pop('db_pass')
    if 'db_host' in config:
        config['host'] = config.pop('db_host')
    if 'db_port' in config:
        config['port'] = config.pop('db_port')

    try:
        conn = psycopg2.connect(**config)
        cur = conn.cursor()

        # Total count
        cur.execute('SELECT COUNT(*) FROM tickers')
        total = cur.fetchone()[0]
        print(f'Total tickers in database: {total}')

        # Check table structure first
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tickers'
            ORDER BY ordinal_position
        """)

        table_columns = [row[0] for row in cur.fetchall()]
        print(f'Tickers table columns: {table_columns}')

        has_market = 'market' in table_columns

        if has_market:
            # By market
            cur.execute("""
                SELECT market, COUNT(*) as count
                FROM tickers
                GROUP BY market
                ORDER BY count DESC
            """)

            markets = cur.fetchall()
            print('\nTickers by market:')
            for market, count in markets:
                print(f'  {market}: {count} tickers')
        else:
            print('\nNo market column found in tickers table')

        print('\nNOTE: This tickers table does not have is_active column.')
        print('Stocks to ignore are tracked separately in failed stocks cache.')
        print('The stock_fundamentals table (when created) will have market cap data for filtering.')

        # Sample stocks
        print('\nSample tickers from database:')
        cur.execute('SELECT symbol, market FROM tickers LIMIT 10')
        samples = cur.fetchall()
        for symbol, market in samples:
            print(f'  {symbol} ({market})')

        # Check for stock_fundamentals table
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'stock_fundamentals'
            )
        """)
        fundamentals_exists = cur.fetchone()[0]

        if fundamentals_exists:
            cur.execute('SELECT COUNT(*) FROM stock_fundamentals')
            fundamentals_count = cur.fetchone()[0]
            print(f'\nStock fundamentals table: EXISTS ({fundamentals_count} records)')

            if fundamentals_count > 0:
                cur.execute('SELECT ticker, market_cap_usd, sector FROM stock_fundamentals LIMIT 3')
                fundamentals_samples = cur.fetchall()
                print('Sample fundamentals data:')
                for ticker, cap, sector in fundamentals_samples:
                    cap_m = cap/1000000 if cap else 0
                    print(f'  {ticker}: ${cap_m:.1f}M ({sector})')
        else:
            print('\nStock fundamentals table: DOES NOT EXIST')
            print('The table will be created automatically when fundamentals are cached.')

        cur.close()
        conn.close()

    except Exception as e:
        print(f'Database error: {e}')

if __name__ == '__main__':
    check_tickers_data()