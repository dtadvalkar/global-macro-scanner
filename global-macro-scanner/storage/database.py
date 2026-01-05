import psycopg2
from psycopg2 import extras
import os
from datetime import datetime, timedelta

class DatabaseManager:
    def __init__(self):
        self.dbname = os.getenv("DB_NAME", "market_scanner")
        self.user = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "postgres")
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = os.getenv("DB_PORT", "5432")
        self.conn = None
        self._initialize_db()

    def _get_connection(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
        return self.conn

    def _initialize_db(self):
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tickers (
                    symbol TEXT PRIMARY KEY,
                    market TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 🚀 Future Expansion: Table for storing triggered alerts/catches
            cur.execute("""
                CREATE TABLE IF NOT EXISTS catches (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT,
                    price DECIMAL,
                    usd_mcap DECIMAL,
                    pct_from_low DECIMAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()

    def get_cached_tickers(self, market, ttl_days=7):
        """Returns tickers for a market if they are fresh."""
        conn = self._get_connection()
        cutoff = datetime.now() - timedelta(days=ttl_days)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol FROM tickers WHERE market = %s AND last_updated > %s",
                (market, cutoff)
            )
            rows = cur.fetchall()
        return [row[0] for row in rows]

    def save_tickers(self, market, tickers):
        """Saves or updates tickers in the database."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            # Clear old for this market to keep it fresh (or upsert)
            # For simplicity, let's just upsert
            data = [(s, market, datetime.now()) for s in tickers]
            extras.execute_values(
                cur,
                "INSERT INTO tickers (symbol, market, last_updated) VALUES %s "
                "ON CONFLICT (symbol) DO UPDATE SET last_updated = EXCLUDED.last_updated, market = EXCLUDED.market",
                data
            )
        conn.commit()
