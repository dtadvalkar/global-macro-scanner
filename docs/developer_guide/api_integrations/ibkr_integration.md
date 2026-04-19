# 🔗 IBKR API Integration

## Overview

Interactive Brokers (IBKR) provides institutional-grade market data through their Trader Workstation (TWS) API.

## Connection Architecture

### TWS Gateway Setup
```python
# Connection parameters
IBKR_CONFIG = {
    'host': '127.0.0.1',          # Local TWS instance
    'port': 7496,                 # Live account port
    'client_id': random.randint(1, 999),  # Unique client ID
    'timeout': 30                 # Connection timeout
}

# Establish connection
ib = IB()
await ib.connectAsync(
    host=IBKR_CONFIG['host'],
    port=IBKR_CONFIG['port'],
    clientId=IBKR_CONFIG['client_id']
)
```

### Market Data Types

#### Type 3: Delayed Data (Primary)
```python
# Enable delayed market data (free, 15-20 min delay)
ib.reqMarketDataType(3)

# Request snapshot
contract = Stock('RELIANCE', 'NSE', 'INR')
ticker = ib.reqMktData(contract, "", snapshot=True)

# Wait for data arrival
await asyncio.sleep(2)
market_data = util.tree(ticker)
```

#### Type 1: Live Data (Premium)
```python
# Live data requires subscription
ib.reqMarketDataType(1)
# Only use if client has live data permissions
```

## Data Structures

### Contract Definition
```python
# NSE Stock contract
contract = Stock(
    symbol='RELIANCE',           # Base symbol
    exchange='NSE',              # Exchange
    currency='INR'               # Currency
)

# Qualified contract (after resolution)
qualified = await ib.qualifyContractsAsync(contract)
contract_id = qualified[0].conId
```

### Market Data Snapshot
```python
# Request market data
ticker = ib.reqMktData(contract, "", snapshot=True)

# Available fields after data arrives
market_snapshot = {
    'last': ticker.last,          # Last traded price
    'close': ticker.close,        # Previous close
    'open': ticker.open,          # Today's open
    'high': ticker.high,          # Today's high
    'low': ticker.low,            # Today's low
    'volume': ticker.volume,      # Trading volume
    'bid': ticker.bid,            # Best bid
    'ask': ticker.ask,            # Best ask
    'bidSize': ticker.bidSize,    # Bid size
    'askSize': ticker.askSize,    # Ask size
}
```

### Fundamentals Data

#### ReportSnapshot (Company Overview)
```python
# Request fundamental data
xml_snapshot = await ib.reqFundamentalDataAsync(
    contract=contract,
    reportType='ReportSnapshot'
)

# Contains: company info, market cap, P/E, industry, etc.
# ~50KB XML per company
```

#### ReportRatios (Financial Ratios)
```python
# Request financial ratios
xml_ratios = await ib.reqFundamentalDataAsync(
    contract=contract,
    reportType='ReportRatios'
)

# Contains: valuation ratios, profitability, margins, etc.
# ~25KB XML per company
```

## Error Handling

### Common Error Codes
```python
ERROR_CODES = {
    200: "No security definition found",
    354: "Requested market data is not subscribed",
    502: "Couldn't connect to TWS",
    504: "Not connected to TWS",
    1100: "Connectivity between IB and TWS has been lost",
    1102: "Connectivity between TWS and IB has been restored"
}

async def handle_ibkr_error(error_code, error_msg):
    if error_code == 200:
        # Mark ticker as inactive
        await mark_ticker_inactive(ticker, error_msg)
    elif error_code == 354:
        # Fallback to YFinance
        await use_yfinance_fallback(ticker)
    elif error_code in [502, 504, 1100]:
        # Connection issues - retry
        await retry_connection()
```

### Connection Recovery
```python
async def robust_ibkr_connection():
    """Handle connection issues gracefully"""
    try:
        await ib.connectAsync(host, port, clientId)
        return True
    except Exception as e:
        logger.error(f"IBKR connection failed: {e}")

        # Try alternative ports
        for alt_port in [7497, 4001, 4002]:  # Paper, gateway ports
            try:
                await ib.connectAsync(host, alt_port, clientId)
                logger.info(f"Connected on alternative port {alt_port}")
                return True
            except:
                continue

        return False
```

## Rate Limiting & Throttling

### Request Limits
- **Market Data**: No explicit limits for delayed data
- **Fundamentals**: ~100-200 requests/minute
- **Connection**: Max 8 concurrent connections per TWS instance

### Throttling Strategy
```python
# Semaphore for concurrent requests
MAX_CONCURRENT = 3  # Conservative limit
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def throttled_request(ticker):
    async with semaphore:
        return await fetch_ibkr_data(ticker)

# Process in controlled batches
BATCH_SIZE = 50
for i in range(0, len(tickers), BATCH_SIZE):
    batch = tickers[i:i + BATCH_SIZE]
    tasks = [throttled_request(t) for t in batch]
    results = await asyncio.gather(*tasks)
    await save_batch_results(results)
```

## Data Quality Validation

### Market Data Validation
```python
def validate_market_data(mkt_data):
    """Validate IBKR market data quality"""
    validations = [
        ('last_price', mkt_data.get('last'), lambda x: x > 0),
        ('volume', mkt_data.get('volume'), lambda x: x >= 0),
        ('price_range', (mkt_data.get('high'), mkt_data.get('low')),
         lambda x: x[0] >= x[1] if x[0] and x[1] else True)
    ]

    for field, value, validator in validations:
        if not validator(value):
            logger.warning(f"Invalid {field}: {value}")

    return all(validator(value) for _, value, validator in validations)
```

