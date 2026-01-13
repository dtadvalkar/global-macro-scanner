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
                    status TEXT DEFAULT 'ACTIVE',
                    status_message TEXT,
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

        conn.commit()

    def get_actionable_tickers(self, market):
        """
        Returns tickers that are either:
        1. ACTIVE
        2. INACTIVE but older than 200 days (Parole/Retry Period)
        """
        conn = self._get_connection()
        # 200 days parole as requested by user
        parole_date = datetime.now() - timedelta(days=200) 
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol FROM tickers 
                WHERE market = %s 
                AND (
                    status = 'ACTIVE' 
                    OR status IS NULL 
                    OR last_updated < %s
                )
            """, (market, parole_date))
            rows = cur.fetchall()
        return [row[0] for row in rows]

    def update_ticker_status(self, symbol, status, message=None):
        """Updates the status of a ticker (e.g., 'INACTIVE', 'ACTIVE')"""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tickers 
                SET status = %s, status_message = %s, last_updated = %s
                WHERE symbol = %s
            """, (status, message, datetime.now(), symbol))
        conn.commit()

    def is_market_fresh(self, market, ttl_days=7, min_count=100):
        """Checks if we have recently updated the universe for this market."""
        conn = self._get_connection()
        cutoff = datetime.now() - timedelta(days=ttl_days)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM tickers WHERE market = %s AND last_updated > %s",
                (market, cutoff)
            )
            count = cur.fetchone()[0]
        return count >= min_count

    def truncate_tables(self):
        """Wipes all data from tickers and stock_fundamentals while preserving schema."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            print("Truncating 'tickers' and 'stock_fundamentals'...")
            cur.execute("TRUNCATE TABLE tickers, stock_fundamentals RESTART IDENTITY CASCADE")
        conn.commit()
        print("✅ Database tables truncated.")

    def save_tickers(self, market, tickers):
        """Saves or updates tickers in the database (Source of Truth sync)."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            # We insert with status='ACTIVE' (default) if new.
            # If exists, we ONLY update last_updated and market.
            # We do NOT reset status to ACTIVE because it might be deliberately INACTIVE.
            data = [(s, market, datetime.now()) for s in tickers]
            extras.execute_values(
                cur,
                "INSERT INTO tickers (symbol, market, last_updated) VALUES %s "
                "ON CONFLICT (symbol) DO UPDATE SET last_updated = EXCLUDED.last_updated, market = EXCLUDED.market",
                data
            )
        conn.commit()
