#!/usr/bin/env python3
"""
Global Macro Scanner - Centralized Database Interface

This module provides a unified interface for all PostgreSQL database operations.
Centralizes all database interactions to avoid scattered queries throughout the codebase.

ARCHITECTURE:
- Connection management with proper error handling
- Query execution with logging and metrics
- Data validation and type conversion
- Schema management and migrations
- Health checks and diagnostics

USAGE:
    from db import Database
    db = Database()
    result = db.query("SELECT * FROM stock_fundamentals LIMIT 5")
"""

import psycopg2
import psycopg2.extras
import psycopg2.pool
import sys
import io
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from contextlib import contextmanager
import json


# Import config
from dotenv import load_dotenv
load_dotenv()

try:
    from config import DB_CONFIG
except ImportError:
    # Fallback for when config.py is not available
    DB_CONFIG = {
        'db_name': os.getenv('DB_NAME', 'global_macro'),
        'db_user': os.getenv('DB_USER', 'postgres'),
        'db_pass': os.getenv('DB_PASSWORD', ''),
        'db_host': os.getenv('DB_HOST', 'localhost'),
        'db_port': os.getenv('DB_PORT', '5432')
    }

class Database:
    """
    Centralized database interface for Global Macro Scanner.

    Provides connection pooling, query execution, schema management,
    and data validation for all database operations.
    """

    def __init__(self, config: Optional[Dict] = None, pool_size: int = 5):
        """
        Initialize database connection pool.

        Args:
            config: Database configuration (uses DB_CONFIG if None)
            pool_size: Connection pool size
        """
        self.config = config or DB_CONFIG
        self.pool_size = pool_size
        self.pool = None
        self.logger = logging.getLogger(__name__)

        # Setup logging
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        self._create_pool()

    def _create_pool(self):
        """Create connection pool with retry logic."""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self.pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=self.pool_size,
                    dbname=self.config['db_name'],
                    user=self.config['db_user'],
                    password=self.config['db_pass'],
                    host=self.config['db_host'],
                    port=self.config['db_port']
                )

                # Test connection
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        result = cur.fetchone()

                self.logger.info(f"✅ Database connection pool created (size: {self.pool_size})")
                return

            except psycopg2.Error as e:
                self.logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to connect to database after {max_retries} attempts: {e}")

    @contextmanager
    def get_connection(self):
        """
        Get database connection from pool with automatic cleanup.

        Usage:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM table")
        """
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
        except Exception as e:
            self.logger.error(f"Database operation failed: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.pool.putconn(conn)

    def query(self, sql: str, params: Tuple = None, fetch: str = 'all') -> Union[List, Dict, None]:
        """
        Execute SELECT query and return results.

        Args:
            sql: SQL query string
            params: Query parameters tuple
            fetch: 'all' (list of tuples), 'one' (single tuple), 'dict' (list of dicts)

        Returns:
            Query results based on fetch parameter
        """
        start_time = time.time()

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor if fetch == 'dict' else None) as cur:
                try:
                    cur.execute(sql, params or ())

                    if fetch == 'one':
                        result = cur.fetchone()
                    elif fetch == 'dict':
                        rows = cur.fetchall()
                        result = [dict(row) for row in rows]
                    else:  # 'all'
                        result = cur.fetchall()

                    execution_time = time.time() - start_time
                    self.logger.debug(".3f")

                    return result

                except psycopg2.Error as e:
                    self.logger.error(f"Query execution failed: {e}")
                    self.logger.error(f"SQL: {sql}")
                    self.logger.error(f"Params: {params}")
                    raise

    def execute(self, sql: str, params: Tuple = None) -> int:
        """
        Execute INSERT, UPDATE, DELETE, or DDL statements.

        Args:
            sql: SQL statement
            params: Parameters tuple

        Returns:
            Number of affected rows
        """
        start_time = time.time()

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(sql, params or ())
                    affected_rows = cur.rowcount
                    conn.commit()

                    execution_time = time.time() - start_time
                    self.logger.debug(".3f")

                    return affected_rows

                except psycopg2.Error as e:
                    conn.rollback()
                    self.logger.error(f"Execute failed: {e}")
                    self.logger.error(f"SQL: {sql}")
                    self.logger.error(f"Params: {params}")
                    raise

    def bulk_insert(self, table: str, data: List[Dict], batch_size: int = 1000) -> int:
        """
        Bulk insert data into table.

        Args:
            table: Table name
            data: List of dictionaries with column data
            batch_size: Batch size for insertion

        Returns:
            Total rows inserted
        """
        if not data:
            return 0

        columns = list(data[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

        total_inserted = 0
        start_time = time.time()

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    for i in range(0, len(data), batch_size):
                        batch = data[i:i + batch_size]
                        values = [tuple(row[col] for col in columns) for row in batch]

                        cur.executemany(sql, values)
                        total_inserted += len(batch)

                    conn.commit()

                    execution_time = time.time() - start_time
                    self.logger.info(f"✅ Bulk inserted {total_inserted} rows into {table} in {execution_time:.2f}s")

                    return total_inserted

                except psycopg2.Error as e:
                    conn.rollback()
                    self.logger.error(f"Bulk insert failed: {e}")
                    raise

    # ============================================================================
    # SCHEMA MANAGEMENT
    # ============================================================================

    def create_tables(self):
        """Create all required database tables."""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS tickers (
                ticker TEXT PRIMARY KEY,
                market TEXT,
                status TEXT DEFAULT 'ACTIVE',
                status_message TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS stock_fundamentals (
                ticker TEXT PRIMARY KEY,
                company_name TEXT,
                rep_no TEXT,
                org_perm_id TEXT,
                isin TEXT,
                ric TEXT,
                exchange_code TEXT,
                exchange_country TEXT,
                most_recent_split_date DATE,
                most_recent_split_factor NUMERIC,
                mkt_cap_usd NUMERIC,
                currency TEXT,
                price_currency TEXT,
                last_fundamental_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS prices_daily (
                ticker TEXT,
                trade_date DATE,
                open NUMERIC,
                high NUMERIC,
                low NUMERIC,
                close NUMERIC,
                adj_close NUMERIC,
                volume BIGINT,
                source TEXT NOT NULL,
                PRIMARY KEY (ticker, trade_date, source)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS current_market_data (
                ticker TEXT PRIMARY KEY,
                last_price NUMERIC,
                close_price NUMERIC,
                open_price NUMERIC,
                high_price NUMERIC,
                low_price NUMERIC,
                volume BIGINT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS raw_fd_nse (
                ticker TEXT PRIMARY KEY,
                data JSONB,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS raw_ibkr_nse (
                ticker TEXT PRIMARY KEY,
                xml_snapshot TEXT,
                xml_ratios TEXT,
                mkt_data JSONB,
                contract_details JSONB,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS raw_yf_nse (
                ticker TEXT PRIMARY KEY,
                info JSONB,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]

        for sql in tables:
            self.execute(sql)

        self.logger.info("✅ All database tables created/verified")

    def drop_tables(self, tables: List[str] = None):
        """Drop specified tables or all tables if none specified."""
        if tables is None:
            tables = [
                'raw_yf_nse', 'raw_ibkr_nse', 'raw_fd_nse',
                'current_market_data', 'prices_daily', 'stock_fundamentals', 'tickers'
            ]

        for table in tables:
            try:
                self.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                self.logger.info(f"✅ Dropped table: {table}")
            except Exception as e:
                self.logger.warning(f"Failed to drop {table}: {e}")

    def get_table_info(self, table: str) -> Dict:
        """Get detailed information about a table."""
        info = {}

        # Row count
        result = self.query(f"SELECT COUNT(*) as count FROM {table}", fetch='one')
        info['row_count'] = result[0] if result else 0

        # Column info
        columns = self.query(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = '{table}' AND table_schema = 'public'
            ORDER BY ordinal_position
        """)

        info['columns'] = columns or []

        # Indexes
        indexes = self.query(f"""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = '{table}' AND schemaname = 'public'
        """)

        info['indexes'] = indexes or []

        return info

    def is_market_fresh(self, market: str, ttl_days: int = 7, min_count: int = 100) -> bool:
        """Checks if we have recently updated the universe for this market."""
        cutoff = datetime.now() - timedelta(days=ttl_days)
        result = self.query(
            "SELECT count(*) FROM tickers WHERE market = %s AND last_updated > %s",
            (market, cutoff),
            fetch='one'
        )
        return result[0] >= min_count if result else False

    def get_actionable_tickers(self, market: str) -> List[str]:
        """Returns tickers that are either ACTIVE or in parole."""
        parole_date = datetime.now() - timedelta(days=200) 
        rows = self.query("""
            SELECT ticker FROM tickers 
            WHERE market = %s 
            AND (status = 'ACTIVE' OR status IS NULL OR last_updated < %s)
            ORDER BY ticker
        """, (market, parole_date))
        return [row[0] for row in rows] if rows else []

    def save_tickers(self, market: str, tickers: List[str]):
        """Saves or updates tickers in the database (Source of Truth sync)."""
        now = datetime.now()
        data = [(s, market, now) for s in tickers]
        # Use execute_values for efficient batch insertion
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                from psycopg2.extras import execute_values
                execute_values(
                    cur,
                    "INSERT INTO tickers (ticker, market, last_updated) VALUES %s "
                    "ON CONFLICT (ticker) DO UPDATE SET last_updated = EXCLUDED.last_updated, market = EXCLUDED.market",
                    data
                )

    def update_ticker_status(self, ticker, status, message=None):
        """Updates the status of a ticker (e.g., 'INACTIVE', 'ACTIVE')"""
        self.execute("""
            UPDATE tickers 
            SET status = %s, status_message = %s, last_updated = %s
            WHERE ticker = %s
        """, (status, message, datetime.now(), ticker))

    # ============================================================================
    # DATA VALIDATION & HEALTH CHECKS
    # ============================================================================

    def health_check(self) -> Dict:
        """Perform comprehensive database health check."""
        health = {
            'timestamp': datetime.now().isoformat(),
            'connection': 'ok',
            'tables': {},
            'issues': []
        }

        try:
            # Check all tables
            tables = [
                'tickers', 'stock_fundamentals', 'prices_daily',
                'current_market_data', 'raw_fd_nse', 'raw_ibkr_nse', 'raw_yf_nse'
            ]

            for table in tables:
                try:
                    info = self.get_table_info(table)
                    health['tables'][table] = {
                        'exists': True,
                        'row_count': info['row_count'],
                        'columns': len(info['columns'])
                    }
                except Exception as e:
                    health['tables'][table] = {'exists': False, 'error': str(e)}
                    health['issues'].append(f"Table {table}: {e}")

        except Exception as e:
            health['connection'] = 'error'
            health['issues'].append(f"Connection error: {e}")

        return health

    def validate_data_integrity(self) -> Dict:
        """Validate data integrity across tables."""
        issues = []

        # Check for orphaned records
        try:
            result = self.query("""
                SELECT COUNT(*) FROM prices_daily p
                LEFT JOIN stock_fundamentals sf ON p.ticker = sf.ticker
                WHERE sf.ticker IS NULL
            """, fetch='one')
            orphaned_prices = result[0] if result else 0
            if orphaned_prices > 0:
                issues.append(f"Found {orphaned_prices} price records without fundamentals")
        except Exception as e:
            issues.append(f"Price integrity check failed: {e}")

        try:
            result = self.query("""
                SELECT COUNT(*) FROM current_market_data c
                LEFT JOIN stock_fundamentals sf ON c.ticker = sf.ticker
                WHERE sf.ticker IS NULL
            """, fetch='one')
            orphaned_current = result[0] if result else 0
            if orphaned_current > 0:
                issues.append(f"Found {orphaned_current} current market records without fundamentals")
        except Exception as e:
            issues.append(f"Current market integrity check failed: {e}")

        return {
            'timestamp': datetime.now().isoformat(),
            'issues': issues,
            'status': 'healthy' if not issues else 'issues_found'
        }

    # ============================================================================
    # CONVENIENCE METHODS FOR COMMON QUERIES
    # ============================================================================

    def get_fundamentals_count(self) -> int:
        """Get count of tickers in fundamentals table."""
        result = self.query("SELECT COUNT(*) FROM stock_fundamentals", fetch='one')
        return result[0] if result else 0

    def get_price_data_count(self) -> int:
        """Get count of price records."""
        result = self.query("SELECT COUNT(*) FROM prices_daily", fetch='one')
        return result[0] if result else 0

    def get_current_market_count(self) -> int:
        """Get count of current market data records."""
        result = self.query("SELECT COUNT(*) FROM current_market_data", fetch='one')
        return result[0] if result else 0

    def get_latest_price_update(self) -> Optional[datetime]:
        """Get timestamp of latest price data update."""
        result = self.query("SELECT MAX(trade_date) FROM prices_daily", fetch='one')
        return result[0] if result and result[0] else None

    def get_latest_fundamentals_update(self) -> Optional[datetime]:
        """Get timestamp of latest fundamentals update."""
        result = self.query("SELECT MAX(last_fundamental_update) FROM stock_fundamentals", fetch='one')
        return result[0] if result and result[0] else None

    def truncate_table(self, table: str):
        """Truncate (empty) a table."""
        self.execute(f"TRUNCATE TABLE {table}")
        self.logger.info(f"✅ Truncated table: {table}")

    def close(self):
        """Close database connection pool."""
        if self.pool:
            self.pool.closeall()
            self.logger.info("✅ Database connection pool closed")


# ============================================================================
# GLOBAL DATABASE INSTANCE
# ============================================================================

# Global database instance for application-wide use
_db_instance = None

def get_db() -> Database:
    """Get global database instance (singleton pattern)."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance

def init_db():
    """Initialize database tables."""
    db = get_db()
    db.create_tables()

def reset_db():
    """Reset database (drop and recreate all tables)."""
    db = get_db()
    db.drop_tables()
    db.create_tables()

# ============================================================================
# CLI INTERFACE FOR MANUAL OPERATIONS
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Global Macro Scanner - Database Interface')
    parser.add_argument('command', choices=['init', 'reset', 'health', 'info', 'validate'],
                       help='Database command to execute')
    parser.add_argument('--table', help='Table name for info command')

    args = parser.parse_args()

    db = Database()

    try:
        if args.command == 'init':
            print("Initializing database...")
            db.create_tables()
            print("✅ Database initialized")

        elif args.command == 'reset':
            confirm = input("⚠️  This will delete all data. Continue? (yes/no): ")
            if confirm.lower() == 'yes':
                print("Resetting database...")
                db.drop_tables()
                db.create_tables()
                print("✅ Database reset")
            else:
                print("❌ Reset cancelled")

        elif args.command == 'health':
            print("Checking database health...")
            health = db.health_check()
            print(json.dumps(health, indent=2, default=str))

        elif args.command == 'info':
            if not args.table:
                print("❌ Please specify --table")
                exit(1)

            print(f"Getting info for table: {args.table}")
            info = db.get_table_info(args.table)
            print(json.dumps(info, indent=2, default=str))

        elif args.command == 'validate':
            print("Validating data integrity...")
            validation = db.validate_data_integrity()
            print(json.dumps(validation, indent=2, default=str))

    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
    finally:
        db.close()