### Fundamentals Validation
```python
def validate_fundamentals(xml_content):
    """Validate XML fundamentals data"""
    try:
        root = ET.fromstring(xml_content)

        # Check for essential fields
        required_fields = [
            './/CompanyName',
            './/MarketCap',
            './/PERatio'
        ]

        missing_fields = []
        for xpath in required_fields:
            if not root.find(xpath) is not None:
                missing_fields.append(xpath)

        if missing_fields:
            logger.warning(f"Missing fields in fundamentals: {missing_fields}")

        return len(missing_fields) == 0

    except ET.ParseError:
        logger.error("Invalid XML structure")
        return False
```

## Integration Patterns

### Provider Class Structure
```python
class IBKRProvider(BaseMarketDataProvider):
    def __init__(self):
        self.ib = IB()
        self.connected = False

    async def connect(self):
        """Establish IBKR connection"""
        if not self.connected:
            await self.ib.connectAsync(
                host=IBKR_CONFIG['host'],
                port=IBKR_CONFIG['port'],
                clientId=random.randint(1, 999)
            )
            self.connected = True

    async def get_market_data(self, tickers, criteria=None):
        """Fetch market data for multiple tickers"""
        await self.connect()

        results = {}
        for ticker in tickers:
            try:
                data = await self._fetch_single_ticker(ticker)
                results[ticker] = data
            except Exception as e:
                results[ticker] = {'error': str(e)}

        return results

    async def get_fundamentals(self, ticker):
        """Fetch fundamental data"""
        await self.connect()

        contract = Stock(ticker.split('.')[0], 'NSE', 'INR')
        xml_data = await self.ib.reqFundamentalDataAsync(
            contract, 'ReportSnapshot'
        )

        return self._parse_fundamentals_xml(xml_data)
```

### Error Recovery Patterns
```python
class IBKRErrorHandler:
    @staticmethod
    async def handle_error(error_code, ticker, retry_count=0):
        """Comprehensive error handling"""

        if error_code == 200:  # No security definition
            await Database.mark_ticker_inactive(ticker, "Security not found")

        elif error_code == 354:  # No subscription
            # Try YFinance fallback
            yf_data = await YFinanceProvider.get_market_data([ticker])
            return yf_data

        elif error_code in [502, 504]:  # Connection issues
            if retry_count < 3:
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await retry_request(ticker, retry_count + 1)

        # Log unhandled errors
        logger.error(f"Unhandled IBKR error {error_code} for {ticker}")
        return None
```

## Testing & Validation

### Connection Testing
```python
async def test_ibkr_connection():
    """Validate IBKR connectivity"""
    ib = IB()

    try:
        await asyncio.wait_for(
            ib.connectAsync('127.0.0.1', 7496, clientId=999),
            timeout=10
        )

        # Test market data
        contract = Stock('RELIANCE', 'NSE', 'INR')
        ticker = ib.reqMktData(contract, "", snapshot=True)
        await asyncio.sleep(2)

        success = ticker.last > 0
        ib.disconnect()

        return success

    except Exception as e:
        logger.error(f"IBKR test failed: {e}")
        return False
```

### Data Consistency Checks
```python
async def validate_ibkr_data_consistency():
    """Ensure IBKR data is consistent across requests"""

    # Request same ticker multiple times
    results = []
    for i in range(3):
        data = await fetch_ibkr_market_data('RELIANCE.NSE')
        results.append(data)
        await asyncio.sleep(1)

    # Check consistency
    prices = [r['last'] for r in results if r.get('last')]
    if prices:
        price_range = max(prices) - min(prices)
        # Allow for small variations due to market movement
        return price_range < max(prices) * 0.01  # Within 1%
```

## Performance Optimization

### Connection Pooling
```python
class IBKRConnectionPool:
    def __init__(self, max_connections=3):
        self.max_connections = max_connections
        self.connections = []
        self.semaphore = asyncio.Semaphore(max_connections)

    async def get_connection(self):
        """Get available IBKR connection"""
        async with self.semaphore:
            if not self.connections:
                ib = IB()
                await ib.connectAsync(
                    host=IBKR_CONFIG['host'],
                    port=IBKR_CONFIG['port'],
                    clientId=random.randint(1, 999)
                )
                self.connections.append(ib)

            return self.connections.pop()

    async def return_connection(self, ib):
        """Return connection to pool"""
        if len(self.connections) < self.max_connections:
            self.connections.append(ib)
        else:
            ib.disconnect()
```

## Monitoring & Observability

### Health Checks
```python
async def ibkr_health_check():
    """Monitor IBKR connection health"""
    metrics = {
        'connection_status': False,
        'market_data_working': False,
        'fundamentals_working': False,
        'response_time_ms': 0,
        'error_rate': 0.0
    }

    start_time = time.time()

    try:
        ib = IB()
        await ib.connectAsync('127.0.0.1', 7496, clientId=999)
        metrics['connection_status'] = True

        # Test market data
        contract = Stock('RELIANCE', 'NSE', 'INR')
        ticker = ib.reqMktData(contract, "", snapshot=True)
        await asyncio.sleep(1)
        metrics['market_data_working'] = ticker.last > 0

        # Test fundamentals
        xml = await ib.reqFundamentalDataAsync(contract, 'ReportSnapshot')
        metrics['fundamentals_working'] = len(xml) > 1000

        ib.disconnect()

    except Exception as e:
        logger.error(f"IBKR health check failed: {e}")

    metrics['response_time_ms'] = (time.time() - start_time) * 1000

    return metrics
```

## Related Documentation

- **[API Overview](./)** - General API integration guide
- **[YFinance Integration](./yfinance_integration.md)** - Alternative data source
- **[Architecture](../architecture.md)** - System integration patterns
- **[Error Handling](../../user_guide/troubleshooting.md)** - Common IBKR issues

---

**Status**: ✅ Complete | **Last Updated**: January 2025