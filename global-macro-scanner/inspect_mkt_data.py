import psycopg2
import json
from config import DB_CONFIG

def inspect_mkt_data():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        cur.execute("SELECT ticker, mkt_data FROM raw_ibkr_nse WHERE ticker = 'RELIANCE.NSE';")
        row = cur.fetchone()
        
        if row and row[1]:
            print(f"\n--- Raw Market Data for {row[0]} ---")
            print(json.dumps(row[1], indent=2))
        else:
            print("No market data found.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_mkt_data()
