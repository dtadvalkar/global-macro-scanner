
import psycopg2
import os

def kill_locks():
    dbname = os.getenv("DB_NAME", "market_scanner")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")

    # Connect to default 'postgres' db to administrate
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        
        with conn.cursor() as cur:
            print(f"Terminating connections to {dbname}...")
            cur.execute(f"""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = '{dbname}' 
                AND pid <> pg_backend_pid();
            """)
            print("Connections terminated.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    kill_locks()
