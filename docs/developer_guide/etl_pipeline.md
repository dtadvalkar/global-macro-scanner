# 🔄 ETL Pipeline Guide

## Overview

The ETL (Extract, Transform, Load) pipeline processes raw financial data into analytical structures for market scanning.

## Pipeline Architecture

### Three-Stage Design
```
Extract → Transform → Load
   ↓        ↓        ↓
Raw    Analytical  Query
Data     Data     Ready
```

## Stage 1: Extract (Data Collection)

### Data Sources

#### FinanceDatabase Universe
```python
# Extract: Pull complete NSE universe
equities = fd.Equities()
nse_data = equities.select(exchange='NSE')

# Load: Store raw JSON
for ticker, data in nse_data.items():
    insert_raw_fd(ticker, data)
```

#### IBKR Fundamentals
```python
# Extract: XML data via IBKR API
contract = Stock(ticker, 'NSE', 'INR')
xml_snapshot = await ib.reqFundamentalDataAsync(contract, 'ReportSnapshot')
xml_ratios = await ib.reqFundamentalDataAsync(contract, 'ReportRatios')

# Load: Store XML strings
insert_raw_ibkr(ticker, xml_snapshot, xml_ratios, None, None)
```

#### IBKR Market Data
```python
# Extract: Current market snapshot
ib.reqMarketDataType(3)
ticker = ib.reqMktData(contract, "", snapshot=True)
await asyncio.sleep(2)  # Wait for data
market_data = util.tree(ticker)

# Load: Store JSON snapshot
update_raw_ibkr_mkt_data(ticker, market_data)
```

#### YFinance Historical
```python
# Extract: Bulk OHLCV download
data_hist = yf.download(
    tickers=ticker_list,
    period="2y",
    interval="1d",
    threads=True
)

# Load: Parse and store OHLCV
for ticker in ticker_list:
    df = data_hist[ticker].dropna()
    insert_prices_daily_batch(ticker, df)
```

## Stage 2: Transform (Data Processing)

### Fundamentals Flattening
```python
# Transform: XML → Structured columns
def flatten_fundamentals(xml_content):
    root = ET.fromstring(xml_content)

    # Extract 80+ fields from XML structure
    data = {
        'ticker': extract_ticker(root),
        'company_name': extract_company_name(root),
        'market_cap_usd': extract_market_cap(root),
        'pe_ratio': extract_pe_ratio(root),
        # ... 80+ more fields
    }

    return data

# Process all raw fundamentals
for row in raw_ibkr_fundamentals:
    flattened = flatten_fundamentals(row.xml_snapshot)
    insert_stock_fundamentals(flattened)
```

### Market Data Extraction
```python
# Transform: JSON → Price fields
def extract_market_data(json_data):
    ticker_data = json_data.get('Ticker', {})

    return {
        'last_price': float(ticker_data.get('last', 0) or 0),
        'close_price': float(ticker_data.get('close', 0) or 0),
        'open_price': float(ticker_data.get('open', 0) or 0),
        'high_price': float(ticker_data.get('high', 0) or 0),
        'low_price': float(ticker_data.get('low', 0) or 0),
        'volume': int(ticker_data.get('volume', 0) or 0)
    }

# Process market snapshots
for row in raw_ibkr_market_data:
    extracted = extract_market_data(row.mkt_data)
    insert_current_market_data(row.ticker, extracted)
```

## Stage 3: Load (Data Storage)

### Batch Processing Strategy
```python
# Efficient bulk inserts
BATCH_SIZE = 100

def batch_insert(table, data_list):
    for i in range(0, len(data_list), BATCH_SIZE):
        batch = data_list[i:i + BATCH_SIZE]
        execute_values(cur, INSERT_QUERY, batch)
        conn.commit()
```

### Conflict Resolution
```sql
-- Handle duplicates gracefully
INSERT INTO stock_fundamentals (ticker, ...)
VALUES (%s, %s, ...)
ON CONFLICT (ticker)
DO UPDATE SET
    company_name = EXCLUDED.company_name,
    market_cap_usd = EXCLUDED.market_cap_usd,
    last_updated = CURRENT_TIMESTAMP;
```

## Pipeline Orchestration

