"""
YFinance Rate Limiting Solutions and Best Practices

YFinance rate limits are typically around 1-2 requests per second.
With ~5000 stocks in your universe, naive sequential processing would take
40+ minutes and likely hit rate limits.

This module provides multiple strategies to handle rate limiting effectively.
"""

import time
import asyncio
from typing import List, Dict, Optional, Callable
import pandas as pd
from datetime import datetime, timedelta

# Strategy 1: Adaptive Rate Limiting
class AdaptiveRateLimiter:
    """
    Dynamically adjusts request rate based on success/failure patterns.

    - Starts conservative (0.5 req/sec)
    - Increases rate when successful
    - Decreases rate when rate limited
    - Includes exponential backoff for failures
    """

    def __init__(self, initial_rate: float = 0.5, max_rate: float = 1.0, min_rate: float = 0.1):
        self.current_rate = initial_rate
        self.max_rate = max_rate
        self.min_rate = min_rate
        self.success_count = 0
        self.failure_count = 0
        self.last_request_time = 0

    def wait_if_needed(self):
        """Wait appropriate time before next request"""
        current_time = time.time()
        min_interval = 1.0 / self.current_rate

        time_since_last = current_time - self.last_request_time
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)

        self.last_request_time = time.time()

    def record_success(self):
        """Record successful request - may increase rate"""
        self.success_count += 1
        if self.success_count >= 10 and self.current_rate < self.max_rate:
            self.current_rate = min(self.current_rate * 1.1, self.max_rate)
            self.success_count = 0  # Reset counter

    def record_failure(self):
        """Record failed request - decrease rate"""
        self.failure_count += 1
        if self.failure_count >= 3:
            self.current_rate = max(self.current_rate * 0.5, self.min_rate)
            self.failure_count = 0

# Strategy 2: Parallel Processing with Controlled Concurrency
class ControlledConcurrencyFetcher:
    """
    Process multiple tickers concurrently but with controlled parallelism
    to avoid overwhelming the API.
    """

    def __init__(self, max_concurrent: int = 5, requests_per_second: float = 1.0):
        self.max_concurrent = max_concurrent
        self.requests_per_second = requests_per_second
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = AdaptiveRateLimiter(requests_per_second)

    async def fetch_batch_concurrent(self, symbols: List[str], fetch_func: Callable) -> List[Dict]:
        """Fetch data for multiple symbols concurrently with rate limiting"""

        async def fetch_single(symbol: str) -> Optional[Dict]:
            async with self.semaphore:
                self.rate_limiter.wait_if_needed()
                try:
                    result = await asyncio.get_event_loop().run_in_executor(None, fetch_func, symbol)
                    self.rate_limiter.record_success()
                    return result
                except Exception as e:
                    self.rate_limiter.record_failure()
                    print(f"  Warning: Failed to fetch {symbol}: {e}")
                    return None

        # Create tasks for all symbols
        tasks = [fetch_single(symbol) for symbol in symbols]

        # Execute with controlled concurrency
        results = []
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                results.append(result)

        return results

# Strategy 3: Intelligent Caching with TTL
class SmartCache:
    """
    Cache with time-based expiration and intelligent invalidation.
    Only caches successful results and handles staleness.
    """

    def __init__(self, ttl_hours: int = 24, max_cache_size: int = 10000):
        self.cache = {}
        self.ttl_hours = ttl_hours
        self.max_cache_size = max_cache_size

    def get(self, key: str) -> Optional[Dict]:
        """Get cached data if still valid"""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry['timestamp'] < timedelta(hours=self.ttl_hours):
                return entry['data']
            else:
                # Expired, remove
                del self.cache[key]
        return None

    def set(self, key: str, data: Dict):
        """Cache data with timestamp"""
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entries (simple LRU approximation)
            oldest_keys = sorted(self.cache.keys(),
                               key=lambda k: self.cache[k]['timestamp'])[:100]
            for old_key in oldest_keys:
                del self.cache[old_key]

        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }

    def clear_expired(self):
        """Remove all expired entries"""
        current_time = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry['timestamp'] >= timedelta(hours=self.ttl_hours)
        ]
        for key in expired_keys:
            del self.cache[key]

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_entries = len(self.cache)
        if total_entries == 0:
            return {'entries': 0, 'hit_rate': 0, 'avg_age_hours': 0}

        current_time = datetime.now()
        ages = [(current_time - entry['timestamp']).total_seconds() / 3600
                for entry in self.cache.values()]

        return {
            'entries': total_entries,
            'avg_age_hours': sum(ages) / len(ages),
            'oldest_hours': max(ages),
            'newest_hours': min(ages)
        }

