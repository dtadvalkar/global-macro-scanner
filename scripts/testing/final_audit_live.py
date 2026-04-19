import psycopg2
from config import DB_CONFIG

def final_audit():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        # 1. Check counts
        cur.execute("SELECT count(*) FROM raw_ibkr_nse WHERE xml_snapshot IS NOT NULL;")
        xml_count = cur.fetchone()[0]
        
        # 2. Get a snippet of the XML
        cur.execute("SELECT ticker, length(xml_snapshot), left(xml_snapshot, 300) FROM raw_ibkr_nse LIMIT 1;")
        row = cur.fetchone()
        
        print("\n" + "="*50)
        print("🚀 LIVE ACCOUNT AUDIT SUCCESS")
        print("="*50)
        print(f"Tickers with Full XML: {xml_count}")
        if row:
            print(f"\nTicker: {row[0]}")
            print(f"XML Length: {row[1]} bytes")
            print(f"XML Snippet:\n{row[2]}...")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    final_audit()
