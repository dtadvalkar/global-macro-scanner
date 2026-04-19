# 🗄️ Database Schema Reference

## Overview

Complete PostgreSQL schema for Global Market Scanner with table definitions, relationships, and indexing strategy.

## Schema Architecture

### Layered Design
```
Universe Layer → Raw Data Layer → Analytical Layer → Application Layer
     ↓              ↓                ↓                ↓
  tickers       raw_* tables    fundamentals    query optimization
```

## Table Definitions

### Universe Management

#### `tickers` - Master Security Registry
```sql
CREATE TABLE tickers (
    ticker TEXT PRIMARY KEY,              -- e.g., 'RELIANCE.NS'
    market TEXT NOT NULL,                 -- e.g., 'NSE', 'NYSE'
    status TEXT DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'ERROR')),
    status_message TEXT,                  -- API error details
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data
INSERT INTO tickers (ticker, market, status) VALUES
('RELIANCE.NS', 'NSE', 'ACTIVE'),
('TCS.NS', 'NSE', 'ACTIVE');
```

### Raw Data Layer

#### `raw_fd_nse` - FinanceDatabase Raw Data
```sql
CREATE TABLE raw_fd_nse (
    ticker TEXT PRIMARY KEY,
    raw_data JSONB NOT NULL,              -- Complete company metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- JSON structure example
{
  "company_name": "Reliance Industries Limited",
  "sector": "Energy",
  "industry": "Oil & Gas Refining",
  "market_cap": 1500000000000,
  "currency": "INR"
}
```

#### `raw_ibkr_nse` - IBKR Raw Data
```sql
CREATE TABLE raw_ibkr_nse (
    ticker TEXT PRIMARY KEY,
    xml_snapshot TEXT,                    -- Complete fundamentals XML
    xml_ratios TEXT,                      -- Financial ratios XML
    mkt_data JSONB,                       -- Current market snapshot
    contract_details JSONB,               -- IBKR contract info
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- mkt_data JSON structure
{
  "Ticker": {
    "last": 2500.50,
    "close": 2480.25,
    "open": 2495.00,
    "high": 2510.75,
    "low": 2480.00,
    "volume": 1500000
  }
}
```

### Analytical Layer

#### `stock_fundamentals` - Flattened Fundamentals
```sql
CREATE TABLE stock_fundamentals (
    ticker TEXT PRIMARY KEY,

    -- Identifiers
    company_name TEXT,
    isin TEXT,
    ric TEXT,
    exchange_code TEXT,

    -- Financial Metrics (extracted from IBKR XML)
    market_cap_usd NUMERIC,
    pe_ratio NUMERIC,
    price_to_book NUMERIC,
    dividend_yield_pct NUMERIC,
    roe_pct NUMERIC,
    gross_margin_pct NUMERIC,

    -- Industry Classification
    sector TEXT,
    industry TEXT,
    sub_industry TEXT,

    -- Market Data
    fifty_two_w_high NUMERIC,
    fifty_two_w_low NUMERIC,
    beta NUMERIC,

    -- Metadata
    data_source TEXT,                    -- 'ibkr', 'financedatabase'
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign Key Relationship
    CONSTRAINT fk_fundamentals_ticker
        FOREIGN KEY (ticker) REFERENCES tickers(ticker)
);

-- Partial view of 81+ columns
SELECT ticker, company_name, market_cap_usd, pe_ratio, sector
FROM stock_fundamentals
WHERE market_cap_usd > 1000000000
ORDER BY market_cap_usd DESC;
```

#### `current_market_data` - Live Market State
```sql
CREATE TABLE current_market_data (
    ticker TEXT PRIMARY KEY,

    -- Current Prices
    last_price NUMERIC,                  -- Last traded price
    close_price NUMERIC,                 -- Previous close
    open_price NUMERIC,                  -- Today's open
    high_price NUMERIC,                  -- Today's high
    low_price NUMERIC,                   -- Today's low

    -- Volume
    volume BIGINT,                       -- Trading volume

    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign Key
    CONSTRAINT fk_market_data_ticker
        FOREIGN KEY (ticker) REFERENCES tickers(ticker)
);

-- Current market overview
SELECT
    ticker,
    last_price,
    ROUND((last_price - close_price) / close_price * 100, 2) as pct_change,
    volume
FROM current_market_data
WHERE last_price > 0
ORDER BY volume DESC;
```

### Application Layer

#### `prices_daily` - Historical OHLCV Bars
```sql
CREATE TABLE prices_daily (
    ticker        TEXT NOT NULL,
    price_date    DATE NOT NULL,
    open          NUMERIC,
    high          NUMERIC,
    low           NUMERIC,
    close         NUMERIC,
    volume        BIGINT,
    datetimestamp TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (ticker, price_date)
);

-- Historical price analysis
SELECT
    ticker,
    price_date,
    close,
    volume,
    ROUND((close - LAG(close) OVER (PARTITION BY ticker ORDER BY price_date)) / LAG(close) OVER (PARTITION BY ticker ORDER BY price_date) * 100, 2) as daily_return
FROM prices_daily
WHERE price_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY ticker, price_date;
```

## Indexing Strategy

