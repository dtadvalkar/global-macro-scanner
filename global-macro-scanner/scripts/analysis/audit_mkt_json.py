import psycopg2
import json
from config import DB_CONFIG

def audit_mkt_json():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        # Use JSONB pathing to extract nested values
        query = """
        SELECT 
            ticker,
            mkt_data->'Ticker'->>'last' as last,
            mkt_data->'Ticker'->>'close' as close,
            mkt_data->'Ticker'->>'open' as open,
            mkt_data->'Ticker'->>'high' as high,
            mkt_data->'Ticker'->>'low' as low,
            mkt_data->'Ticker'->>'volume' as volume
        FROM raw_ibkr_nse;
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        print(f"{'Ticker':<15} | {'Last':<8} | {'Close':<8} | {'Open':<8} | {'High':<8} | {'Low':<8} | {'Volume':<8}")
        print("-" * 80)
        for row in rows:
            print(f"{row[0]:<15} | {str(row[1]):<8} | {str(row[2]):<8} | {str(row[3]):<8} | {str(row[4]):<8} | {str(row[5]):<8} | {str(row[6]):<8}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    audit_mkt_json()
