import psycopg2
from config import DB_CONFIG

def audit_mega():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        # Count columns
        cur.execute("""
            SELECT count(*) 
            FROM information_schema.columns 
            WHERE table_name = 'stock_fundamentals'
        """)
        col_count = cur.fetchone()[0]
        
        # Count rows
        cur.execute("SELECT count(*) FROM stock_fundamentals")
        row_count = cur.fetchone()[0]
        
        print(f"--- 🏛️ MEGA-SCHEMA AUDIT ---")
        print(f"Table Name : stock_fundamentals")
        print(f"Total Columns: {col_count}")
        print(f"Total Rows   : {row_count}")
        print("-" * 30)
        
        # Sample Data
        cur.execute("""
            SELECT 
                ticker, 
                company_name, 
                exchange_code, 
                isin,
                mkt_cap_usd, 
                industry_trbc,
                officer_1_name,
                left(business_summary, 50) as bio
            FROM stock_fundamentals
        """)
        rows = cur.fetchall()
        for r in rows:
            ticker, name, exch, isin, mc, ind, off, bio = r
            print(f"\nTicker    : {ticker}")
            print(f"Name      : {name}")
            print(f"Exchange  : {exch}")
            print(f"ISIN      : {isin}")
            print(f"Industry  : {ind}")
            print(f"Chairman  : {off}")
            print(f"Bio Snippet: {bio}...")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    audit_mega()