### Sequential Execution
```python
async def run_etl_pipeline():
    """Complete ETL workflow"""

    # Phase 1: Extract
    print("📥 Phase 1: Data Extraction")
    await extract_universe_data()
    await extract_ibkr_fundamentals()
    await extract_ibkr_market_data()
    await extract_yfinance_history()

    # Phase 2: Transform
    print("🔄 Phase 2: Data Transformation")
    await transform_fundamentals()
    await transform_market_data()

    # Phase 3: Load/Validate
    print("💾 Phase 3: Data Loading & Validation")
    await validate_data_quality()
    await update_pipeline_status()
```

### Error Handling & Recovery
```python
async def robust_etl_step(step_func, step_name):
    """Execute ETL step with error handling"""
    try:
        await step_func()
        log_success(step_name)
    except Exception as e:
        log_error(f"{step_name} failed: {e}")
        # Continue with other steps or trigger recovery
        await handle_etl_error(step_name, e)
```

## Data Quality Assurance

### Validation Checks
```python
def validate_fundamentals_data():
    """Quality checks for flattened fundamentals"""
    checks = [
        ("Market cap should be positive", "market_cap_usd > 0"),
        ("Company name should exist", "company_name IS NOT NULL"),
        ("PE ratio should be reasonable", "pe_ratio BETWEEN 0 AND 1000"),
    ]

    for description, condition in checks:
        invalid_count = count_where(f"NOT ({condition})")
        if invalid_count > 0:
            log_warning(f"{description}: {invalid_count} invalid records")
```

### Audit Trails
```python
# Track ETL execution
etl_log = {
    'pipeline_run_id': generate_id(),
    'start_time': datetime.now(),
    'steps_completed': [],
    'errors_encountered': [],
    'records_processed': 0,
    'end_time': None
}
```

## Performance Optimization

### Parallel Processing
```python
# Concurrent API calls within rate limits
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def process_ticker_parallel(ticker):
    async with semaphore:
        return await fetch_ibkr_data(ticker)

# Process in batches
tasks = [process_ticker_parallel(t) for t in tickers]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Memory Management
```python
# Process large datasets in chunks
def process_large_dataset(data, chunk_size=1000):
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        process_chunk(chunk)
        # Allow garbage collection
        del chunk
```

## Monitoring & Observability

### Pipeline Metrics
```python
pipeline_metrics = {
    'total_tickers_processed': 0,
    'successful_extractions': 0,
    'failed_extractions': 0,
    'transformation_errors': 0,
    'load_time_seconds': 0,
    'data_quality_score': 0.0
}
```

### Health Checks
```python
def check_pipeline_health():
    """Validate pipeline components"""
    checks = [
        check_database_connectivity(),
        check_api_endpoints(),
        check_data_freshness(),
        check_error_rates()
    ]

    return all(checks)
```

## ETL Scripts Reference

| Script | Purpose | Input | Output | Frequency |
|--------|---------|-------|--------|-----------|
| `scripts/etl/yfinance/collect_historical_yfinance.py` | Bulk YF download | Fundamentals tickers | prices_daily | One-time |
| `scripts/etl/ibkr/flatten_ibkr_market_data.py` | Market data extraction | raw_ibkr_nse.mkt_data | current_market_data | As needed |
| `scripts/etl/ibkr/flatten_ibkr_final.py` | Fundamentals flattening | raw_ibkr_nse XML | stock_fundamentals | Quarterly |
| `main.py` | Full pipeline orchestration | Universe spec | All tables | Daily |

## Error Recovery

### Partial Failure Handling
```python
async def recover_from_partial_failure(failed_step):
    """Resume pipeline from failed step"""
    if failed_step == 'extract_ibkr':
        # Re-run only failed extractions
        await retry_failed_ibkr_requests()
    elif failed_step == 'transform':
        # Re-process from raw data
        await retransform_all_data()
```

### Data Consistency
```python
# Ensure transactional integrity
async def atomic_etl_operation(operation):
    async with database.transaction():
        result = await operation()
        # Validate consistency
        await validate_data_integrity()
        return result
```

## Related Documentation

- **[Architecture](./architecture.md)** - System design overview
- **[Database Schema](./database_schema.md)** - Data model details
- **[API Integrations](./api_integrations/)** - External service details
- **[Performance Optimization](../technical_reference/performance_optimization.md)** - Tuning guides

---