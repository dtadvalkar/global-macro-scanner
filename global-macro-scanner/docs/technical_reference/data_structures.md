# 🏗️ Data Structures Reference

## Overview

Complete reference for all data structures used in the Global Market Scanner system.

## Core Entity Relationships

### Universe Management
```
tickers (Master Registry)
├── symbol: TEXT (PK) - e.g., "RELIANCE.NSE"
├── market: TEXT - e.g., "NSE", "NYSE"
├── status: TEXT - "ACTIVE", "INACTIVE", "ERROR"
├── status_message: TEXT - API error details
└── last_updated: TIMESTAMP
```

### Raw Data Storage
```
raw_fd_nse (FinanceDatabase)
├── ticker: TEXT (PK)
├── raw_data: JSONB - Complete company metadata
└── last_updated: TIMESTAMP

raw_ibkr_nse (IBKR Fundamentals + Market)
├── ticker: TEXT (PK)
├── xml_snapshot: TEXT - Fundamentals XML (~50KB)
├── xml_ratios: TEXT - Financial ratios XML (~25KB)
├── mkt_data: JSONB - Current market snapshot
├── contract_details: JSONB - IBKR contract info
└── last_updated: TIMESTAMP

raw_yf_nse (YFinance)
├── ticker: TEXT (PK)
├── raw_info: JSONB - Company info dictionary
├── raw_fast_info: JSONB - Quick access metrics
└── last_updated: TIMESTAMP
```

### Analytical Data Structures
```
stock_fundamentals (81+ columns)
├── Core Identifiers
│   ├── ticker: TEXT (PK)
│   ├── company_name: TEXT
│   ├── isin: TEXT
│   ├── ric: TEXT
│   └── exchange_code: TEXT
├── Financial Metrics
│   ├── market_cap_usd: NUMERIC
│   ├── pe_ratio: NUMERIC
│   ├── price_to_book: NUMERIC
│   ├── dividend_yield_pct: NUMERIC
│   ├── roe_pct: NUMERIC
│   └── gross_margin_pct: NUMERIC
├── Industry Classification
│   ├── sector: TEXT
│   ├── industry: TEXT
│   └── sub_industry: TEXT
├── Market Data
│   ├── fifty_two_w_high: NUMERIC
│   ├── fifty_two_w_low: NUMERIC
│   └── beta: NUMERIC
└── Metadata
    ├── data_source: TEXT ("ibkr", "financedatabase")
    └── last_updated: TIMESTAMP

current_market_data (Live Market State)
├── ticker: TEXT (PK)
├── last_price: NUMERIC - Current/last traded price
├── close_price: NUMERIC - Previous close
├── open_price: NUMERIC - Today's open
├── high_price: NUMERIC - Today's high
├── low_price: NUMERIC - Today's low
├── volume: BIGINT - Trading volume
└── last_updated: TIMESTAMP

prices_daily (Historical OHLCV)
├── ticker: TEXT (PK component)
├── trade_date: DATE (PK component)
├── open: NUMERIC
├── high: NUMERIC
├── low: NUMERIC
├── close: NUMERIC
├── adj_close: NUMERIC
├── volume: BIGINT
├── source: TEXT (PK component) - "yf", "ibkr"
└── created_at: TIMESTAMP
```

## JSON Schema Definitions

### FinanceDatabase Raw Data
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "company_name": {"type": "string"},
    "sector": {"type": "string"},
    "industry": {"type": "string"},
    "market_cap": {"type": "number"},
    "currency": {"type": "string"},
    "country": {"type": "string"},
    "employees": {"type": "integer"},
    "description": {"type": "string"},
    "website": {"type": "string"}
  },
  "required": ["company_name", "market_cap"]
}
```

### IBKR Market Data Snapshot
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "Ticker": {
      "type": "object",
      "properties": {
        "last": {"type": "number", "minimum": 0},
        "close": {"type": "number", "minimum": 0},
        "open": {"type": "number", "minimum": 0},
        "high": {"type": "number", "minimum": 0},
        "low": {"type": "number", "minimum": 0},
        "volume": {"type": "integer", "minimum": 0}
      }
    }
  }
}
```

