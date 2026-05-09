-- FinanceDatabase-flattened fundamentals table.
-- Mirrors the schema produced by scripts/etl/finance_db/flatten_fd_nse.py.
CREATE TABLE IF NOT EXISTS stock_fundamentals_fd (
    ticker                   TEXT PRIMARY KEY,

    -- Basic Company Information
    company_name             TEXT,
    city                     TEXT,
    state                    TEXT,
    country                  TEXT,
    currency                 TEXT,
    exchange                 TEXT,
    market                   TEXT,
    website                  TEXT,

    -- Identifiers
    isin                     TEXT,
    cusip                    TEXT,
    figi                     TEXT,
    composite_figi           TEXT,
    shareclass_figi          TEXT,

    -- Industry classification
    industry                 TEXT,
    industry_group           TEXT,
    sector                   TEXT,

    -- Financial information
    market_cap_category      TEXT,  -- 'Large Cap' | 'Mid Cap' | 'Small Cap' | ...
    zipcode                  TEXT,

    -- Description
    summary                  TEXT,

    -- Metadata
    last_updated             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
