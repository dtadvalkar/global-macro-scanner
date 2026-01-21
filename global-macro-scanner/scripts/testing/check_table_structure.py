from config import DB_CONFIG
import psycopg2

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Check raw_ibkr_price_snaps structure
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'raw_ibkr_price_snaps' ORDER BY ordinal_position")
columns = cur.fetchall()
print('raw_ibkr_price_snaps table structure:')
for col in columns:
    print(f'  {col[0]}: {col[1]}')

# Check if there's any data
cur.execute("SELECT COUNT(*) FROM raw_ibkr_price_snaps")
count = cur.fetchone()[0]
print(f'\nRows in raw_ibkr_price_snaps: {count}')

cur.close()
conn.close()