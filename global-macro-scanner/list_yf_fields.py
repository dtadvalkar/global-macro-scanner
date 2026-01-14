import psycopg2
import json
from config import DB_CONFIG

def list_yf_fields():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        cur.execute("SELECT ticker, raw_info FROM raw_yf_nse WHERE ticker = 'RELIANCE.NSE';")
        row = cur.fetchone()
        if row and row[1]:
            info = row[1] # raw_info is JSONB, psycopg2 converts to dict
            print(f"\n--- YFinance Fields for {row[0]} ---")
            fields = sorted(list(info.keys()))
            for f in fields:
                print(f"  {f}")
            print(f"\nTotal Fields: {len(fields)}")
        else:
            print("No data found in raw_yf_nse for RELIANCE.NSE")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_yf_fields()
