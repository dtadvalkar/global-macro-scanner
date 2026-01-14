import psycopg2
from config import DB_CONFIG

def check_yf():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        cur.execute("SELECT ticker, (raw_info IS NOT NULL), (raw_fast_info IS NOT NULL) FROM raw_yf_nse;")
        rows = cur.fetchall()
        for row in rows:
            print(f"Ticker: {row[0]}, Info: {row[1]}, FastInfo: {row[2]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_yf()
