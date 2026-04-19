import yfinance as yf
from ib_async import *
import asyncio
import pandas as pd
from data.currency import usd_market_cap
from datetime import datetime
from screening.screening_utils import should_pass_screening, calculate_rsi, calculate_sma, calculate_atr
from data.cache_manager import FundamentalCacheManager
from db import get_db

util.patchAsyncio()

class BaseProvider:
    def get_market_data(self, tickers, criteria):
        raise NotImplementedError

class OptimizedYFinanceProvider(BaseProvider):
    """
    Optimized YFinance provider with advanced performance features:
    - Intelligent caching with TTL
    - Parallel processing with concurrency control
    - Early filtering to reduce API calls
    - Adaptive rate limiting
    - Batch processing with error recovery
    """

    def __init__(self, requests_per_second: float = 0.8, max_concurrent: int = 5):
        self.requests_per_second = requests_per_second
        self.max_concurrent = max_concurrent
        self.last_request_time = 0
        self.fundamentals_cache = FundamentalCacheManager(use_database=True)
        self.db = get_db()
        self.failed_stocks_cache = {}  # Cache of stocks that consistently fail

    def _rate_limit_wait(self):
        """Simple rate limiting"""
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.requests_per_second

        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)

        self.last_request_time = time.time()


    async def _process_symbol_async(self, symbol, criteria, semaphore):
        """Process a single symbol with technical analysis"""
        async with semaphore:
            try:
                self._rate_limit_wait()

                stock = yf.Ticker(symbol)
                hist = stock.history(period='1y')

                # Check for invalid/empty data (delisted stocks, etc.)
                if hist.empty or len(hist) <= criteria.get('min_history_days', 250):
                    # Mark as failed stock to avoid repeated processing
                    self.failed_stocks_cache[symbol] = self.failed_stocks_cache.get(symbol, 0) + 1
                    return None

                info = stock.info

                # Basic data extraction
                low_52w = hist['Low'].min()
                current = hist['Close'].iloc[-1]
                high_52w = hist['High'].max()

                # Volume analysis
                current_vol = hist['Volume'].iloc[-1]
                avg_vol_30d = hist['Volume'].tail(30).mean() if len(hist) >= 30 else hist['Volume'].mean()
                rvol = current_vol / avg_vol_30d if avg_vol_30d > 0 else 0

                # Market cap conversion
                usd_mcap = usd_market_cap(symbol, info.get('marketCap', 0))

                # Prepare data for screening
                symbol_data = {
                    'symbol': symbol,
                    'price': current,
                    'low_52w': low_52w,
                    'high_52w': high_52w,
                    'usd_mcap': usd_mcap / 1e9,  # Convert to billions
                    'rvol': rvol,
                    'volume': current_vol,
                    'price_history': hist['Close'] if criteria.get('pattern_enabled', False) else None,
                    'avg_volume_20d': hist['Volume'].tail(20).mean() if len(hist) >= 20 else current_vol,
                    'time': datetime.now()
                }

                # Calculate technical indicators if enabled
                if criteria.get('rsi_enabled', False):
                    symbol_data['rsi'] = calculate_rsi(hist['Close'])

                if criteria.get('ma_enabled', False):
                    symbol_data['sma50'] = calculate_sma(hist['Close'], 50)
                    symbol_data['sma200'] = calculate_sma(hist['Close'], 200)
                    if symbol_data['sma50'] and symbol_data['sma200']:
                        symbol_data['price_vs_sma50_pct'] = current / symbol_data['sma50']
                        symbol_data['sma50_vs_sma200_pct'] = symbol_data['sma50'] / symbol_data['sma200']

                if criteria.get('atr_enabled', False):
                    symbol_data['atr_pct'] = calculate_atr(hist['High'], hist['Low'], hist['Close'])

                # Apply screening
                if should_pass_screening(symbol_data, criteria):
                    result = {
                        'symbol': symbol,
                        'price': current,
                        'low_52w': low_52w,
                        'usd_mcap': usd_mcap / 1e9,
                        'pct_from_low': current / low_52w,
                        'rvol': rvol,
                        'volume': current_vol,
                        'time': datetime.now()
                    }

                    # Add technical data if available
                    for key in ['rsi', 'sma50', 'sma200', 'atr_pct']:
                        if key in symbol_data:
                            result[key] = symbol_data[key]

                    return result

            except Exception as e:
                error_str = str(e).lower()
                # Track failed stocks to avoid repeated processing
                # Mark as persistent failure in DB if critical error
                if any(keyword in error_str for keyword in ['delisted', 'not found', '404', 'no data found']):
                    # Update DB to mark as inactive in BOTH tables (Fundamentals and Tickers)
                    self.fundamentals_cache.set_fundamentals(symbol, {'is_active': False}, 'error_handler')
                    self.db.update_ticker_status(symbol, 'INACTIVE', f"YFinance Error: {str(e)[:50]}")
                    self.failed_stocks_cache[symbol] = self.failed_stocks_cache.get(symbol, 0) + 1
                    pass
                else:
                    # For other errors, track but still show warning
                    self.failed_stocks_cache[symbol] = self.failed_stocks_cache.get(symbol, 0) + 1
                    print(f"  Warning: {symbol} error (YFinance): {str(e)[:50]}")

            return None

    def get_market_data(self, tickers, criteria):
        """Optimized processing with fundamental caching and early filtering"""
        import asyncio
        import time

        print(f"Optimized YFinance: Processing {len(tickers)} stocks with fundamental caching")

        # Phase 1: Early filtering using cached fundamentals and failed stocks
        viable_tickers = []
        skipped_by_fundamentals = 0
        skipped_by_failure_cache = 0

        for ticker in tickers:
            # First check if stock is known to fail (delisted, etc.)
            if ticker in self.failed_stocks_cache:
                fail_count = self.failed_stocks_cache[ticker]
                if fail_count >= 3:  # Skip after 3 failures
                    skipped_by_failure_cache += 1
                    continue

            # Then check fundamentals
            # can_skip, reason = self.fundamentals_cache.can_skip_by_fundamentals(ticker, criteria)
            # if can_skip:
            #     print(f"Skipped {ticker}: {reason}")
            #     skipped_by_fundamentals += 1
            # else:
            #     viable_tickers.append(ticker)
            viable_tickers.append(ticker)

        efficiency_msg = f" ({len(viable_tickers)}/{len(tickers)} viable, {skipped_by_fundamentals} fundamentals, {skipped_by_failure_cache} failed cache)"
        print(f"Pre-filtering complete{efficiency_msg}")

        if not viable_tickers:
            return []

        # Phase 2: Process viable tickers with parallel execution
        async def process_viable():
            semaphore = asyncio.Semaphore(self.max_concurrent)
            tasks = [self._process_symbol_async(symbol, criteria, semaphore) for symbol in viable_tickers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out None results and exceptions
            valid_results = []
            for result in results:
                if isinstance(result, Exception):
                    continue
                if result is not None:
                    valid_results.append(result)

            return valid_results

        try:
            results = asyncio.run(process_viable())

            # Phase 3: Update fundamentals cache with fresh data
            self._update_fundamentals_cache(results)

            print(f"Processed {len(results)} stocks, fundamentals cache updated")
            return results

        except Exception as e:
            print(f"❌ Optimized YFinance error: {e}")
            return []

    def _update_fundamentals_cache(self, results):
        """Update fundamentals cache with data from successful scans"""
        for result in results:
            if 'symbol' in result and 'usd_mcap' in result:
                ticker = result['symbol']
                fundamentals = {
                    'symbol': ticker.split('.')[0],
                    'exchange': self._ticker_to_exchange(ticker),
                    'market_cap_usd': int(result['usd_mcap'] * 1e6),  # Convert billions to full USD
                    'sector': result.get('sector'),
                    'industry': result.get('industry'),
                    'currency': 'USD',  # Assuming conversion already done
                    'country': self._exchange_to_country(self._ticker_to_exchange(ticker))
                }
                self.fundamentals_cache.set_fundamentals(ticker, fundamentals, 'yfinance')

    def _ticker_to_exchange(self, ticker):
        """Map ticker suffix to exchange code"""
        if ticker.endswith('.NS'):
            return 'NSE'
        elif ticker.endswith('.TO'):
            return 'TSE'
        elif ticker.endswith('.JK'):
            return 'IDX'
        elif ticker.endswith('.BK'):
            return 'SET'
        else:
            return 'SMART'  # US stocks

    def _exchange_to_country(self, exchange):
        """Map exchange to country"""
        mapping = {
            'NSE': 'India',
            'TSE': 'Canada',
            'IDX': 'Indonesia',
            'SET': 'Thailand',
            'SMART': 'United States'
        }
        return mapping.get(exchange, 'Unknown')

class YFinanceProvider(BaseProvider):
    """
    Basic YFinance provider with minimal rate limiting.

    For production use with large universes, consider OptimizedYFinanceProvider
    which includes advanced caching, parallel processing, and performance optimizations.
    """

    def __init__(self, requests_per_second: float = 0.5):
        self.requests_per_second = requests_per_second
        self.last_request_time = 0

    def _rate_limit_wait(self):
        """Simple rate limiting"""
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.requests_per_second

        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)

        self.last_request_time = time.time()

    def get_market_data(self, tickers, criteria):
        results = []
        batch_size = 20  # Process in small batches to avoid rate limits

        print(f"YFinance: Processing {len(tickers)} stocks in batches of {batch_size}")

        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            print(f"  Processing batch {i//batch_size + 1}: {len(batch)} stocks")

            for symbol in batch:
                try:
                    self._rate_limit_wait()

                    stock = yf.Ticker(symbol)
                    hist = stock.history(period='1y')

                    if not hist.empty and len(hist) > criteria.get('min_history_days', 0):
                        info = stock.info

                        # Basic data extraction
                        current = hist['Close'].iloc[-1]
                        low_52w = hist['Low'].min()
                        high_52w = hist['High'].max()
                        current_vol = hist['Volume'].iloc[-1]
                        avg_vol_30d = hist['Volume'].tail(30).mean()
                        rvol = current_vol / avg_vol_30d if avg_vol_30d > 0 else 0

                        usd_mcap = usd_market_cap(symbol, info.get('marketCap', 0))

                        # Prepare data for centralized screening
                        symbol_data = {
                            'symbol': symbol,
                            'price': current,
                            'low_52w': low_52w,
                            'high_52w': high_52w,
                            'usd_mcap': usd_mcap / 1e9,  # Convert to billions for display
                            'rvol': rvol,
                            'volume': current_vol,
                            'time': datetime.now()
                        }

                        # Calculate additional technical indicators if enabled
                        if criteria.get('rsi_enabled', False):
                            symbol_data['rsi'] = calculate_rsi(hist['Close'])

                        if criteria.get('ma_enabled', False):
                            sma50 = calculate_sma(hist['Close'], 50)
                            sma200 = calculate_sma(hist['Close'], 200)
                            symbol_data['price_vs_sma50_pct'] = current / sma50 if sma50 > 0 else 1.0
                            symbol_data['sma50_vs_sma200_pct'] = sma50 / sma200 if sma200 > 0 else 1.0

                        if criteria.get('atr_enabled', False):
                            symbol_data['atr_pct'] = calculate_atr(hist['High'], hist['Low'], hist['Close'])

                        # Apply centralized screening logic
                        filtered_result = should_pass_screening(symbol_data, criteria)
                        if filtered_result:
                            results.append(filtered_result)

                except Exception as e:
                    print(f"  Warning: {symbol} error (yfinance): {str(e)[:30]}")

            # Brief pause between batches
            if i + batch_size < len(tickers):
                import time
                time.sleep(2.0)  # 2 second pause between batches

        print(f"YFinance: Completed processing, found {len(results)} qualifying stocks")
        return results

