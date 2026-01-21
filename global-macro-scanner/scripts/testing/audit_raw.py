import psycopg2
from config import DB_CONFIG

def audit_raw_data():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        print("\n--- Auditing raw_ibkr_nse ---")
        cur.execute("SELECT ticker, length(xml_snapshot), length(xml_ratios), (mkt_data IS NOT NULL) as has_mkt, (contract_details IS NOT NULL) as has_cd FROM raw_ibkr_nse;")
        rows = cur.fetchall()
        
        for row in rows:
            print(f"Ticker: {row[0]}")
            print(f"  XML Snapshot Length: {row[1] if row[1] is not None else 'NULL'}")
            print(f"  XML Ratios Length:   {row[2] if row[2] is not None else 'NULL'}")
            print(f"  Has Mkt Data:        {row[3]}")
            print(f"  Has Contract Details: {row[4]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    audit_raw_data()