# Strategy 4: Progressive Data Fetching
class ProgressiveDataFetcher:
    """
    Fetch only essential data first, then fetch additional data as needed.
    Reduces initial API load while maintaining functionality.
    """

    def __init__(self):
        self.basic_cache = SmartCache(ttl_hours=24)  # Price/volume data
        self.extended_cache = SmartCache(ttl_hours=6)  # Technical indicators

    def fetch_basic_data(self, symbol: str) -> Optional[Dict]:
        """Fetch only essential screening data (price, volume, market cap)"""
        cache_key = f"basic_{symbol}"

        # Check cache first
        cached = self.basic_cache.get(cache_key)
        if cached:
            return cached

        try:
            import yfinance as yf
            from data.currency import usd_market_cap

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1y')

            if hist.empty:
                return None

            info = ticker.info
            current = hist['Close'].iloc[-1]
            low_52w = hist['Low'].min()
            high_52w = hist['High'].max()
            current_vol = hist['Volume'].iloc[-1]
            avg_vol_30d = hist['Volume'].tail(30).mean()
            rvol = current_vol / avg_vol_30d if avg_vol_30d > 0 else 0
            usd_mcap = usd_market_cap(symbol, info.get('marketCap', 0))

            data = {
                'symbol': symbol,
                'price': current,
                'low_52w': low_52w,
                'high_52w': high_52w,
                'volume': current_vol,
                'rvol': rvol,
                'usd_mcap': usd_mcap / 1e9,
                'has_history': True
            }

            self.basic_cache.set(cache_key, data)
            return data

        except Exception as e:
            print(f"  Warning: Failed to fetch basic data for {symbol}: {e}")
            return None

    def fetch_extended_data(self, symbol: str) -> Optional[Dict]:
        """Fetch technical indicators and extended data"""
        cache_key = f"extended_{symbol}"

        cached = self.extended_cache.get(cache_key)
        if cached:
            return cached

        try:
            import yfinance as yf
            from screening.screening_utils import calculate_rsi, calculate_sma, calculate_atr

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1y')

            if hist.empty:
                return None

            current = hist['Close'].iloc[-1]

            data = {
                'rsi': calculate_rsi(hist['Close']),
                'sma50': calculate_sma(hist['Close'], 50),
                'sma200': calculate_sma(hist['Close'], 200),
                'price_vs_sma50_pct': current / calculate_sma(hist['Close'], 50),
                'sma50_vs_sma200_pct': calculate_sma(hist['Close'], 50) / calculate_sma(hist['Close'], 200),
                'atr_pct': calculate_atr(hist['High'], hist['Low'], hist['Close'])
            }

            self.extended_cache.set(cache_key, data)
            return data

        except Exception as e:
            print(f"  Warning: Failed to fetch extended data for {symbol}: {e}")
            return None

# Strategy 5: Alternative Data Sources
class AlternativeDataSources:
    """
    Fallback data sources when yfinance is rate limited.
    """

    @staticmethod
    def try_alternative_sources(symbol: str) -> Optional[Dict]:
        """
        Try alternative free data sources as fallback.
        Returns basic price data if available.
        """

        # Try yahooquery (different API endpoints)
        try:
            from yahooquery import Ticker
            ticker = Ticker(symbol)
            hist = ticker.history(period='1y')

            if not hist.empty:
                current = hist['close'].iloc[-1]
                low_52w = hist['low'].min()
                volume = hist['volume'].iloc[-1]

                return {
                    'symbol': symbol,
                    'price': current,
                    'low_52w': low_52w,
                    'volume': volume,
                    'source': 'yahooquery'
                }
        except ImportError:
            pass  # yahooquery not installed
        except Exception:
            pass  # yahooquery failed

        # Could add more alternatives here:
        # - Alpha Vantage (requires API key)
        # - IEX Cloud (requires API key)
        # - Polygon.io (requires API key)
        # - Local cache of historical data

        return None

# Strategy 6: Request Optimization
class RequestOptimizer:
    """
    Optimize requests to minimize API calls and data transfer.
    """

    @staticmethod
    def optimize_period(criteria: Dict) -> str:
        """
        Determine minimum period needed based on criteria.
        """
        min_days = criteria.get('min_history_days', 250)

        # Map days to yfinance period
        if min_days <= 30:
            return '1mo'
        elif min_days <= 90:
            return '3mo'
        elif min_days <= 180:
            return '6mo'
        else:
            return '1y'  # Default

    @staticmethod
    def should_skip_extended_data(criteria: Dict) -> bool:
        """
        Check if we need extended technical data.
        """
        return not (
            criteria.get('rsi_enabled', False) or
            criteria.get('ma_enabled', False) or
            criteria.get('atr_enabled', False)
        )

    @staticmethod
    def filter_tickers_by_priority(tickers: List[str], criteria: Dict) -> List[str]:
        """
        Prioritize tickers that are more likely to pass screening.
        Useful for large universes where we want to process high-probability candidates first.
        """
        # For now, return as-is. Could implement market cap pre-filtering,
        # sector preferences, or other prioritization logic here.
        return tickers

