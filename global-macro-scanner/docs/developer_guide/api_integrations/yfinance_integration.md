# 📈 YFinance API Integration

## Overview

Yahoo Finance provides free historical market data through their public API, serving as a fallback and supplement to IBKR data.

## Core Functionality

### Bulk Data Download
```python
import yfinance as yf

# Single ticker
data = yf.download("RELIANCE.NS", period="2y", interval="1d")

# Multiple tickers (recommended approach)
tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
data = yf.download(
    tickers=" ".join(tickers),  # Space-separated string
    period="2y",
    interval="1d",
    auto_adjust=False,
    progress=False,
    threads=True  # Critical for rate limit avoidance
)
```

### Ticker Information
```python
# Company fundamentals and metadata
ticker = yf.Ticker("RELIANCE.NS")

# Available data attributes
info = ticker.info                    # Company details
history = ticker.history(period="2y") # Historical prices
fast_info = ticker.fast_info          # Quick access data
```

## Data Structures

### Historical OHLCV Data
```python
# DataFrame structure from yf.download()
data = yf.download("RELIANCE.NS", period="1mo")

# Columns: Open, High, Low, Close, Adj Close, Volume
# Index: DatetimeIndex
print(data.head())
"""
                 Open      High       Low     Close  Adj Close    Volume
Date
2024-01-01  2500.00  2520.00  2480.00  2510.00    2510.00  1500000
2024-01-02  2515.00  2530.00  2500.00  2525.00    2525.00  1800000
...
"""
```

### Company Information
```python
ticker = yf.Ticker("RELIANCE.NS")

# Key info fields
company_info = {
    'longName': ticker.info.get('longName'),
    'sector': ticker.info.get('sector'),
    'industry': ticker.info.get('industry'),
    'marketCap': ticker.info.get('marketCap'),
    'trailingPE': ticker.info.get('trailingPE'),
    'dividendYield': ticker.info.get('dividendYield'),
    'fiftyTwoWeekHigh': ticker.info.get('fiftyTwoWeekHigh'),
    'fiftyTwoWeekLow': ticker.info.get('fiftyTwoWeekLow'),
}
```

### Fast Info (Optimized Access)
```python
# Faster access to key metrics
fast = ticker.fast_info

fast_data = {
    'last_price': fast.last_price,
    'open': fast.open,
    'day_high': fast.day_high,
    'day_low': fast.day_low,
    'volume': fast.volume,
    'market_cap': fast.market_cap,
    'currency': fast.currency
}
```

## Rate Limiting & Best Practices

### Rate Limit Awareness
```python
# YFinance rate limits (approximate)
RATE_LIMITS = {
    'requests_per_hour': 2000,    # Conservative estimate
    'requests_per_minute': 100,   # Safe limit
    'burst_limit': 10             # Requests in quick succession
}

# Implement rate limiting
import time

def rate_limited_download(tickers, **kwargs):
    """Download with rate limiting"""
    batch_size = 50  # Process in batches

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        data = yf.download(" ".join(batch), **kwargs)

        # Respect rate limits
        time.sleep(1)  # 1 second between batches

        # Process batch
        process_batch_data(data)
```

### Optimal Bulk Download
```python
# ✅ RECOMMENDED: Single bulk request
def bulk_download_optimized(ticker_list, period="2y"):
    """Optimized bulk download to minimize rate limit hits"""

    # Convert to YFinance format
    yf_tickers = []
    ticker_map = {}

    for ticker in ticker_list:
        # RELIANCE.NSE → RELIANCE.NS
        base = ticker.split('.')[0]
        yf_ticker = f"{base}.NS"
        yf_tickers.append(yf_ticker)
        ticker_map[yf_ticker] = ticker

    # Single bulk request (most efficient)
    try:
        data = yf.download(
            tickers=" ".join(yf_tickers),
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=True,  # Enable threading for speed
            timeout=30     # Prevent hanging
        )

        return data, ticker_map

    except Exception as e:
        logger.error(f"Bulk download failed: {e}")
        return None, ticker_map
```

### Error Handling
```python
def robust_yfinance_download(tickers, retries=3):
    """Download with retry logic"""

    for attempt in range(retries):
        try:
            data = yf.download(
                tickers=" ".join(tickers),
                period="2y",
                threads=True
            )

            if not data.empty:
                return data

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")

            if attempt < retries - 1:
                # Exponential backoff
                time.sleep(2 ** attempt)

    logger.error(f"All {retries} attempts failed for {tickers}")
    return None
```

## Data Processing & Validation

### OHLCV Data Extraction
```python
def process_yfinance_data(raw_data, ticker_map):
    """Extract OHLCV data from YFinance DataFrame"""

    processed_data = []

    for yf_symbol in raw_data.columns.levels[0]:
        if yf_symbol not in raw_data.columns:
            continue

        original_ticker = ticker_map[yf_symbol]
        ticker_data = raw_data[yf_symbol].dropna()

        for date, row in ticker_data.iterrows():
            record = {
                'ticker': original_ticker,
                'date': date.date(),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'adj_close': float(row['Adj Close']),
                'volume': int(row['Volume']),
                'source': 'yf'
            }
            processed_data.append(record)

    return processed_data
```

### Data Quality Validation
```python
def validate_yfinance_data(data):
    """Validate downloaded YFinance data quality"""

    if data is None or data.empty:
        return False, "No data received"

    # Check for reasonable data ranges
    validations = []

    # Price ranges (assuming reasonable stock prices)
    if data['Close'].min() < 0.01 or data['Close'].max() > 100000:
        validations.append("Price range outside reasonable bounds")

    # Volume should be non-negative
    if (data['Volume'] < 0).any():
        validations.append("Negative volume values found")

    # OHLC relationships
    invalid_ohlc = (
        (data['High'] < data['Low']) |
        (data['High'] < data['Open']) |
        (data['High'] < data['Close']) |
        (data['Low'] > data['Open']) |
        (data['Low'] > data['Close'])
    ).any()

    if invalid_ohlc:
        validations.append("Invalid OHLC relationships")

    return len(validations) == 0, validations
```