### Performance Indexes
```sql
-- Core lookup indexes
CREATE INDEX idx_tickers_status ON tickers(status);
CREATE INDEX idx_tickers_market ON tickers(market);
CREATE INDEX idx_tickers_last_updated ON tickers(last_updated);

-- Fundamentals analysis
CREATE INDEX idx_fundamentals_mcap ON stock_fundamentals(market_cap_usd);
CREATE INDEX idx_fundamentals_sector ON stock_fundamentals(sector);
CREATE INDEX idx_fundamentals_pe ON stock_fundamentals(pe_ratio);
CREATE INDEX idx_fundamentals_data_source ON stock_fundamentals(data_source);

-- Market data queries
CREATE INDEX idx_market_data_last_price ON current_market_data(last_price);
CREATE INDEX idx_market_data_volume ON current_market_data(volume);
CREATE INDEX idx_market_data_updated ON current_market_data(last_updated);

-- Historical data analysis
CREATE INDEX idx_prices_ticker_date ON prices_daily(ticker, price_date);
CREATE INDEX idx_prices_volume ON prices_daily(volume) WHERE volume > 0;
```

### Partial Indexes
```sql
-- Optimize for active tickers only
CREATE INDEX idx_active_tickers ON tickers(symbol) WHERE status = 'ACTIVE';

-- High market cap companies
CREATE INDEX idx_large_cap_fundamentals ON stock_fundamentals(ticker)
WHERE market_cap_usd > 10000000000;

-- Recent price data
CREATE INDEX idx_recent_prices ON prices_daily(price_date)
WHERE price_date >= CURRENT_DATE - INTERVAL '1 year';
```

## Constraints & Data Integrity

### Check Constraints
```sql
-- Valid price ranges
ALTER TABLE current_market_data
ADD CONSTRAINT chk_positive_prices
CHECK (last_price > 0 AND close_price > 0);

-- Valid market caps
ALTER TABLE stock_fundamentals
ADD CONSTRAINT chk_reasonable_mcap
CHECK (market_cap_usd BETWEEN 1000000 AND 10000000000000);
```

### Foreign Key Relationships
```sql
-- Ensure referential integrity
ALTER TABLE stock_fundamentals
ADD CONSTRAINT fk_fundamentals_ticker
FOREIGN KEY (ticker) REFERENCES tickers(ticker) ON DELETE CASCADE;

ALTER TABLE current_market_data
ADD CONSTRAINT fk_market_data_ticker
FOREIGN KEY (ticker) REFERENCES tickers(ticker) ON DELETE CASCADE;
```

## Data Types & Storage Optimization

### JSONB Usage
```sql
-- Efficient storage for complex structures
CREATE INDEX idx_raw_fd_gin ON raw_fd_nse USING GIN (raw_data);
CREATE INDEX idx_raw_ibkr_gin ON raw_ibkr_nse USING GIN (mkt_data);

-- JSON path queries
SELECT ticker FROM raw_fd_nse
WHERE raw_data ->> 'sector' = 'Technology';
```

### Numeric Precision
```sql
-- Appropriate precision for financial data
market_cap_usd NUMERIC(20,2),    -- Up to $10 trillion
pe_ratio NUMERIC(8,2),           -- Typical range 0-500
price NUMERIC(12,4),             -- Stock prices up to $999,999.9999
```

## Partitioning Strategy (Future)

### Time-Based Partitioning
```sql
-- Partition historical prices by year
CREATE TABLE prices_daily_y2024 PARTITION OF prices_daily
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- Automatic partitioning
CREATE TABLE prices_daily_y2025 PARTITION OF prices_daily
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

## Backup & Recovery

### Logical Backups
```bash
# Schema only
pg_dump --schema-only -h localhost -U user dbname > schema.sql

# Data only (compressed)
pg_dump --data-only --compress=9 -h localhost -U user dbname > data.dump
```

### Point-in-Time Recovery
```sql
-- Enable WAL archiving
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET archive_mode = on;
ALTER SYSTEM SET archive_command = 'cp %p /var/lib/postgresql/archive/%f';
```

## Monitoring Queries

### Database Health
```sql
-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage
SELECT
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### Data Quality Checks
```sql
-- Missing data audit
SELECT
    'stock_fundamentals' as table_name,
    COUNT(*) as total_records,
    COUNT(*) FILTER (WHERE market_cap_usd IS NULL) as missing_mcap,
    ROUND(COUNT(*) FILTER (WHERE market_cap_usd IS NULL) * 100.0 / COUNT(*), 2) as pct_missing
FROM stock_fundamentals

UNION ALL

SELECT
    'current_market_data' as table_name,
    COUNT(*) as total_records,
    COUNT(*) FILTER (WHERE last_price IS NULL OR last_price = 0) as missing_price,
    ROUND(COUNT(*) FILTER (WHERE last_price IS NULL OR last_price = 0) * 100.0 / COUNT(*), 2) as pct_missing
FROM current_market_data;
```

## Related Documentation

- **[Architecture](./architecture.md)** - System design overview
- **[ETL Pipeline](./etl_pipeline.md)** - Data processing workflows
- **[API Integrations](./api_integrations/)** - External data source schemas

---

**Status**: ✅ Complete | **Last Updated**: April 2026