# Comprehensive Solution
class RateLimitResistantProvider:
    """
    Production-ready provider that combines all rate limiting strategies.
    """

    def __init__(self, use_cache: bool = True, use_concurrency: bool = True):
        self.rate_limiter = AdaptiveRateLimiter()
        self.cache = SmartCache() if use_cache else None
        self.progressive_fetcher = ProgressiveDataFetcher()
        self.use_concurrency = use_concurrency

        if use_concurrency:
            self.concurrent_fetcher = ControlledConcurrencyFetcher()

    def get_market_data(self, tickers: List[str], criteria: Dict) -> List[Dict]:
        """
        Main entry point with all optimizations applied.
        """
        print(f"RateLimitResistantProvider: Processing {len(tickers)} tickers")

        # Optimize request strategy
        optimized_period = RequestOptimizer.optimize_period(criteria)
        needs_extended = not RequestOptimizer.should_skip_extended_data(criteria)
        prioritized_tickers = RequestOptimizer.filter_tickers_by_priority(tickers, criteria)

        results = []

        if self.use_concurrency and len(prioritized_tickers) > 10:
            # Use concurrent processing for large batches
            results = asyncio.run(self._process_concurrent(prioritized_tickers, criteria, optimized_period, needs_extended))
        else:
            # Use sequential processing for small batches
            results = self._process_sequential(prioritized_tickers, criteria, optimized_period, needs_extended)

        print(f"RateLimitResistantProvider: Found {len(results)} qualifying stocks")
        return results

    def _process_sequential(self, tickers: List[str], criteria: Dict, period: str, needs_extended: bool) -> List[Dict]:
        """Process tickers sequentially with full optimization"""
        results = []

        for symbol in tickers:
            # Try basic data first
            basic_data = self.progressive_fetcher.fetch_basic_data(symbol)
            if not basic_data:
                continue

            # Add extended data if needed
            if needs_extended:
                extended_data = self.progressive_fetcher.fetch_extended_data(symbol)
                if extended_data:
                    basic_data.update(extended_data)

            # Apply screening
            from screening.screening_utils import should_pass_screening
            filtered_result = should_pass_screening(basic_data, criteria)
            if filtered_result:
                results.append(filtered_result)

        return results

    async def _process_concurrent(self, tickers: List[str], criteria: Dict, period: str, needs_extended: bool) -> List[Dict]:
        """Process tickers concurrently with controlled parallelism"""
        async def process_symbol(symbol: str) -> Optional[Dict]:
            # Basic data fetch (required)
            basic_data = self.progressive_fetcher.fetch_basic_data(symbol)
            if not basic_data:
                return None

            # Extended data fetch (optional)
            if needs_extended:
                extended_data = self.progressive_fetcher.fetch_extended_data(symbol)
                if extended_data:
                    basic_data.update(extended_data)

            # Apply screening
            from screening.screening_utils import should_pass_screening
            filtered_result = should_pass_screening(basic_data, criteria)
            return filtered_result if filtered_result else None

        # Process with controlled concurrency
        if hasattr(self, 'concurrent_fetcher'):
            raw_results = await self.concurrent_fetcher.fetch_batch_concurrent(tickers, process_symbol)
            return [r for r in raw_results if r]
        else:
            # Fallback to sequential
            results = []
            for symbol in tickers:
                result = await process_symbol(symbol)
                if result:
                    results.append(result)
            return results

# Usage Examples and Testing
def test_rate_limiting_solutions():
    """
    Test various rate limiting approaches.
    """
    print("Testing Rate Limiting Solutions...")

    # Test basic rate limiter
    limiter = AdaptiveRateLimiter()
    print(f"Initial rate: {limiter.current_rate} req/sec")

    # Simulate some requests
    for i in range(5):
        limiter.wait_if_needed()
        limiter.record_success()
        print(f"After success {i+1}: {limiter.current_rate} req/sec")

    # Test cache
    cache = SmartCache(ttl_hours=1)
    cache.set('AAPL', {'price': 150})
    cached_data = cache.get('AAPL')
    print(f"Cache test - Retrieved: {cached_data}")

    print("Rate limiting solutions test completed.")

if __name__ == "__main__":
    test_rate_limiting_solutions()