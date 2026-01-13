import os
from dotenv import load_dotenv
from ib_async import IB
import psycopg2
import requests

load_dotenv()

def test_db():
    print("Testing PostgreSQL...")
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        print("✅ DB Connected.")
        conn.close()
    except Exception as e:
        print(f"❌ DB Failed: {e}")

def test_telegram():
    print("Testing Telegram...")
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            print("✅ Telegram OK.")
        else:
            print(f"❌ Telegram Error: {r.text}")
    except Exception as e:
        print(f"❌ Telegram Failed: {e}")

def test_ibkr():
    print("Testing IBKR Live (7496)...")
    ib = IB()
    try:
        ib.connect('127.0.0.1', 7496, clientId=99)
        print("✅ IBKR Connected.")
        ib.disconnect()
    except Exception as e:
        print(f"❌ IBKR Failed: {e}")

if __name__ == "__main__":
    test_db()
    test_telegram()
    test_ibkr()