## Integration Patterns

### Provider Class Implementation
```python
class YFinanceProvider(BaseMarketDataProvider):
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=50)

    async def get_market_data(self, tickers, criteria=None):
        """Fetch historical market data"""
        await self.rate_limiter.wait_if_needed()

        # Convert tickers to YFinance format
        yf_tickers = [self._convert_to_yf_format(t) for t in tickers]

        # Bulk download
        data = yf.download(
            tickers=" ".join(yf_tickers),
            period=criteria.get('period', '2y'),
            interval=criteria.get('interval', '1d'),
            threads=True
        )

        # Process and return
        return self._process_downloaded_data(data, tickers)

    def _convert_to_yf_format(self, ticker):
        """Convert NSE ticker to YFinance format"""
        base = ticker.split('.')[0]
        return f"{base}.NS"

    def _process_downloaded_data(self, raw_data, original_tickers):
        """Process raw YFinance data into standardized format"""
        results = {}

        for i, ticker in enumerate(original_tickers):
            yf_symbol = self._convert_to_yf_format(ticker)

            if yf_symbol in raw_data.columns.levels[0]:
                ticker_data = raw_data[yf_symbol]

                # Convert to our standard format
                processed = self._convert_to_standard_format(ticker_data)
                results[ticker] = processed
            else:
                results[ticker] = {'error': 'Symbol not found in YFinance data'}

        return results
```

### Fallback Integration
```python
async def get_market_data_with_fallback(tickers, primary_provider='ibkr'):
    """Get market data with YFinance fallback"""

    if primary_provider == 'ibkr':
        try:
            ibkr_provider = IBKRProvider()
            data = await ibkr_provider.get_market_data(tickers)
            return data
        except Exception as e:
            logger.warning(f"IBKR failed, falling back to YFinance: {e}")

    # YFinance fallback
    yf_provider = YFinanceProvider()
    return await yf_provider.get_market_data(tickers)
```

## Testing & Validation

### Unit Testing
```python
import pytest
from unittest.mock import patch

class TestYFinanceProvider:
    def test_ticker_conversion(self):
        provider = YFinanceProvider()
        assert provider._convert_to_yf_format("RELIANCE.NSE") == "RELIANCE.NS"

    @patch('yfinance.download')
    async def test_bulk_download(self, mock_download):
        # Mock successful download
        mock_data = pd.DataFrame({
            'Open': [2500, 2510],
            'High': [2520, 2530],
            'Low': [2480, 2490],
            'Close': [2510, 2520],
            'Adj Close': [2510, 2520],
            'Volume': [1000000, 1200000]
        })

        mock_download.return_value = mock_data

        provider = YFinanceProvider()
        result = await provider.get_market_data(["RELIANCE.NSE"])

        assert "RELIANCE.NSE" in result
        assert result["RELIANCE.NSE"]["close"] == 2520
```

### Integration Testing
```python
async def test_yfinance_end_to_end():
    """Full integration test"""
    provider = YFinanceProvider()

    # Test with real data (limited scope for CI)
    test_tickers = ["RELIANCE.NS"]  # Use .NS format for YFinance

    data = await provider.get_market_data(test_tickers)

    # Validate response structure
    assert len(data) == 1
    assert "RELIANCE.NS" in data

    ticker_data = data["RELIANCE.NS"]
    assert "close" in ticker_data
    assert "volume" in ticker_data

    # Validate data quality
    assert ticker_data["close"] > 0
    assert ticker_data["volume"] >= 0
```

## Performance Monitoring

### Download Metrics
```python
class YFinanceMetrics:
    def __init__(self):
        self.requests_total = 0
        self.requests_successful = 0
        self.requests_failed = 0
        self.data_points_downloaded = 0
        self.average_response_time = 0

    def record_request(self, success, response_time, data_points):
        self.requests_total += 1

        if success:
            self.requests_successful += 1
        else:
            self.requests_failed += 1

        self.data_points_downloaded += data_points

        # Update rolling average
        self.average_response_time = (
            (self.average_response_time * (self.requests_total - 1)) + response_time
        ) / self.requests_total
```

### Health Monitoring
```python
async def yfinance_health_check():
    """Monitor YFinance service availability"""

    metrics = {
        'service_available': False,
        'response_time_ms': 0,
        'data_quality': False,
        'last_check': None
    }

    start_time = time.time()

    try:
        # Test with a reliable ticker
        data = yf.download(
            "AAPL",
            period="5d",
            interval="1d",
            progress=False
        )

        metrics['service_available'] = not data.empty
        metrics['data_quality'] = validate_yfinance_data(data)[0]

    except Exception as e:
        logger.error(f"YFinance health check failed: {e}")

    metrics['response_time_ms'] = (time.time() - start_time) * 1000
    metrics['last_check'] = datetime.now()

    return metrics
```

## Related Documentation

- **[API Overview](./)** - General API integration patterns
- **[IBKR Integration](./ibkr_integration.md)** - Primary data source
- **[Rate Limiting Guide](../../technical_reference/rate_limiting_guide.md)** - Managing API limits
- **[Performance Optimization](../../technical_reference/performance_optimization.md)** - YFinance optimization

---

**Status**: ✅ Complete | **Last Updated**: January 2025