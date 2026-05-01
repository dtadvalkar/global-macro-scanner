"""
Fundamental Data Cache for Global Market Scanner.

Read-only cache over the curated `stock_fundamentals` table (IBKR-source-of-truth).
Provides fast in-memory lookups for the runtime screening path.

Write-side methods were removed during the SQL externalization cleanup
(2026-04-30): they referenced uninitialized `self.db_config` / `self.ttl_settings`
and would have AttributeErrored if called. They also targeted the legacy
YFinance-shaped 10-column schema, not the curated 80+-column IBKR schema.
If TTL caching or write-back is wanted later, re-introduce as a fresh feature.
"""

from db import get_db


class FundamentalCacheManager:
    """In-memory cache backed by stock_fundamentals; read-only at runtime."""

    def __init__(self, use_database=True):
        self.use_database = use_database
        self.memory_cache = {}
        self.db = get_db() if use_database else None
        if use_database:
            self.ensure_table_exists()

    def ensure_table_exists(self):
        """Verify stock_fundamentals exists with the curated FinanceDatabase schema."""
        if not self.use_database:
            return
        try:
            table_exists = self.db.query("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'stock_fundamentals'
                )
            """, fetch='one')

            if table_exists and table_exists[0]:
                has_fd_columns = self.db.query("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'stock_fundamentals'
                        AND column_name = 'mkt_cap_usd'
                    )
                """, fetch='one')

                if has_fd_columns and has_fd_columns[0]:
                    print("stock_fundamentals table exists with FinanceDatabase schema")
                    return

            # If we got here the curated schema is missing — flatten_ibkr_final.py
            # is responsible for creating it via sql/schema/stock_fundamentals.sql.
            print("stock_fundamentals not found with curated schema; run flatten_ibkr_final.py")

        except Exception as e:
            print(f"Error checking fundamentals table: {e}")

    def get_fundamentals(self, ticker):
        """Get cached fundamental data for a ticker (memory-first, then DB)."""
        if ticker in self.memory_cache:
            return self.memory_cache[ticker]

        if not self.use_database:
            return None

        try:
            result = self.db.query("""
                SELECT ticker, exchange_code, mkt_cap_usd, industry_trbc, industry_naics,
                       price_currency, country_code, last_fundamental_update,
                       xml_52w_low, xml_52w_high
                FROM stock_fundamentals
                WHERE ticker = %s
            """, (ticker,), fetch='one')

            if result:
                fundamentals = {
                    'ticker': result[0],
                    'symbol': result[0].split('.')[0],
                    'exchange': result[1],
                    'market_cap_usd': float(result[2]) if result[2] is not None else 0.0,
                    'sector': result[3],
                    'industry': result[4],
                    'currency': result[5],
                    'country': result[6],
                    'last_updated': result[7],
                    'xml_52w_low': float(result[8]) if result[8] is not None else None,
                    'xml_52w_high': float(result[9]) if result[9] is not None else None,
                    'data_source': 'ibkr',
                    'is_active': True,
                    'metadata': {}
                }
                self.memory_cache[ticker] = fundamentals
                return fundamentals

        except Exception as e:
            print(f"Error fetching fundamentals for {ticker}: {e}")

        return None
