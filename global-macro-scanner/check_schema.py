import psycopg2
from config import DB_CONFIG

def check_tables():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        # Check for tickers table
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'tickers' ORDER BY ordinal_position;")
        columns = cur.fetchall()
        print("\nTable: tickers")
        for col in columns:
            print(f"  {col[0]}: {col[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_tables()