### YFinance Info Structure
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "longName": {"type": "string"},
    "sector": {"type": "string"},
    "industry": {"type": "string"},
    "marketCap": {"type": "number"},
    "trailingPE": {"type": "number"},
    "dividendYield": {"type": "number"},
    "fiftyTwoWeekHigh": {"type": "number"},
    "fiftyTwoWeekLow": {"type": "number"},
    "beta": {"type": "number"},
    "currency": {"type": "string"}
  }
}
```

## In-Memory Data Structures

### Screening Criteria
```python
CRITERIA = {
    # Price proximity filters
    'price_52w_low_pct': 1.01,        # Within 1% of 52-week low
    'min_volume': 100000,             # Minimum daily volume
    'max_price': 1000.00,             # Maximum stock price
    'min_price': 1.00,                # Minimum stock price

    # Technical filters
    'rsi_min': 20,                    # RSI lower bound
    'rsi_max': 45,                    # RSI upper bound
    'ma_support_pct': 1.03,           # Price within 3% of SMA50
    'atr_min': 1.5,                   # Minimum ATR percentage
    'atr_max': 8.0,                   # Maximum ATR percentage

    # Market cap filters (by exchange)
    'market_cap_filters': {
        'NSE': {'min': 500000000, 'max': 50000000000},    # $500M - $50B
        'NYSE': {'min': 1000000000, 'max': 100000000000}, # $1B - $100B
        'NASDAQ': {'min': 500000000, 'max': 50000000000}  # $500M - $50B
    }
}
```

### Provider Response Format
```python
# Standardized response from all providers
MarketDataResponse = {
    'ticker': str,                    # Original ticker symbol
    'price': float,                   # Current price
    'volume': int,                    # Trading volume
    'market_cap': float,              # Company market cap
    '52w_high': float,                # 52-week high
    '52w_low': float,                 # 52-week low
    'pe_ratio': float,                # Price-to-earnings ratio
    'sector': str,                    # Industry sector
    'industry': str,                  # Specific industry
    'error': str,                     # Error message if failed
    'source': str,                    # 'ibkr', 'yfinance'
    'timestamp': datetime             # When data was fetched
}
```

### ETL Pipeline Configuration
```python
ETL_CONFIG = {
    'batch_sizes': {
        'ibkr_fundamentals': 50,       # Concurrent IBKR requests
        'yfinance_bulk': 200,          # Tickers per bulk download
        'database_insert': 1000        # Records per batch insert
    },

    'timeouts': {
        'ibkr_connection': 30,         # Connection timeout
        'ibkr_request': 20,            # Individual request timeout
        'yfinance_download': 60,       # Bulk download timeout
        'database_operation': 300      # DB operation timeout
    },

    'retries': {
        'ibkr_connection': 3,          # Connection retry attempts
        'api_request': 2,              # API request retries
        'database_operation': 1        # DB operation retries
    },

    'rate_limits': {
        'ibkr_per_minute': 100,        # IBKR requests/minute
        'yfinance_per_minute': 50,     # YFinance requests/minute
        'database_connections': 10     # Max DB connections
    }
}
```

## Data Flow Objects

### Raw Data Ingestion
```python
RawDataIngestion = {
    'source': str,                    # 'financedatabase', 'ibkr', 'yfinance'
    'ticker': str,                    # Original ticker symbol
    'data_type': str,                 # 'fundamentals', 'market_data', 'ohlcv'
    'raw_content': Union[str, dict],  # XML string or JSON dict
    'metadata': {
        'fetch_timestamp': datetime,
        'data_size_bytes': int,
        'compression': str,
        'quality_score': float
    },
    'processing_status': str          # 'pending', 'processing', 'completed', 'failed'
}
```

### Transformed Analytical Data
```python
AnalyticalData = {
    'entity_type': str,               # 'company', 'market_data', 'timeseries'
    'primary_key': dict,              # Composite key fields
    'data_fields': dict,              # Field name -> value mapping
    'data_quality': {
        'completeness_score': float,  # 0.0 - 1.0
        'accuracy_score': float,      # 0.0 - 1.0
        'timeliness_score': float     # 0.0 - 1.0
    },
    'provenance': {
        'source_system': str,
        'transformation_applied': list,
        'last_updated': datetime
    }
}
```

### Screening Results
```python
ScreeningResult = {
    'ticker': str,
    'screening_run_id': str,
    'criteria_applied': dict,         # Which criteria were checked
    'criteria_passed': dict,          # Which criteria passed
    'score': float,                   # Overall match score (0-100)
    'rank': int,                      # Position in results
    'market_data': dict,              # Current market data used
    'fundamentals': dict,             # Company fundamentals used
    'alert_level': str,               # 'weak', 'moderate', 'strong', 'extreme'
    'generated_at': datetime,
    'expires_at': datetime            # When this result becomes stale
}
```

## Configuration Structures

### Database Configuration
```python
DB_CONFIG = {
    'host': str,                      # Database host
    'port': int,                      # Database port
    'database': str,                  # Database name
    'username': str,                  # Database user
    'password': str,                  # Database password
    'ssl_mode': str,                  # SSL configuration
    'connection_pool': {
        'min_connections': int,
        'max_connections': int,
        'connection_timeout': int
    },
    'query_timeout': int,             # Query timeout in seconds
    'retry_on_failure': bool,         # Auto-retry failed connections
    'health_check_interval': int      # Health check frequency
}
```

### API Provider Configuration
```python
API_CONFIG = {
    'ibkr': {
        'host': str,                  # TWS host (usually 127.0.0.1)
        'ports': [int],               # Available ports [7496, 7497, 4001, 4002]
        'market_data_type': int,      # 3 for delayed, 1 for live
        'max_concurrent': int,        # Max concurrent requests
        'request_timeout': int,       # Request timeout in seconds
        'retry_attempts': int,        # Number of retry attempts
        'rate_limit_per_minute': int  # API rate limit
    },

    'yfinance': {
        'max_batch_size': int,        # Max tickers per bulk request
        'rate_limit_per_minute': int, # API rate limit
        'download_timeout': int,      # Download timeout in seconds
        'threads_enabled': bool,      # Use threading for bulk downloads
        'auto_adjust_prices': bool,   # Adjust OHLCV for splits/dividends
        'include_prepost': bool       # Include pre/post market data
    },

    'financedatabase': {
        'api_timeout': int,           # API request timeout
        'cache_ttl_hours': int,       # Cache validity period
        'retry_attempts': int,        # Number of retry attempts
        'rate_limit_per_minute': int  # API rate limit
    }
}
```

## Error and Exception Structures

### API Error Response
```python
APIError = {
    'error_code': int,                # HTTP status or API error code
    'error_message': str,             # Human-readable error description
    'error_type': str,                # 'connection', 'rate_limit', 'data_error', 'auth'
    'provider': str,                  # 'ibkr', 'yfinance', 'financedatabase'
    'ticker': str,                    # Affected ticker (if applicable)
    'retryable': bool,                # Whether the operation can be retried
    'retry_after_seconds': int,       # Suggested wait time before retry
    'context': dict,                  # Additional error context
    'timestamp': datetime             # When the error occurred
}
```

### Validation Error
```python
ValidationError = {
    'field_name': str,                # Which field failed validation
    'field_value': any,               # The invalid value
    'validation_rule': str,           # Which validation rule failed
    'expected_format': str,           # Expected value format
    'error_message': str,             # Human-readable explanation
    'severity': str,                  # 'warning', 'error', 'critical'
    'correction_suggestion': str,     # How to fix the issue
    'data_source': str                # Where the data came from
}
```

## Performance Metrics Structures

### System Performance
```python
PerformanceMetrics = {
    'timestamp': datetime,
    'operation_type': str,            # 'screening', 'data_fetch', 'etl'
    'duration_seconds': float,
    'records_processed': int,
    'success_rate': float,            # 0.0 - 1.0
    'error_rate': float,              # 0.0 - 1.0
    'throughput_per_second': float,
    'memory_usage_mb': float,
    'cpu_usage_percent': float,
    'api_calls_made': int,
    'rate_limit_hits': int
}
```

### Data Quality Metrics
```python
DataQualityMetrics = {
    'table_name': str,
    'total_records': int,
    'null_values': dict,              # field_name -> count
    'duplicate_records': int,
    'outlier_records': int,
    'completeness_score': float,      # 0.0 - 1.0
    'accuracy_score': float,          # 0.0 - 1.0
    'consistency_score': float,       # 0.0 - 1.0
    'timeliness_score': float,        # 0.0 - 1.0
    'last_assessed': datetime
}
```

---

**Status**: ✅ Complete | **Last Updated**: January 2025