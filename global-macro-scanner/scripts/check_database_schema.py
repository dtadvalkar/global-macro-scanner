#!/usr/bin/env python3
"""
Check PostgreSQL database schema and data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from config import DB_CONFIG

# Normalize DB config
db_config = DB_CONFIG.copy()
db_config['database'] = db_config.pop('db_name', 'global_scanner')

def check_database():
    print('POSTGRESQL DATABASE SCHEMA & DATA CHECK')
    print('=' * 60)

    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        # Get all tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        tables = cur.fetchall()
        print(f'Database tables: {[t[0] for t in tables]}')

        # Check stock_fundamentals table
        print('\nSTOCK_FUNDAMENTALS TABLE:')
        print('-' * 40)

        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'stock_fundamentals'
            ORDER BY ordinal_position
        """)

        columns = cur.fetchall()
        if columns:
            print('Columns:')
            for col in columns:
                print(f'  {col[0]} ({col[1]}) - Nullable: {col[2]}')

            # Sample data
            cur.execute('SELECT COUNT(*) FROM stock_fundamentals')
            count = cur.fetchone()[0]
            print(f'\nTotal records: {count}')

            if count > 0:
                cur.execute('SELECT ticker, market_cap_usd, sector, industry, last_updated FROM stock_fundamentals LIMIT 5')
                samples = cur.fetchall()
                print('\nSample records:')
                for sample in samples:
                    market_cap = sample[1]
                    if market_cap:
                        mc_str = f'${market_cap/1000000:.1f}M'
                    else:
                        mc_str = 'N/A'
                    print(f'  {sample[0]}: {mc_str} ({sample[2]}/{sample[3]}) - {sample[4]}')
        else:
            print('Table does not exist or is empty')

        # Check tickers table
        print('\nTICKERS TABLE:')
        print('-' * 40)

        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'tickers'
            ORDER BY ordinal_position
        """)

        columns = cur.fetchall()
        if columns:
            print('Columns:')
            for col in columns:
                print(f'  {col[0]} ({col[1]}) - Nullable: {col[2]}')

            # Sample data
            cur.execute('SELECT COUNT(*) FROM tickers')
            count = cur.fetchone()[0]
            print(f'\nTotal records: {count}')

            if count > 0:
                cur.execute('SELECT ticker, exchange, is_active FROM tickers LIMIT 5')
                samples = cur.fetchall()
                print('\nSample records:')
                for sample in samples:
                    status = 'ACTIVE' if sample[2] else 'INACTIVE'
                    print(f'  {sample[0]} ({sample[1]}) - {status}')

        # Check for ignored stocks analysis
        print('\nSTOCKS TO IGNORE ANALYSIS:')
        print('-' * 40)

        # Stocks below market cap threshold
        min_market_cap = 150000000  # $150M for emerging markets
        cur.execute("""
            SELECT COUNT(*), MIN(market_cap_usd), MAX(market_cap_usd), AVG(market_cap_usd)
            FROM stock_fundamentals
            WHERE market_cap_usd < %s AND market_cap_usd > 0
        """, (min_market_cap,))

        result = cur.fetchone()
        if result and result[0] > 0:
            print(f'Stocks below ${min_market_cap/1000000:.0f}M threshold: {result[0]}')
            print(f'  Market cap range: ${result[1]/1000000:.1f}M - ${result[2]/1000000:.1f}M')
            print(f'  Average: ${result[3]/1000000:.1f}M')

            # Show some examples
            cur.execute("""
                SELECT ticker, market_cap_usd, sector
                FROM stock_fundamentals
                WHERE market_cap_usd < %s AND market_cap_usd > 0
                ORDER BY market_cap_usd ASC
                LIMIT 5
            """, (min_market_cap,))

            examples = cur.fetchall()
            print('  Examples of small cap stocks to ignore:')
            for ex in examples:
                print(f'    {ex[0]}: ${ex[1]/1000000:.1f}M ({ex[2]})')

        # Inactive stocks
        cur.execute('SELECT COUNT(*) FROM tickers WHERE is_active = FALSE')
        inactive_count = cur.fetchone()[0]
        if inactive_count > 0:
            print(f'\nManually marked inactive stocks: {inactive_count}')

        cur.close()
        conn.close()

    except Exception as e:
        print(f'Database connection error: {e}')
        print('Make sure PostgreSQL is running and credentials are correct')

if __name__ == '__main__':
    check_database()