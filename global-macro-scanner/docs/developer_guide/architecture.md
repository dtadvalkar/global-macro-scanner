# 🏗️ System Architecture

## Overview

Global Market Scanner's architecture follows a modular, ETL-based design optimized for financial data processing and market scanning.

## Core Architecture Principles

### 1. Separation of Concerns
- **Data Collection**: External APIs (IBKR, YFinance)
- **Data Processing**: ETL pipeline with transformation layers
- **Data Storage**: PostgreSQL with optimized schemas
- **Business Logic**: Screening engine with configurable criteria

### 2. Scalability Design
- **Batch Processing**: Handle thousands of tickers efficiently
- **Rate Limiting**: Respect API constraints
- **Parallel Execution**: Concurrent processing where possible
- **Caching**: Reduce redundant API calls

### 3. Reliability Features
- **Fallback Systems**: Multiple data sources
- **Error Recovery**: Graceful failure handling
- **Data Validation**: Quality checks and audits
- **Monitoring**: Health checks and status tracking

## System Components

### Entry Point Layer
```
main.py → Orchestrates scanning workflows
├── Universe Management → screener/universe.py
├── Screening Engine → screener/core.py
├── Data Providers → data/providers.py
└── Storage → storage/database.py
```

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                     │
├─────────────────────────────────────────────────────────────┤
│  FinanceDatabase    IBKR Fundamentals    IBKR Market     YFinance │
│  (Company Data)     (XML + Ratios)       (Snapshots)     (OHLCV) │
└─────────────────────┬─────────────────────┬─────────────┬─────────┘
                      │                     │             │
                      ▼                     ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                     RAW DATA LAYER                          │
├─────────────────────────────────────────────────────────────┤
│  raw_fd_nse         raw_ibkr_nse         raw_ibkr_nse    prices_daily │
│  (JSON)             (XML + JSON)         .mkt_data       (YFinance)   │
└─────────────────────┼─────────────────────┼─────────────┼─────────────┘
                      │                     │             │
                      ▼                     ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                  ANALYTICAL LAYER                           │
├─────────────────────────────────────────────────────────────┤
│  stock_fundamentals ←───── scripts/etl/ibkr/flatten_ibkr_final.py           │
│  (81+ columns)                                              │
│                                                             │
│  current_market_data ←─── scripts/etl/ibkr/flatten_ibkr_market_data.py       │
│  (Current prices)                                           │
│                                                             │
│  prices_daily ────────────── scripts/etl/yfinance/collect_historical_yfinance.py─┘
│  (Historical OHLCV)                                         │
└─────────────────────────────────────────────────────────────┘
```

## Data Pipeline Stages

### Stage 1: Raw Data Ingestion
**Purpose**: Capture complete, unaltered data from sources
**Characteristics**:
- Maximum fidelity (no data loss)
- JSON/XML storage for complex structures
- Timestamp tracking for freshness
- Error logging for failed requests

### Stage 2: Data Transformation
**Purpose**: Convert raw data into analytical structures
**Processes**:
- **Fundamentals Flattening**: XML → Structured columns
- **Market Data Extraction**: JSON → Price tables
- **Data Validation**: Quality checks and cleaning
- **Relationship Building**: Foreign keys and constraints

### Stage 3: Application Layer
**Purpose**: Query-optimized tables for business logic
**Features**:
- **Universe Management**: Active/inactive status tracking
- **Screening Ready**: Pre-filtered, indexed data
- **Caching**: Reduced computation for repeated queries

## Key Design Decisions

### Database Schema Design

#### Normalized Structure
```sql
-- Core entities
tickers (universe management)
    ↓
stock_fundamentals (company data)
current_market_data (live prices)
prices_daily (historical prices)
```

#### Indexing Strategy
```sql
-- Performance optimization
CREATE INDEX idx_tickers_status ON tickers(status);
CREATE INDEX idx_fundamentals_mcap ON stock_fundamentals(market_cap_usd);
CREATE INDEX idx_prices_ticker_date ON prices_daily(ticker, trade_date);
```

### API Integration Patterns

#### Provider Abstraction
```python
class BaseProvider(ABC):
    @abstractmethod
    async def get_market_data(self, tickers, criteria):
        pass

class IBKRProvider(BaseProvider):
    async def get_market_data(self, tickers, criteria):
        # IBKR-specific implementation
        pass

class YFinanceProvider(BaseProvider):
    async def get_market_data(self, tickers, criteria):
        # YFinance-specific implementation
        pass
```

#### Fallback Chain
```
Primary → Fallback → Cache → Error
  ↓         ↓         ↓       ↓
 IBKR   YFinance  Redis   Log
```

### Concurrency Model

#### Controlled Parallelism
```python
# Rate limiting with semaphores
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def process_with_limit(ticker):
    async with semaphore:
        return await fetch_data(ticker)
```

#### Batch Processing
```python
# Database efficiency
BATCH_SIZE = 100
for i in range(0, len(data), BATCH_SIZE):
    batch = data[i:i + BATCH_SIZE]
    execute_values(cur, query, batch)
```

## Component Interactions

### Screening Workflow
```
1. Universe Generation
   └── FinanceDatabase API → tickers table

2. Data Collection
   ├── IBKR Fundamentals → raw_ibkr_nse → stock_fundamentals
   ├── IBKR Market Data → raw_ibkr_nse → current_market_data
   └── YFinance History → prices_daily

3. Screening Execution
   └── stock_fundamentals + current_market_data → screening_results

4. Result Processing
   └── screening_results → alerts + database updates
```

### ETL Pipeline Coordination
```python
# Orchestration pattern
async def run_full_pipeline():
    await collect_universe_data()
    await collect_fundamentals_data()
    await collect_market_data()
    await run_screening()
    await send_notifications()
```

## Performance Characteristics

### Throughput Targets
- **Universe Scan**: 5000 tickers in <5 minutes
- **Data Collection**: 2000 fundamentals in <10 minutes
- **Screening**: 5000 tickers in <2 minutes
- **API Rate Limits**: Stay within provider constraints

### Resource Utilization
- **Memory**: <2GB for typical scans
- **CPU**: Multi-core utilization for parallel processing
- **Network**: Efficient batching and caching
- **Storage**: Optimized PostgreSQL with proper indexing

## Reliability Patterns

### Error Handling
```python
try:
    result = await api_call()
except RateLimitError:
    await exponential_backoff()
except ConnectionError:
    await retry_with_fallback()
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    await graceful_degradation()
```

### Health Monitoring
- **Database connectivity** checks
- **API endpoint** availability
- **Rate limit** status tracking
- **Data freshness** validation
- **Performance metrics** collection

## Security Considerations

### API Key Management
```bash
# Environment variables only
IBKR_CLIENT_ID=1
TELEGRAM_TOKEN=secure_token_here
```

### Data Privacy
- No sensitive user data storage
- Secure credential handling
- Audit logging for compliance

## Related Documentation

- **[ETL Pipeline](./etl_pipeline.md)** - Detailed data processing
- **[Database Schema](./database_schema.md)** - Complete data model
- **[API Integrations](./api_integrations/)** - External service details
- **[Performance Optimization](../technical_reference/performance_optimization.md)** - Tuning guides

---