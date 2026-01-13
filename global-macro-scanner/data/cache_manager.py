"""
Fundamental Data Cache System for Global Market Scanner
Stores core company data (market cap, sector, etc.) to enable early filtering without API calls.

This is the foundation of our efficiency strategy: filter out obviously unqualified stocks
before making any expensive API calls to get price data.
"""

import time
import json
import os
from datetime import datetime, timedelta
import psycopg2
from config import DB_CONFIG
import hashlib

class FundamentalCacheManager:
    """
    Fundamental Data Cache - The Efficiency Foundation

    Database Table: stock_fundamentals
    Purpose: Store basic company data for instant filtering
    Impact: Eliminates 80-90% of API calls through early filtering
    """

    def __init__(self, db_config=None, use_database=True):
        self.use_database = use_database
        if use_database:
            self.db_config = self._normalize_db_config(db_config or DB_CONFIG)
            self.memory_cache = {}  # Fast in-memory cache
            self.ensure_table_exists()
        else:
            self.memory_cache = {}  # Only use in-memory cache

    def _normalize_db_config(self, config):
        """Normalize database config for psycopg2 compatibility"""
        normalized = config.copy()
        # Map common parameter names to psycopg2 expected names
        param_mapping = {
            'db_name': 'database',
            'db_user': 'user',
            'db_pass': 'password',
            'db_host': 'host',
            'db_port': 'port'
        }
        for old_key, new_key in param_mapping.items():
            if old_key in normalized:
                normalized[new_key] = normalized.pop(old_key)
        return normalized

    def ensure_table_exists(self):
        """Create the fundamentals table with proper indexes"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            # Main fundamentals table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_fundamentals (
                    ticker VARCHAR(20) PRIMARY KEY,
                    symbol VARCHAR(20),                    -- Clean symbol without suffix
                    exchange VARCHAR(10),                 -- NSE, TSE, ASX, etc.
                    market_cap_usd BIGINT,                -- Market cap in USD (millions)
                    sector VARCHAR(100),                  -- Technology, Healthcare, etc.
                    industry VARCHAR(100),                -- Software, Pharmaceuticals, etc.
                    currency VARCHAR(3),                  -- USD, CAD, INR, etc.
                    country VARCHAR(50),                  -- United States, Canada, etc.
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_source VARCHAR(20),              -- 'yfinance', 'ibkr', 'manual'
                    is_active BOOLEAN DEFAULT TRUE,       -- Still trading?
                    metadata JSONB                        -- Additional flexible data
                );

                -- Indexes for fast filtering
                CREATE INDEX IF NOT EXISTS idx_fundamentals_exchange ON stock_fundamentals(exchange);
                CREATE INDEX IF NOT EXISTS idx_fundamentals_market_cap ON stock_fundamentals(market_cap_usd);
                CREATE INDEX IF NOT EXISTS idx_fundamentals_sector ON stock_fundamentals(sector);
                CREATE INDEX IF NOT EXISTS idx_fundamentals_updated ON stock_fundamentals(last_updated);
                CREATE INDEX IF NOT EXISTS idx_fundamentals_active ON stock_fundamentals(is_active) WHERE is_active = TRUE;
            """)

            conn.commit()
            cur.close()
            conn.close()
            print("stock_fundamentals table ready")

        except Exception as e:
            print(f"Error creating fundamentals table: {e}")

    # ==================== EARLY FILTERING METHODS ====================

    def can_skip_by_fundamentals(self, ticker, criteria):
        """
        The key efficiency method: check if we can skip this ticker entirely
        based on cached fundamental data, without making any API calls.

        Returns: (can_skip: bool, reason: str)
        """
        if not self.use_database:
            return False, "Database disabled - process all"  # Skip filtering without DB

        fundamentals = self.get_fundamentals(ticker)

        if not fundamentals:
            return False, "No cached fundamentals"  # Need to fetch

        # Check market cap threshold
        market_cap = fundamentals.get('market_cap_usd')
        if market_cap:
            # Get appropriate threshold for this exchange
            from config.markets import get_min_market_cap
            exchange = fundamentals.get('exchange', 'SMART')
            min_cap = get_min_market_cap(exchange)

            if market_cap < min_cap:
                return True, f"Market cap ${market_cap/1000000:.0f}M < threshold ${min_cap/1000000:.0f}M"

        # Check if stock is still active
        if not fundamentals.get('is_active', True):
            return True, "Stock no longer active"

        # Check data freshness (don't use very old data)
        last_updated = fundamentals.get('last_updated')
        if last_updated:
            days_old = (datetime.now() - last_updated).days
            if days_old > 30:  # Data too old, need refresh
                return False, f"Data {days_old} days old, needs refresh"

        return False, "Passes fundamental filters"

    # ==================== FUNDAMENTAL DATA MANAGEMENT ====================

    def get_fundamentals(self, ticker):
        """Get cached fundamental data for a ticker"""
        # Check memory cache first
        if ticker in self.memory_cache:
            return self.memory_cache[ticker]

        # Check database
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("""
                SELECT symbol, exchange, market_cap_usd, sector, industry,
                       currency, country, last_updated, data_source, is_active, metadata
                FROM stock_fundamentals
                WHERE ticker = %s AND is_active = TRUE
            """, (ticker,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if result:
                fundamentals = {
                    'ticker': ticker,
                    'symbol': result[0],
                    'exchange': result[1],
                    'market_cap_usd': result[2],
                    'sector': result[3],
                    'industry': result[4],
                    'currency': result[5],
                    'country': result[6],
                    'last_updated': result[7],
                    'data_source': result[8],
                    'is_active': result[9],
                    'metadata': result[10] or {}
                }

                # Cache in memory
                self.memory_cache[ticker] = fundamentals
                return fundamentals

        except Exception as e:
            print(f"Error fetching fundamentals for {ticker}: {e}")

        return None

    def set_fundamentals(self, ticker, fundamentals_dict, data_source='yfinance'):
        """Store or update fundamental data for a single ticker"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            # Prepare data
            symbol = fundamentals_dict.get('symbol', ticker.split('.')[0])
            
            # Smart Exchange Derivation: Avoid defaulting to 'SMART' for international markets
            exchange = fundamentals_dict.get('exchange')
            if not exchange:
                if '.NS' in ticker: exchange = 'NSE'
                elif '.TO' in ticker: exchange = 'TSE'
                elif '.AX' in ticker: exchange = 'ASX'
                elif '.SI' in ticker: exchange = 'SGX'
                elif '.DE' in ticker: exchange = 'IBIS'
                elif '.PA' in ticker: exchange = 'SBF'
                elif '.JK' in ticker: exchange = 'IDX'
                elif '.BK' in ticker: exchange = 'SET'
                else: exchange = 'SMART' # Default to SMART for US/Unknown
            
            market_cap = fundamentals_dict.get('market_cap_usd')
            sector = fundamentals_dict.get('sector')
            industry = fundamentals_dict.get('industry')
            currency = fundamentals_dict.get('currency', 'USD')
            country = fundamentals_dict.get('country')
            is_active = fundamentals_dict.get('is_active', True)
            metadata = fundamentals_dict.get('metadata', {})

            # Upsert fundamentals
            cur.execute("""
                INSERT INTO stock_fundamentals
                (ticker, symbol, exchange, market_cap_usd, sector, industry,
                 currency, country, data_source, is_active, metadata, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (ticker)
                DO UPDATE SET
                    symbol = EXCLUDED.symbol,
                    exchange = EXCLUDED.exchange,
                    market_cap_usd = EXCLUDED.market_cap_usd,
                    sector = EXCLUDED.sector,
                    industry = EXCLUDED.industry,
                    currency = EXCLUDED.currency,
                    country = EXCLUDED.country,
                    data_source = EXCLUDED.data_source,
                    is_active = EXCLUDED.is_active,
                    metadata = EXCLUDED.metadata,
                    last_updated = CURRENT_TIMESTAMP
            """, (
                ticker, symbol, exchange, market_cap, sector, industry,
                currency, country, data_source, is_active, json.dumps(metadata)
            ))

            conn.commit()
            cur.close()
            conn.close()

            # Update memory cache
            fundamentals_dict['last_updated'] = datetime.now()
            self.memory_cache[ticker] = fundamentals_dict

        except Exception as e:
            print(f"Error storing fundamentals for {ticker}: {e}")

    def set_fundamentals_batch(self, fundamentals_list, data_source='yfinance'):
        """Store or update multiple fundamental records at once"""
        if not fundamentals_list:
            return

        try:
            from datetime import datetime
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            # Prepare data for batch insert
            batch_data = []
            for item in fundamentals_list:
                ticker = item['ticker']
                symbol = item.get('symbol', ticker.split('.')[0])
                exchange = item.get('exchange', 'SMART')
                market_cap = item.get('market_cap_usd')
                sector = item.get('sector')
                industry = item.get('industry')
                currency = item.get('currency', 'USD')
                country = item.get('country')
                is_active = item.get('is_active', True)
                metadata = item.get('metadata', {})

                batch_data.append((
                    ticker, symbol, exchange, market_cap, sector, industry,
                    currency, country, data_source, is_active, json.dumps(metadata),
                    datetime.now()
                ))

            # Bulk insert using execute_values
            from psycopg2.extras import execute_values
            try:
                execute_values(
                    cur,
                    """
                    INSERT INTO stock_fundamentals
                    (ticker, symbol, exchange, market_cap_usd, sector, industry,
                     currency, country, data_source, is_active, metadata, last_updated)
                    VALUES %s
                    ON CONFLICT (ticker)
                    DO UPDATE SET
                        symbol = EXCLUDED.symbol,
                        exchange = EXCLUDED.exchange,
                        market_cap_usd = EXCLUDED.market_cap_usd,
                        sector = EXCLUDED.sector,
                        industry = EXCLUDED.industry,
                        currency = EXCLUDED.currency,
                        country = EXCLUDED.country,
                        data_source = EXCLUDED.data_source,
                        is_active = EXCLUDED.is_active,
                        metadata = EXCLUDED.metadata,
                        last_updated = CURRENT_TIMESTAMP
                    """,
                    batch_data
                )
            except Exception as batch_error:
                print(f"DEBUG: Batch insert failed ({batch_error}).")
                # Removed experimental fallback to avoid more errors; just raise and trace.
                raise batch_error

            conn.commit()
            cur.close()
            conn.close()
            
            # Clear memory cache to ensure fresh data
            self.memory_cache.clear()

        except Exception as e:
            import traceback
            print(f"Error storing batch fundamentals: {e}")
            traceback.print_exc()

    # ==================== BULK OPERATIONS ====================

    def get_fundamentals_batch(self, tickers):
        """Get fundamentals for multiple tickers efficiently"""
        if not tickers:
            return {}

        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            # Create placeholders for IN clause
            placeholders = ','.join(['%s'] * len(tickers))

            cur.execute(f"""
                SELECT ticker, symbol, exchange, market_cap_usd, sector, industry,
                       currency, country, last_updated, data_source, is_active, metadata
                FROM stock_fundamentals
                WHERE ticker IN ({placeholders}) AND is_active = TRUE
            """, tickers)

            results = {}
            for row in cur.fetchall():
                ticker = row[0]
                results[ticker] = {
                    'ticker': ticker,
                    'symbol': row[1],
                    'exchange': row[2],
                    'market_cap_usd': row[3],
                    'sector': row[4],
                    'industry': row[5],
                    'currency': row[6],
                    'country': row[7],
                    'last_updated': row[8],
                    'data_source': row[9],
                    'is_active': row[10],
                    'metadata': row[11] or {}
                }

            cur.close()
            conn.close()

            # Update memory cache
            self.memory_cache.update(results)

            return results

        except Exception as e:
            print(f"Error in batch fundamentals fetch: {e}")
            return {}

    def get_market_cap_stats(self, exchange=None):
        """Get market cap statistics for analysis"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            query = """
                SELECT
                    COUNT(*) as total_stocks,
                    AVG(market_cap_usd) as avg_market_cap,
                    MIN(market_cap_usd) as min_market_cap,
                    MAX(market_cap_usd) as max_market_cap,
                    COUNT(CASE WHEN market_cap_usd < 100000000 THEN 1 END) as under_100m,
                    COUNT(CASE WHEN market_cap_usd BETWEEN 100000000 AND 500000000 THEN 1 END) as small_cap,
                    COUNT(CASE WHEN market_cap_usd > 500000000 THEN 1 END) as mid_large_cap
                FROM stock_fundamentals
                WHERE is_active = TRUE
            """

            if exchange:
                query += " AND exchange = %s"
                cur.execute(query, (exchange,))
            else:
                cur.execute(query)

            result = cur.fetchone()
            cur.close()
            conn.close()

            if result:
                return {
                    'total_stocks': result[0],
                    'avg_market_cap': result[1],
                    'min_market_cap': result[2],
                    'max_market_cap': result[3],
                    'under_100m': result[4],
                    'small_cap': result[5],
                    'mid_large_cap': result[6]
                }

        except Exception as e:
            print(f"Error getting market cap stats: {e}")

        return None

    # ==================== UTILITY METHODS ====================

    def cleanup_old_data(self, days_old=90):
        """Remove very old fundamental data"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days_old)
            cur.execute("""
                UPDATE stock_fundamentals
                SET is_active = FALSE
                WHERE last_updated < %s
            """, (cutoff_date,))

            updated_count = cur.rowcount
            conn.commit()
            cur.close()
            conn.close()

            print(f"Marked {updated_count} old records as inactive")

        except Exception as e:
            print(f"Error cleaning up old data: {e}")

    def export_fundamentals_csv(self, filename="fundamentals_export.csv"):
        """Export fundamentals data for analysis"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("""
                SELECT ticker, symbol, exchange, market_cap_usd, sector, industry,
                       currency, country, last_updated, data_source
                FROM stock_fundamentals
                WHERE is_active = TRUE
                ORDER BY market_cap_usd DESC NULLS LAST
            """)

            with open(filename, 'w') as f:
                # Write header
                f.write("ticker,symbol,exchange,market_cap_usd,sector,industry,currency,country,last_updated,data_source\n")

                # Write data
                for row in cur.fetchall():
                    # Format market cap
                    market_cap = row[3]
                    if market_cap:
                        market_cap_str = f"{market_cap:,}"
                    else:
                        market_cap_str = ""

                    # Format date
                    last_updated = row[8]
                    if last_updated:
                        date_str = last_updated.strftime("%Y-%m-%d")
                    else:
                        date_str = ""

                    # Write row
                    f.write(f"{row[0]},{row[1]},{row[2]},{market_cap_str},{row[4]},{row[5]},{row[6]},{row[7]},{date_str},{row[9]}\n")

            cur.close()
            conn.close()

            print(f"Exported fundamentals to {filename}")

        except Exception as e:
            print(f"Error exporting fundamentals: {e}")

    def _get_cache_key(self, ticker, data_type, criteria_version=None):
        """Generate consistent cache key"""
        key_parts = [ticker, data_type]
        if criteria_version:
            key_parts.append(str(criteria_version))
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

    def _get_criteria_version(self, criteria):
        """Generate version hash for criteria to detect changes"""
        criteria_str = json.dumps(criteria, sort_keys=True)
        return hashlib.md5(criteria_str.encode()).hexdigest()[:8]

    # ==================== FILTERING RESULTS CACHE ====================

    def check_filtering_cache(self, ticker, criteria):
        """
        Check if we should skip this ticker based on recent filtering results.

        Returns:
            (should_skip: bool, reason: str, cached_result: dict)
        """
        criteria_version = self._get_criteria_version(criteria)
        cache_key = self._get_cache_key(ticker, 'filtering', criteria_version)

        # Check memory cache first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if self._is_fresh(entry['timestamp'], self.ttl_settings['filtering_results']):
                return entry['should_skip'], entry.get('reason', ''), entry
            else:
                del self.memory_cache[cache_key]  # Remove expired

        # Check database cache
        db_result = self._get_db_cache(cache_key)
        if db_result and self._is_fresh(db_result['timestamp'], self.ttl_settings['filtering_results']):
            # Store in memory for faster future access
            self.memory_cache[cache_key] = db_result
            return db_result['should_skip'], db_result.get('reason', ''), db_result

        return False, '', None

    def cache_filtering_result(self, ticker, criteria, should_skip, reason='', result_data=None):
        """Cache a filtering decision"""
        criteria_version = self._get_criteria_version(criteria)
        cache_key = self._get_cache_key(ticker, 'filtering', criteria_version)

        cache_entry = {
            'ticker': ticker,
            'should_skip': should_skip,
            'reason': reason,
            'result_data': result_data,
            'timestamp': time.time(),
            'criteria_version': criteria_version,
            'data_type': 'filtering'
        }

        # Store in memory
        self.memory_cache[cache_key] = cache_entry

        # Store in database (async/background)
        self._set_db_cache(cache_key, cache_entry)

    # ==================== METADATA CACHE ====================

    def get_metadata(self, ticker):
        """Get cached metadata (market cap, exchange, etc.)"""
        cache_key = self._get_cache_key(ticker, 'metadata')

        # Check memory first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if self._is_fresh(entry['timestamp'], self.ttl_settings['metadata']):
                return entry['data']

        # Check database
        db_result = self._get_db_cache(cache_key)
        if db_result and self._is_fresh(db_result['timestamp'], self.ttl_settings['metadata']):
            self.memory_cache[cache_key] = db_result
            return db_result['data']

        return None

    def set_metadata(self, ticker, metadata_dict):
        """Cache metadata"""
        cache_key = self._get_cache_key(ticker, 'metadata')

        cache_entry = {
            'ticker': ticker,
            'data': metadata_dict,
            'timestamp': time.time(),
            'data_type': 'metadata'
        }

        self.memory_cache[cache_key] = cache_entry
        self._set_db_cache(cache_key, cache_entry)

    # ==================== API RESPONSES CACHE ====================

    def get_api_response(self, ticker, data_type='price_data'):
        """Get cached API response"""
        cache_key = self._get_cache_key(ticker, f'api_{data_type}')

        # Check memory first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if self._is_fresh(entry['timestamp'], self.ttl_settings['api_responses']):
                return entry['data']

        # Check database
        db_result = self._get_db_cache(cache_key)
        if db_result and self._is_fresh(db_result['timestamp'], self.ttl_settings['api_responses']):
            self.memory_cache[cache_key] = db_result
            return db_result['data']

        return None

    def set_api_response(self, ticker, response_data, data_type='price_data'):
        """Cache API response"""
        cache_key = self._get_cache_key(ticker, f'api_{data_type}')

        cache_entry = {
            'ticker': ticker,
            'data': response_data,
            'timestamp': time.time(),
            'data_type': f'api_{data_type}'
        }

        self.memory_cache[cache_key] = cache_entry
        self._set_db_cache(cache_key, cache_entry)

    # ==================== UTILITY METHODS ====================

    def _is_fresh(self, timestamp, ttl_seconds):
        """Check if cache entry is still fresh"""
        return (time.time() - timestamp) < ttl_seconds

    def _get_db_cache(self, cache_key):
        """Retrieve from database cache"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            cur.execute("""
                SELECT data, timestamp, data_type
                FROM cache_entries
                WHERE cache_key = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (cache_key,))

            result = cur.fetchone()
            cur.close()
            conn.close()

            if result:
                data, timestamp, data_type = result
                return {
                    'data': json.loads(data) if isinstance(data, str) else data,
                    'timestamp': timestamp.timestamp() if hasattr(timestamp, 'timestamp') else timestamp,
                    'data_type': data_type
                }

        except Exception as e:
            print(f"Cache DB read error: {e}")
            return None

        return None

    def _set_db_cache(self, cache_key, cache_entry):
        """Store in database cache (async/background)"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            # Create table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key VARCHAR(255) PRIMARY KEY,
                    data JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_type VARCHAR(50)
                )
            """)

            # Upsert cache entry
            cur.execute("""
                INSERT INTO cache_entries (cache_key, data, timestamp, data_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (cache_key)
                DO UPDATE SET
                    data = EXCLUDED.data,
                    timestamp = EXCLUDED.timestamp,
                    data_type = EXCLUDED.data_type
            """, (
                cache_key,
                json.dumps(cache_entry['data']) if 'data' in cache_entry else json.dumps(cache_entry),
                datetime.fromtimestamp(cache_entry['timestamp']),
                cache_entry.get('data_type', 'unknown')
            ))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print(f"Cache DB write error: {e}")

    def clear_expired_cache(self):
        """Remove expired entries from memory and database"""
        current_time = time.time()

        # Clear memory cache
        expired_keys = []
        for key, entry in self.memory_cache.items():
            ttl = self.ttl_settings.get(entry.get('data_type', 'filtering_results'), 3600)
            if not self._is_fresh(entry['timestamp'], ttl):
                expired_keys.append(key)

        for key in expired_keys:
            del self.memory_cache[key]

        print(f"Cleared {len(expired_keys)} expired memory cache entries")

        # Clear database cache (optional - can be done periodically)
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            for data_type, ttl in self.ttl_settings.items():
                cutoff_time = datetime.now() - timedelta(seconds=ttl)
                cur.execute("""
                    DELETE FROM cache_entries
                    WHERE data_type = %s AND timestamp < %s
                """, (data_type, cutoff_time))

            deleted_count = cur.rowcount
            conn.commit()
            cur.close()
            conn.close()

            print(f"Cleared {deleted_count} expired database cache entries")

        except Exception as e:
            print(f"Cache cleanup error: {e}")

    def get_cache_stats(self):
        """Get cache performance statistics"""
        stats = {
            'memory_entries': len(self.memory_cache),
            'cache_types': {},
            'hit_rates': {},  # Would need to track hits/misses separately
        }

        for entry in self.memory_cache.values():
            data_type = entry.get('data_type', 'unknown')
            stats['cache_types'][data_type] = stats['cache_types'].get(data_type, 0) + 1

        return stats

# ==================== INTEGRATION WITH PROVIDERS ====================

def integrate_with_yfinance_provider():
    """
    How to integrate fundamental caching with YFinanceProvider

    Before making expensive API calls, check fundamentals cache.
    This can eliminate 80-90% of API calls instantly.
    """

    from data.providers import OptimizedYFinanceProvider

    class FundamentalsAwareYFinanceProvider(OptimizedYFinanceProvider):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fundamentals_cache = FundamentalCacheManager()

        def get_market_data(self, tickers, criteria):
            """Enhanced with fundamental pre-filtering"""

            # Phase 1: Fundamental filtering (no API calls)
            viable_tickers = []
            skipped_by_fundamentals = 0

            for ticker in tickers:
                can_skip, reason = self.fundamentals_cache.can_skip_by_fundamentals(ticker, criteria)
                if can_skip:
                    print(f"🚫 Skipped {ticker}: {reason}")
                    skipped_by_fundamentals += 1
                else:
                    viable_tickers.append(ticker)

            print(f"📊 Fundamental pre-filtering: {len(viable_tickers)}/{len(tickers)} tickers viable ({skipped_by_fundamentals} skipped)")

            if not viable_tickers:
                return []

            # Phase 2: Normal processing for viable tickers
            results = []
            for ticker in viable_tickers:
                try:
                    # Your existing processing logic here
                    result = self._process_single_ticker(ticker, criteria)
                    if result:
                        results.append(result)

                        # Update fundamentals cache with fresh data
                        if 'market_cap_usd' in result:
                            fundamentals = {
                                'symbol': ticker.split('.')[0],
                                'exchange': self._get_exchange_from_ticker(ticker),
                                'market_cap_usd': result['market_cap_usd'] * 1e6,  # Convert to full USD
                                'sector': result.get('sector'),
                                'industry': result.get('industry'),
                                'currency': 'USD',  # Assuming conversion already done
                                'country': self._get_country_from_exchange(ticker)
                            }
                            self.fundamentals_cache.set_fundamentals(ticker, fundamentals)

                except Exception as e:
                    print(f"Error processing {ticker}: {e}")

            return results

# ==================== USAGE EXAMPLES ====================

def example_usage():
    """Demonstrate the fundamental caching system"""

    print("🚀 Fundamental Cache Manager Demo")
    print("=" * 50)

    cache = FundamentalCacheManager()

    # Example: Store fundamentals for a stock
    fundamentals_data = {
        'symbol': 'AAPL',
        'exchange': 'SMART',
        'market_cap_usd': 3000000000000,  # $3T
        'sector': 'Technology',
        'industry': 'Consumer Electronics',
        'currency': 'USD',
        'country': 'United States'
    }

    print("1. Storing fundamentals for AAPL...")
    cache.set_fundamentals('AAPL', fundamentals_data)

    # Example: Check if we can skip by fundamentals
    from config import CRITERIA
    print("\n2. Testing fundamental filtering...")

    can_skip, reason = cache.can_skip_by_fundamentals('AAPL', CRITERIA)
    print(f"AAPL skip check: {can_skip} - {reason}")

    # Example: Small cap stock that should be skipped
    small_cap_data = {
        'symbol': 'MICRO',
        'exchange': 'SMART',
        'market_cap_usd': 50000000,  # $50M - below threshold
        'sector': 'Technology',
        'industry': 'Software',
        'currency': 'USD',
        'country': 'United States'
    }

    print("\n3. Testing small cap filtering...")
    cache.set_fundamentals('MICRO', small_cap_data)
    can_skip, reason = cache.can_skip_by_fundamentals('MICRO', CRITERIA)
    print(f"MICRO skip check: {can_skip} - {reason}")

    # Example: Get market cap statistics
    print("\n4. Market cap statistics...")
    stats = cache.get_market_cap_stats()
    if stats:
        print(f"Total stocks cached: {stats['total_stocks']}")
        print(f"Average market cap: ${stats['avg_market_cap']/1e9:.1f}B")
        print(f"Small caps (<$100M): {stats['under_100m']}")

    print("\nFundamental caching system ready!")

if __name__ == '__main__':
    example_usage()