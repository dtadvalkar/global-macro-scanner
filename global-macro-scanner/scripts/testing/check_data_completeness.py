#!/usr/bin/env python3
"""
Check data completeness in raw_ibkr_nse table
"""

import os
import psycopg2

db_name = os.getenv("DB_NAME", "market_scanner")
db_user = os.getenv("DB_USER", "postgres")
db_pass = os.getenv("DB_PASSWORD", "")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")

conn = psycopg2.connect(
    dbname=db_name,
    user=db_user,
    password=db_pass,
    host=db_host,
    port=db_port,
)
cur = conn.cursor()

# Check current table structure and data completeness
cur.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN xml_snapshot IS NOT NULL THEN 1 ELSE 0 END) as has_fundamentals,
        SUM(CASE WHEN mkt_data IS NOT NULL THEN 1 ELSE 0 END) as has_market_data,
        SUM(CASE WHEN xml_snapshot IS NOT NULL AND mkt_data IS NOT NULL THEN 1 ELSE 0 END) as has_both,
        SUM(CASE WHEN xml_snapshot IS NULL AND mkt_data IS NULL THEN 1 ELSE 0 END) as has_neither
    FROM raw_ibkr_nse
""")

stats = cur.fetchone()
print('RAW_IBKR_NSE DATA COMPLETENESS:')
print('=' * 50)
print(f'Total records: {stats[0]}')
print(f'Has fundamentals only: {stats[1] - stats[3]}')
print(f'Has market data only: {stats[2] - stats[3]}')
print(f'Has both: {stats[3]}')
print(f'Has neither: {stats[4]}')

# Show table structure
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'raw_ibkr_nse'
    ORDER BY ordinal_position
""")

columns = cur.fetchall()
print(f'\nTABLE STRUCTURE:')
print('=' * 30)
for col, dtype, nullable in columns:
    null_status = 'NULL' if nullable == 'YES' else 'NOT NULL'
    print(f'{col:<20} {dtype:<15} {null_status}')

cur.close()
conn.close()