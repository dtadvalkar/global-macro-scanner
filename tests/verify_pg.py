import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def verify():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        with conn.cursor() as cur:
            cur.execute("SELECT market, COUNT(*) FROM tickers GROUP BY market")
            rows = cur.fetchall()
            print("--- POSTGRES TICKER STATS ---")
            for row in rows:
                print(f"Market: {row[0]} | Count: {row[1]}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify()
