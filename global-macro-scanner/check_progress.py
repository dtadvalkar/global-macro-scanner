import psycopg2
from config import DB_CONFIG

def check_progress():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        tables = ['raw_fd_nse', 'raw_ibkr_nse', 'raw_yf_nse', 'prices_daily', 'raw_ibkr_price_snaps', 'current_market_data']
        for t in tables:
            cur.execute(f"SELECT count(*) FROM {t}")
            count = cur.fetchone()[0]
            print(f"Table {t}: {count} rows")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_progress()
