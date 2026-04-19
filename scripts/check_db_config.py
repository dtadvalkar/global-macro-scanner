#!/usr/bin/env python3
"""
Check database configuration and connectivity
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_CONFIG

def check_db_config():
    print('DATABASE CONFIGURATION CHECK')
    print('=' * 50)

    print('Environment variables:')
    print(f'  DB_NAME: {os.getenv("DB_NAME", "NOT SET")}')
    print(f'  DB_USER: {os.getenv("DB_USER", "NOT SET")}')
    print(f'  DB_PASSWORD: {os.getenv("DB_PASSWORD", "NOT SET")}')
    print(f'  DB_HOST: {os.getenv("DB_HOST", "NOT SET")}')
    print(f'  DB_PORT: {os.getenv("DB_PORT", "NOT SET")}')

    print('\nDB_CONFIG from settings.py:')
    for key, value in DB_CONFIG.items():
        print(f'  {key}: {value}')

    print('\nNormalized config (for psycopg2):')
    normalized = DB_CONFIG.copy()
    # Map config keys to psycopg2 expected keys
    key_mapping = {
        'db_name': 'database',
        'db_user': 'user',
        'db_pass': 'password',
        'db_host': 'host',
        'db_port': 'port'
    }

    for old_key, new_key in key_mapping.items():
        if old_key in normalized:
            normalized[new_key] = normalized.pop(old_key)

    for key, value in normalized.items():
        print(f'  {key}: {value}')

    target_db = normalized.get('database', 'global_scanner')
    print(f'\nTarget database: {target_db}')

    print('\nTO CONNECT VIA PGADMIN OR PSQL:')
    print(f'  Database: {target_db}')
    print(f'  Host: {normalized.get("db_host", "localhost")}')
    print(f'  Port: {normalized.get("db_port", "5432")}')
    print(f'  User: {normalized.get("db_user", "postgres")}')

    return normalized

def test_connection(config):
    print('\nTESTING DATABASE CONNECTION...')
    print('-' * 40)

    try:
        import psycopg2
        conn = psycopg2.connect(**config)
        cur = conn.cursor()

        # Get database name
        cur.execute('SELECT current_database()')
        db_name = cur.fetchone()[0]
        print(f'Connected to database: {db_name}')

        # List tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        tables = cur.fetchall()
        if tables:
            print(f'Tables found: {[t[0] for t in tables]}')

            # Check for our tables
            our_tables = ['tickers', 'stock_fundamentals']
            existing_tables = [t[0] for t in tables]

            for table in our_tables:
                if table in existing_tables:
                    cur.execute(f'SELECT COUNT(*) FROM {table}')
                    count = cur.fetchone()[0]
                    print(f'  {table}: {count} records')
                else:
                    print(f'  {table}: Table does not exist')
        else:
            print('No tables found in database')

        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f'Connection failed: {e}')
        print('\nTROUBLESHOOTING:')
        print('1. Make sure PostgreSQL is running')
        print('2. Check if pgAdmin is connected (might lock the database)')
        print('3. Verify credentials in config/settings.py')
        print('4. Try connecting manually: psql -d market_scanner -U postgres')
        return False

if __name__ == '__main__':
    config = check_db_config()
    test_connection(config)