"""
Optimized YFinance Provider with Rate Limiting Workarounds
"""

import yfinance as yf
import asyncio
import time
import pandas as pd
from typing import List, Dict, Optional
from data.currency import usd_market_cap
from datetime import datetime
from screening.screening_utils import should_pass_screening, calculate_rsi, calculate_sma, calculate_atr

class BaseProvider:
    def get_market_data(self, tickers, criteria):
        raise NotImplementedError

class OptimizedYFinanceProvider(BaseProvider):
    """
    Optimized YFinance provider with rate limiting workarounds.

    Strategies to avoid rate limits:
    1. Batch processing with controlled concurrency
    2. Exponential backoff on failures
    3. Intelligent caching and retry logic
    4. Reduced data requests (only fetch what's needed)
    """

    def __init__(self, requests_per_second: float = 0.5, max_retries: int = 3):
        self.requests_per_second = requests_per_second
        self.max_retries = max_retries
        self.request_times = []
        self._rate_limit_delay()

    def _rate_limit_delay(self):
        """Enforce rate limiting to avoid Yahoo Finance throttling"""
        current_time = time.time()

        # Clean old timestamps (keep last 60 seconds)
        self.request_times = [t for t in self.request_times if current_time - t < 60]

        # Calculate required delay
        if len(self.request_times) >= self.requests_per_second * 60:
            # Too many requests, wait until we can make another
            oldest_allowed = current_time - 60
            sleep_time = max(0, self.request_times[0] - oldest_allowed + 1/self.requests_per_second)
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.request_times.append(current_time)

    def _fetch_with_retry(self, symbols: List[str], period: str = "1y") -> Optional[pd.DataFrame]:
        """Fetch data with exponential backoff retry logic"""
        for attempt in range(self.max_retries):
            try:
                self._rate_limit_delay()

                if len(symbols) == 1:
                    # Single ticker
                    ticker = yf.Ticker(symbols[0])
                    data = ticker.history(period=period)
                    return data
                else:
                    # Multiple tickers (limited batch)
                    tickers = yf.Tickers(symbols)
                    data = tickers.history(period=period)
                    return data

            except Exception as e:
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s...
                    delay = 2 ** attempt
                    print(f"  Warning: YFinance error (attempt {attempt + 1}/{self.max_retries}): {e}")
                    print(f"  Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print(f"  Error: Failed to fetch data after {self.max_retries} attempts: {e}")
                    return None

        return None

    def get_market_data(self, tickers: List[str], criteria: Dict) -> List[Dict]:
        """
        Optimized batch processing with rate limiting and caching.

        Strategies:
        1. Process in small batches (10-20 tickers) to avoid rate limits
        2. Add delays between batches
        3. Retry failed requests with exponential backoff
        4. Only fetch required data (no unnecessary API calls)
        """
        results = []
        batch_size = 10  # Conservative batch size to avoid rate limits

        print(f"YFinance: Processing {len(tickers)} stocks in batches of {batch_size}")

        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            print(f"  Batch {i//batch_size + 1}/{(len(tickers) + batch_size - 1)//batch_size}: {len(batch)} stocks")

            # Process batch
            batch_results = self._process_batch(batch, criteria)
            results.extend(batch_results)

            # Small delay between batches
            if i + batch_size < len(tickers):
                time.sleep(1.0)  # 1 second between batches

        print(f"YFinance: Completed processing {len(results)} qualified stocks")
        return results

    def _process_batch(self, symbols: List[str], criteria: Dict) -> List[Dict]:
        """Process a batch of symbols"""
        batch_results = []

        # For now, process individually but with rate limiting
        # TODO: Implement true batch downloading when yfinance supports it better
        for symbol in symbols:
            try:
                # Fetch historical data
                hist_data = self._fetch_with_retry([symbol], period="1y")

                if hist_data is None or hist_data.empty:
                    continue

                # Validate minimum history
                if len(hist_data) < criteria.get('min_history_days', 250):
                    continue

                # Fetch info data (separate rate-limited call)
                info_data = self._fetch_info_with_retry(symbol)
                if not info_data:
                    continue

                # Extract basic price data
                current = hist_data['Close'].iloc[-1]
                low_52w = hist_data['Low'].min()
                high_52w = hist_data['High'].max()
                current_vol = hist_data['Volume'].iloc[-1]
                avg_vol_30d = hist_data['Volume'].tail(30).mean()
                rvol = current_vol / avg_vol_30d if avg_vol_30d > 0 else 0

                # Get market cap
                usd_mcap = usd_market_cap(symbol, info_data.get('marketCap', 0))

                # Prepare data for centralized screening
                symbol_data = {
                    'symbol': symbol,
                    'price': current,
                    'low_52w': low_52w,
                    'high_52w': high_52w,
                    'usd_mcap': usd_mcap / 1e9,  # Convert to billions
                    'rvol': rvol,
                    'volume': current_vol,
                    'time': datetime.now()
                }

                # Calculate technical indicators only if enabled
                if criteria.get('rsi_enabled', False):
                    symbol_data['rsi'] = calculate_rsi(hist_data['Close'])

                if criteria.get('ma_enabled', False):
                    sma50 = calculate_sma(hist_data['Close'], 50)
                    sma200 = calculate_sma(hist_data['Close'], 200)
                    symbol_data['price_vs_sma50_pct'] = current / sma50 if sma50 > 0 else 1.0
                    symbol_data['sma50_vs_sma200_pct'] = sma50 / sma200 if sma200 > 0 else 1.0

                if criteria.get('atr_enabled', False):
                    symbol_data['atr_pct'] = calculate_atr(hist_data['High'], hist_data['Low'], hist_data['Close'])

                # Apply centralized screening
                filtered_result = should_pass_screening(symbol_data, criteria)
                if filtered_result:
                    batch_results.append(filtered_result)

            except Exception as e:
                print(f"  Warning: Failed to process {symbol}: {str(e)[:50]}")

        return batch_results

    def _fetch_info_with_retry(self, symbol: str) -> Optional[Dict]:
        """Fetch ticker info with retry logic"""
        for attempt in range(self.max_retries):
            try:
                self._rate_limit_delay()
                ticker = yf.Ticker(symbol)
                return ticker.info
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = 2 ** attempt
                    time.sleep(delay)
                else:
                    return None
        return None

class CachedYFinanceProvider(OptimizedYFinanceProvider):
    """
    Cached version that stores results to avoid repeated API calls.

    Useful for development/testing or when scanning the same universe frequently.
    """

    def __init__(self, cache_file: str = "yfinance_cache.pkl", cache_expiry_hours: int = 24, **kwargs):
        super().__init__(**kwargs)
        self.cache_file = cache_file
        self.cache_expiry_hours = cache_expiry_hours
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cached data if it exists and isn't expired"""
        try:
            import pickle
            import os
            from datetime import datetime, timedelta

            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)

                # Check if cache is expired
                cache_time = cache_data.get('_timestamp', datetime.min)
                if datetime.now() - cache_time < timedelta(hours=self.cache_expiry_hours):
                    print(f"Loaded YFinance cache from {self.cache_file}")
                    return cache_data

            print("YFinance cache expired or missing, starting fresh")
        except Exception as e:
            print(f"Warning: Could not load YFinance cache: {e}")

        return {'_timestamp': datetime.now()}

    def _save_cache(self):
        """Save cache to disk"""
        try:
            import pickle
            self.cache['_timestamp'] = datetime.now()
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
            print(f"Saved YFinance cache to {self.cache_file}")
        except Exception as e:
            print(f"Warning: Could not save YFinance cache: {e}")

    def _fetch_with_retry(self, symbols: List[str], period: str = "1y") -> Optional[pd.DataFrame]:
        """Cached version of fetch with retry"""
        cache_key = f"{'_'.join(symbols)}_{period}"

        # Check cache first
        if cache_key in self.cache:
            print(f"  Cache hit for {len(symbols)} symbols")
            return self.cache[cache_key]

        # Fetch from API
        result = super()._fetch_with_retry(symbols, period)

        # Cache the result
        if result is not None:
            self.cache[cache_key] = result
            self._save_cache()

        return result

    def __del__(self):
        """Save cache on exit"""
        if hasattr(self, 'cache'):
            self._save_cache()