class IBKRProvider(BaseProvider):
    """
    IBKR Data Provider - Uses Delayed Data (Type 3) for ALL Markets

    Data Type Strategy:
    - Type 3 (Delayed): Primary data type for ALL markets (15-20 min delay)
    - Provides access to global delayed market data without rate limiting
    - Free/low-cost access to international markets
    - As confirmed by IBKR support: "no trouble accessing delayed data from any market"

    Markets Supported via IBKR Type 3:
    - US (SMART)
    - Canada (TSE)
    - India (NSE)
    - Europe (LSE, XETRA, etc.)
    - Australia (ASX)
    - Hong Kong (SEHK)
    - Singapore (SGX)
    - [Other markets as enabled by IBKR account permissions]

    Markets NOT supported (routed to YFinance):
    - Thailand (SET)
    - Indonesia (IDX)
    """

    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()
        self.fundamentals_cache = FundamentalCacheManager(use_database=True)
        self.db = get_db()

    def _get_exchange_from_symbol(self, symbol):
        """Extract exchange from symbol suffix"""
        if symbol.endswith('.NS'):
            return 'NSE'
        elif symbol.endswith('.TO'):
            return 'TSE'
        elif symbol.endswith('.AX'):
            return 'ASX'
        elif symbol.endswith('.SI'):
            return 'SGX'
        elif symbol.endswith('.DE'):
            return 'IBIS'
        elif symbol.endswith('.PA'):
            return 'SBF'
        else:
            return 'SMART'  # US stocks

    def _fetch_fundamentals_from_sources(self, symbol, exchange, currency):
        """Fetch fundamentals from multiple data sources with rate limiting"""

        # Source 1: YFinance (most comprehensive, but rate limited)
        try:
            import yfinance as yf
            import time

            # Add small delay to respect rate limits
            time.sleep(0.1)

            ticker_obj = yf.Ticker(symbol)
            info = ticker_obj.info

            # Check if we got valid data (not empty dict)
            if info and isinstance(info, dict) and len(info) > 0 and 'marketCap' in info:
                return {
                    'symbol': symbol.split('.')[0],
                    'exchange': self._get_exchange_from_symbol(symbol),
                    'market_cap_usd': info.get('marketCap', 0),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', ''),
                    'currency': currency,
                    'country': info.get('country', ''),
                    'data_source': 'yfinance'
                }
        except Exception as e:
            # YFinance failed (rate limit, network, etc.)
            # This is expected and not an error we need to report
            pass

        # Source 2: IBKR Fundamentals (future enhancement)
        # IBKR provides some fundamental data, but YFinance is more comprehensive
        # Could be added here for IBKR-specific data

        # Source 3: Future data sources (Alpha Vantage, Financial Modeling Prep, etc.)
        # Can be added here as additional fallbacks

        return None

    async def connect(self):
        try:
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
            # IBKR Data Types:
            # Type 1 = Real-time data (requires subscription, expensive)
            # Type 2 = Frozen real-time (not used)
            # Type 3 = Delayed data (15-20 min delay, free/low cost, PRIMARY TYPE for all markets)
            # Type 4 = Delayed frozen (not used)
            #
            # We use Type 3 (Delayed) as PRIMARY data type for ALL markets to ensure NSE access
            # This provides access to global delayed data
            self.ib.reqMarketDataType(3)
            print(f"Connected to IBKR on {self.host}:{self.port} (Delayed Data Mode - Type 3)")
            return True
        except Exception:
            return False

    async def get_market_data_async(self, tickers, criteria):
        """Screen using stored market data from current_market_data table (fresh from today's collection)"""
        try:
            print(f"IBKR Stored Data Scan: {len(tickers)} stocks...")
            results = []

            # Phase 1: Pre-Filtering (Optimization)
            # Filter out stocks that are known to be inactive or small cap based on DB cache
            print(f"  Pre-filtering {len(tickers)} stocks using fundamentals cache...")
            viable_tickers = []
            skipped_count = 0

            for ticker in tickers:
                # can_skip, reason = self.fundamentals_cache.can_skip_by_fundamentals(ticker, criteria)
                # if can_skip:
                #     skipped_count += 1
                #     print(f"    Skipped {ticker}: {reason}")
                # else:
                #     viable_tickers.append(ticker)
                viable_tickers.append(ticker)

            if skipped_count > 0:
                print(f"  Skipped {skipped_count} stocks (cached fundamentals). Processing {len(viable_tickers)} stocks...")
            else:
                print(f"  No stocks skipped. Processing {len(viable_tickers)} stocks...")

            if not viable_tickers:
                return []

            # Phase 2: Query stored market data and apply criteria
            results = await self._screen_stored_market_data(viable_tickers, criteria)

            return results

        except Exception as e:
            print(f"Error in stored data screening: {e}")
            return []

    async def _screen_stored_market_data(self, tickers, criteria):
        """Apply screening criteria to stored market data from current_market_data table"""
        results = []

        # Query current_market_data for these tickers
        ticker_list = ','.join(f"'{t}'" for t in tickers)
        query = f"""
            SELECT
                ticker,
                last_price,
                close_price,
                open_price,
                high_price,
                low_price,
                volume,
                last_updated
            FROM current_market_data
            WHERE ticker IN ({ticker_list})
            ORDER BY ticker
        """

        try:
            from screening.screening_utils import should_pass_screening
            market_data_rows = self.db.query(query)

            for row in market_data_rows:
                ticker, last_price, close_price, open_price, high_price, low_price, volume, last_updated = row

                # Skip if no price data
                if not last_price:
                    continue

                # Get fundamentals for additional criteria
                fundamentals = self.fundamentals_cache.get_fundamentals(ticker) or {}

                # Build symbol_data for centralized screening
                symbol_data = {
                    'symbol': ticker,
                    'price': float(last_price),
                    'low_52w': fundamentals.get('xml_52w_low'),
                    'high_52w': fundamentals.get('xml_52w_high'),
                    'volume': int(volume) if volume else 0,
                    'rvol': 1.0, # Approximate for stored data
                    'usd_mcap': (fundamentals.get('market_cap_usd', 0) or 0) / 1e9,
                    'time': last_updated
                }

                # Apply centralized screening logic
                filtered_result = should_pass_screening(symbol_data, criteria)
                
                if filtered_result:
                    results.append({
                        'ticker': ticker,
                        'price': filtered_result['price'],
                        'volume': filtered_result['volume'],
                        'reason': self._get_screening_reason(filtered_result, criteria)
                    })

        except Exception as e:
            print(f"Error querying stored market data: {e}")

        return results


    def _get_screening_reason(self, market_data, criteria):
        """Generate reason for why stock passed screening"""
        reasons = []
        price = market_data.get('price', 0)
        low_52w = market_data.get('low_52w')
        volume = market_data.get('volume', 0)

        if low_52w and low_52w > 0:
            pct_above_low = ((price - low_52w) / low_52w) * 100
            reasons.append(f"{pct_above_low:.1f}% from 52w low")
        else:
            reasons.append("No 52w low baseline (Volume Catch)")

        if volume > 0:
            reasons.append(f"Vol: {volume:,}")

        return "; ".join(reasons)

    def disconnect_sync(self):
        """Synchronous disconnect for compatibility"""
        if self.ib.isConnected():
            self.ib.disconnect()

    async def process_stock(self, symbol, criteria):
        try:
            # 1. Map symbol to IBKR contract (Move this higher to fix scoping bug)
            exchange = 'SMART'
            currency = 'USD'
            pure_symbol = symbol
            
            if symbol.endswith('.TO'):
                exchange = 'TSE'  # Toronto Stock Exchange (not TSX brand name)
                currency = 'CAD'
                pure_symbol = symbol[:-3]
            elif symbol.endswith('.NS'):
                exchange = 'NSE'
                currency = 'INR'
                pure_symbol = symbol[:-3]
            elif symbol.endswith('.AX'):
                exchange = 'ASX'
                currency = 'AUD'
                pure_symbol = symbol[:-3]
            elif symbol.endswith('.SI'):
                exchange = 'SGX'
                currency = 'SGD'
                pure_symbol = symbol[:-3]
            elif symbol.endswith('.DE'):
                exchange = 'IBIS'
                currency = 'EUR'
                pure_symbol = symbol[:-3]
            elif symbol.endswith('.PA'):
                exchange = 'SBF'
                currency = 'EUR'
                pure_symbol = symbol[:-3]
            elif symbol.endswith('.JK'):
                # Indonesia IDX not supported by IBKR - skip to YFinance fallback
                self.fundamentals_cache.set_fundamentals(symbol, {'is_active': False, 'exchange': 'IDX'}, 'ibkr_validation')
                return None
            elif symbol.endswith('.BK'):
                # Thailand SET not supported by IBKR - skip to YFinance fallback
                self.fundamentals_cache.set_fundamentals(symbol, {'is_active': False, 'exchange': 'SET'}, 'ibkr_validation')
                return None

            # 2. Get fundamentals from cache (populated during universe refresh)
            fundamentals = self.fundamentals_cache.get_fundamentals(symbol)
            
            # 🧪 Modular Fallback: If fundamentals missing, try YFinance (Optionally)
            from config import ENABLE_FALLBACKS
            if not fundamentals and ENABLE_FALLBACKS:
                try:
                    # Non-blocking fetch for metadata
                    fundamentals_data = self._fetch_fundamentals_from_sources(symbol, exchange, currency)
                    if fundamentals_data:
                        self.fundamentals_cache.set_fundamentals(symbol, fundamentals_data)
                        fundamentals = fundamentals_data
                except Exception:
                    pass

            contract = Stock(pure_symbol, exchange, currency)
            qualified = await self.ib.qualifyContractsAsync(contract)
            
            # Handle [None] case which IBKR returns for invalid contracts
            # qualified is list of contracts. If empty or contains None, it failed.
            is_valid = qualified and qualified[0]

            if not is_valid: 
                # Contract invalid/delisted - mark as inactive in DB (Tickers and Fundamentals)
                self.db.update_ticker_status(symbol, 'INACTIVE', 'Error 200: Contract not found (IBKR)')
                self.fundamentals_cache.set_fundamentals(symbol, {'is_active': False}, 'ibkr_validation')
                return None

            # Attempt to fetch TRADES if possible for volume, otherwise MIDPOINT
            # For delayed data (Type 3), limit to 16 minutes ago to avoid permission issues
            from datetime import datetime, timedelta
            end_time = datetime.utcnow() - timedelta(minutes=16)
            end_datetime_str = end_time.strftime('%Y%m%d %H:%M:%S')

            try:
                bars = await self.ib.reqHistoricalDataAsync(
                    contract, endDateTime=end_datetime_str, durationStr='1 Y',
                    barSizeSetting='1 day', whatToShow='TRADES', useRTH=True
                )
            except Exception:
                bars = await self.ib.reqHistoricalDataAsync(
                    contract, endDateTime=end_datetime_str, durationStr='1 Y',
                    barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
                )
            
            if not bars:
                self.db.update_ticker_status(symbol, 'INACTIVE', 'IBKR: No Historical Data (Bars empty)')
                return None

            # Extract basic price data
            low_52w = min(b.low for b in bars)
            high_52w = max(b.high for b in bars)  # Add high for 52w high check
            current = bars[-1].close

            # RVOL Calculation
            # If TRADES worked, bars[i].volume is available. If MIDPOINT, it's 0/-1.
            current_vol = bars[-1].volume
            if current_vol > 0:
                avg_vol_30d = sum(b.volume for b in bars[-30:]) / 30
                rvol = current_vol / avg_vol_30d if avg_vol_30d > 0 else 0
            else:
                # 🧪 Modular Fallback: Try YFinance for RVOL if IBKR volume is missing
                from config import ENABLE_FALLBACKS
                if ENABLE_FALLBACKS:
                    try:
                        import yfinance as yf
                        yf_hist = yf.Ticker(symbol).history(period='1mo')
                        current_vol = yf_hist['Volume'].iloc[-1]
                        avg_vol_30d = yf_hist['Volume'].mean()
                        rvol = current_vol / avg_vol_30d if avg_vol_30d > 0 else 0
                        volume = current_vol # Use YFinance volume for the report
                    except Exception:
                        rvol = 0
                else:
                    rvol = 0

            # Prepare data for centralized screening
            symbol_data = {
                'symbol': symbol,
                'price': current,
                'low_52w': low_52w,
                'high_52w': high_52w,
                'rvol': rvol,
                'volume': current_vol,
                'time': datetime.now()
            }

            # Use cached fundamentals for market cap (populated during universe refresh)
            usd_mcap = fundamentals.get('market_cap_usd', 0) if fundamentals else 0
            symbol_data['usd_mcap'] = usd_mcap / 1e9  # billions

            # Calculate technicals strictly from IBKR bars
            if len(bars) >= 50:
                closes = pd.Series([b.close for b in bars])
                highs = pd.Series([b.high for b in bars])
                lows = pd.Series([b.low for b in bars])
                
                if criteria.get('rsi_enabled', False):
                    symbol_data['rsi'] = calculate_rsi(closes)
                
                if criteria.get('ma_enabled', False):
                    sma50 = calculate_sma(closes, 50)
                    sma200 = calculate_sma(closes, 200)
                    symbol_data['price_vs_sma50_pct'] = current / sma50 if sma50 > 0 else 1.0
                    symbol_data['sma50_vs_sma200_pct'] = sma50 / sma200 if sma200 > 0 else 1.0
                    symbol_data['sma50'] = sma50
                    symbol_data['sma200'] = sma200

                if criteria.get('atr_enabled', False):
                    symbol_data['atr_pct'] = calculate_atr(highs, lows, closes)

            # Apply centralized screening logic
            filtered_result = should_pass_screening(symbol_data, criteria)
            return filtered_result

        except Exception as e:
            # Catch-all for other errors (Timeout, Network)
            print(f"❌ {symbol} IBKR Error: {e}")
            pass
        return None

    def get_market_data(self, tickers, criteria):
        # Synchronous wrapper for asyncio
        try:
            return asyncio.run(self.get_market_data_async(tickers, criteria))
        except Exception as e:
            print(f"  IBKR Async Error: {e}")
            return []

class IBKRScannerProvider(BaseProvider):
    def __init__(self, host='127.0.0.1', port=7496, client_id=1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()

    def get_scanner_results(self, instrument, location, scan_code):
        """Option B: Direct Server-Side Scan using delayed data (Type 3)"""
        try:
            if not self.ib.isConnected():
                self.ib.connect(self.host, self.port, clientId=self.client_id)
                # Ensure we're using delayed data (Type 3) for scanner operations
                self.ib.reqMarketDataType(3)

            subscription = ScannerSubscription(
                instrument=instrument,
                locationCode=location,
                scanCode=scan_code
            )
            
            print(f"🔎 IBKR Server Scan: {location} ({scan_code})...")
            scan_data = self.ib.reqScannerData(subscription)
            
            results = []
            for item in scan_data:
                # We need historical data for the actual 52w low calculation
                # because the scanner just gives us the rank.
                results.append(item.contractDetails.contract.symbol + 
                              ('.TO' if 'CANADA' in location else ''))
            
            return results
        except Exception as e:
            print(f"  ⚠️ Scanner error: {e}")
            return []
        finally:
            self.ib.disconnect()
