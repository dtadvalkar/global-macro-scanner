# YFinance Rate Limiting Solutions Guide

## Problem Analysis

**Current Situation:**
- YFinance version 1.0 (latest stable)
- Rate limit: ~1-2 requests per second
- Your universe: ~5000 stocks
- Naive processing: 40+ minutes + rate limit failures

**Symptoms:**
- `ConnectionError` or `Too Many Requests` errors
- Slow processing (1-2 stocks/second)
- Incomplete data fetching
- Scanner hangs or fails partway through

## Solutions Overview

### 1. **Immediate Fixes (Apply Now)**

#### A. Upgrade to Optimized Provider
Replace the basic YFinance provider with rate-limited version:

```python
# In main.py or wherever providers are imported
from data.providers_optimized import OptimizedYFinanceProvider

# Instead of:
provider = YFinanceProvider()

# Use:
provider = OptimizedYFinanceProvider(requests_per_second=0.5)
```

**Benefits:**
- Automatic rate limiting (0.5 req/sec default)
- Exponential backoff on failures
- Batch processing with delays
- Retry logic for failed requests

#### B. Reduce Data Requirements
```python
# In criteria.py, reduce history requirements for faster fetching
CRITERIA['min_history_days'] = 200  # Instead of 250
CRITERIA['scan_sample_size'] = 2000  # Instead of 5000
```

#### C. Enable Caching
```python
from data.providers_optimized import CachedYFinanceProvider

provider = CachedYFinanceProvider(
    cache_file="yfinance_cache.pkl",
    cache_expiry_hours=24
)
```

**Benefits:**
- Avoids re-fetching same data
- Faster subsequent runs
- Survives rate limit blocks

### 2. **Advanced Solutions**

#### A. Controlled Concurrency
```python
from data.rate_limit_solutions import RateLimitResistantProvider

provider = RateLimitResistantProvider(
    use_cache=True,
    use_concurrency=True
)
```

**Features:**
- Parallel processing with controlled limits
- Adaptive rate limiting (adjusts based on success/failure)
- Progressive data fetching (basic data first, technicals second)

#### B. Alternative Data Sources
```python
# Install yahooquery: pip install yahooquery
from data.providers_optimized import YahooQueryProvider

provider = YahooQueryProvider()  # Alternative API
```

**Benefits:**
- Different rate limits and endpoints
- Backup when yfinance is blocked
- May have different reliability characteristics

### 3. **Configuration Strategies**

#### A. Preset Configurations
```python
# In criteria.py, use conservative settings for rate-limited periods
from config.criteria import PRESETS

criteria = {**CRITERIA, **PRESETS['conservative']}
# - Lower volume requirements
# - More relaxed price proximity
# - Smaller sample size
```

#### B. Progressive Loading
```python
# Only fetch technical indicators when needed
CRITERIA['rsi_enabled'] = False    # Disable for basic screening
CRITERIA['ma_enabled'] = False     # Enable only when researching
CRITERIA['atr_enabled'] = False    # Keep disabled for speed
```

### 4. **Operational Strategies**

#### A. Time-Based Scheduling
```python
# Run scans during off-peak hours (US market closed)
# UTC times: US market closed 4:00-13:30 UTC on weekdays
import schedule

schedule.every().day.at("02:00").do(daily_scan)  # 2 AM UTC
```

#### B. Incremental Processing
```python
# Process markets separately over time
markets_to_process = ['nse', 'tsx', 'idx', 'set']

for market in markets_to_process:
    criteria = CRITERIA.copy()
    criteria['markets'] = [market]
    scan_single_market(criteria)
    time.sleep(3600)  # 1 hour between markets
```

#### C. Error Recovery
```python
# Resume from last successful point
last_processed = load_checkpoint()
remaining_tickers = universe[last_processed:]

for symbol in remaining_tickers:
    try:
        process_symbol(symbol)
        save_checkpoint(symbol)
    except Exception as e:
        print(f"Failed {symbol}: {e}")
        continue
```

### 5. **Alternative Libraries**

#### A. YahooQuery (Recommended Alternative)
```bash
pip install yahooquery
```

```python
from yahooquery import Ticker

# May have different rate limits
tickers = Ticker(['AAPL', 'MSFT'])
data = tickers.history(period='1y')
```

#### B. Other Options
```bash
# Alpha Vantage (requires API key)
pip install alpha_vantage

# Polygon.io (requires API key)
pip install polygon-api-client

# IEX Cloud (requires API key)
pip install iexfinance
```

### 6. **Monitoring and Debugging**

#### A. Rate Limit Monitoring
```python
# Add to your provider
self.request_count = 0
self.error_count = 0
self.start_time = time.time()

def log_stats(self):
    elapsed = time.time() - self.start_time
    rate = self.request_count / elapsed if elapsed > 0 else 0
    print(f"Requests: {self.request_count}, Rate: {rate:.2f}/sec, Errors: {self.error_count}")
```

#### B. Performance Profiling
```python
import cProfile
cProfile.run('daily_scan()', 'profile_stats.prof')

# Analyze with:
# python -m pstats profile_stats.prof
```

### 7. **Emergency Workarounds**

#### A. Local Data Cache
```python
# Pre-download data during off-peak hours
def build_local_cache():
    provider = CachedYFinanceProvider(cache_expiry_hours=168)  # 1 week
    all_tickers = get_universe(MARKETS)
    # This will build cache for all tickers
    provider.get_market_data(all_tickers[:100], CRITERIA)  # Test batch
```

#### B. Reduced Frequency Scanning
```python
# Instead of every 30 minutes, scan every 4 hours
schedule.every(4).hours.do(daily_scan)
```

#### C. Market Segmentation
```python
# Scan different regions at different times
asia_markets = ['nse', 'idx', 'set']  # Scan at 2 AM UTC
americas_markets = ['tsx']           # Scan at 14 PM UTC
```

### 8. **Long-term Solutions**

#### A. Paid Data Providers
Consider upgrading to paid data services for production use:
- **Alpha Vantage**: $50/month for 800k requests
- **Polygon.io**: $200/month for unlimited requests
- **IEX Cloud**: $9/month for 50k requests

#### B. Local Data Infrastructure
```python
# Set up local data collection
# - Schedule regular data pulls during off-hours
# - Store in local database (PostgreSQL/TimescaleDB)
# - Serve from local cache for real-time scanning
```

## Implementation Priority

### Phase 1 (Immediate - Apply Now)
1. ✅ Switch to `OptimizedYFinanceProvider`
2. ✅ Enable caching with `CachedYFinanceProvider`
3. ✅ Reduce `min_history_days` to 200
4. ✅ Add batch processing with 2-second delays

### Phase 2 (Short-term - Next Week)
1. Implement `RateLimitResistantProvider` with concurrency
2. Add yahooquery as fallback provider
3. Create preset configurations for different load levels

### Phase 3 (Medium-term - Next Month)
1. Evaluate paid data providers
2. Implement local data caching infrastructure
3. Add monitoring and alerting for rate limit issues

## Quick Start

To immediately fix rate limiting issues:

1. **Replace provider in core.py:**
```python
# Change from:
from data.providers import YFinanceProvider

# To:
from data.providers_optimized import CachedYFinanceProvider
provider = CachedYFinanceProvider()
```

2. **Adjust criteria for speed:**
```python
CRITERIA['min_history_days'] = 200
CRITERIA['scan_sample_size'] = 2000
```

3. **Run during off-peak hours:**
```bash
# Schedule for 2 AM UTC (US market closed)
python main.py
```

This should reduce processing time from 40+ minutes to ~10-15 minutes while avoiding rate limits.