# Alternative: Use yahooquery (more reliable but less features)
class YahooQueryProvider(BaseProvider):
    """
    Alternative provider using yahooquery library.
    May have different rate limits and reliability characteristics.
    """

    def __init__(self):
        try:
            from yahooquery import Ticker
            self.Ticker = Ticker
        except ImportError:
            raise ImportError("yahooquery not installed. Install with: pip install yahooquery")

    def get_market_data(self, tickers: List[str], criteria: Dict) -> List[Dict]:
        """Fetch data using yahooquery (alternative to yfinance)"""
        results = []

        for symbol in tickers:
            try:
                # yahooquery uses different API patterns
                ticker = self.Ticker(symbol)

                # Get historical data
                hist = ticker.history(period='1y')
                if hist.empty:
                    continue

                # Get summary detail (equivalent to yfinance.info)
                summary = ticker.summary_detail
                if not summary:
                    continue

                # Extract data (yahooquery has different data structure)
                current = hist['close'].iloc[-1]
                low_52w = hist['low'].min()
                high_52w = hist['high'].max()
                current_vol = hist['volume'].iloc[-1]
                avg_vol_30d = hist['volume'].tail(30).mean()
                rvol = current_vol / avg_vol_30d if avg_vol_30d > 0 else 0

                # Market cap from summary_detail
                usd_mcap = usd_market_cap(symbol, summary.get('marketCap', 0))

                symbol_data = {
                    'symbol': symbol,
                    'price': current,
                    'low_52w': low_52w,
                    'high_52w': high_52w,
                    'usd_mcap': usd_mcap / 1e9,
                    'rvol': rvol,
                    'volume': current_vol,
                    'time': datetime.now()
                }

                # Apply screening
                filtered_result = should_pass_screening(symbol_data, criteria)
                if filtered_result:
                    results.append(filtered_result)

            except Exception as e:
                print(f"  Warning: yahooquery error for {symbol}: {str(e)[:50]}")

        return results