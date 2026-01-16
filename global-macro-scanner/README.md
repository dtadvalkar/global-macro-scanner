# Global Macro Scanner

A **premium** Python‑based macro‑scanner that pulls market data from **Interactive Brokers (IBKR)** (delayed Type 3) and **Yahoo Finance** as a fallback. It stores a full universe of tickers in PostgreSQL, tracks ticker status, and implements a **200‑day parole** system for inactive or delisted symbols.

## ✨ Key Features
- **Dynamic universe**: Pulls the complete list of symbols from `financedatabase` on first run and caches it in PostgreSQL.
- **Smart ticker status**:
  - `status` (`ACTIVE`, `INACTIVE`, `ERROR`)
  - `status_message` stores the raw API error (e.g. `Error 200: No security definition`)
  - **Parole**: Inactive tickers are automatically re‑checked after 200 days.
- **CLI mode**: `--mode live` runs a full scan; `--mode test` limits NSE to the top `nse_top_limit` (default 200) for quick debugging.
- **Robust fallback**: IBKR → YFinance with clear error handling.
- **Database‑driven caching**: `tickers` table holds the source‑of‑truth; `stock_fundamentals` holds detailed data.
- **Telegram alerts** (optional) for scan results.

## 📦 Installation
```bash
# Clone the repo
git clone https://github.com/yourorg/global-macro-scanner.git
cd global-macro-scanner

# Install dependencies (Python 3.10+)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables (create a .env file)
# DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
# IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID (optional)
# TELEGRAM_TOKEN, CHAT_ID (optional)
```

## 🚀 Running the scanner
```bash
# Live full‑universe scan (default)
python main.py --exchanges NSE --mode live

# Quick test mode (limits NSE to top 200 tickers)
python main.py --exchanges NSE --mode test
```
The script will:
1. Refresh the ticker list from FinanceDatabase if the cache is stale.
2. Load **actionable** tickers (`ACTIVE` + those whose `last_updated` > 200 days).
3. Scan via IBKR (parallel, batch size 50) and fall back to YFinance where needed.
4. Update the database with any status changes.

## 🗄️ Database Schema

### 🏛️ Core Tables
```sql
CREATE TABLE IF NOT EXISTS tickers (
    symbol TEXT PRIMARY KEY,
    market TEXT,
    status TEXT DEFAULT 'ACTIVE',
    status_message TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 📡 Unified Price Data (Recurring)
```sql
CREATE TABLE IF NOT EXISTS prices_daily (
    ticker       TEXT,
    trade_date   DATE,
    open         NUMERIC,
    high         NUMERIC,
    low          NUMERIC,
    close        NUMERIC,
    adj_close    NUMERIC,
    volume       BIGINT,
    source       TEXT NOT NULL,  -- 'ibkr', 'yf', etc.
    PRIMARY KEY (ticker, trade_date, source)
);
```

### 🧬 Raw-Fidelity Storage (Maximum Truth)
To ensure no data is lost during ingestion, we store the full verbatim output from each provider.

| Table | Source | Content Type |
| :--- | :--- | :--- |
| `raw_fd_nse` | FinanceDatabase | Full JSON Metadata |
| `raw_ibkr_nse` | IBKR (Reuters) | Complete XML Snapshot + Ratios |
| `raw_yf_nse` | YFinance | Exhaustive `.info` Property Dictionary |

```sql
-- Example: Accessing Delayed Market Ticks (Nested JSONB)
SELECT 
    ticker,
    mkt_data->'Ticker'->>'open' as open_price,
    mkt_data->'Ticker'->>'close' as prior_close,
    mkt_data->'Ticker'->>'last' as current_last -- -1.0 if market is closed
FROM raw_ibkr_nse;
```

> [!TIP]
> **Why is Volume 0?**: IBKR's `volume` field (TickType 74) represents **cumulative volume for the current trading day**. If you query while the market is closed (and before the next open), it resets to 0. Use the `xml_snapshot` or `prices_daily` for historical volume data.

## 📊 **Complete ETL Pipeline & Market Data Architecture**

### **🏗️ ETL Pipeline Overview**
```
Raw Data Sources → Archival Layer → Analytical Layer → Application Layer
```

**Phase 1: Raw Data Ingestion**
- FinanceDatabase → `raw_fd_nse` (JSON metadata)
- IBKR Fundamentals → `raw_ibkr_nse` (XML snapshots & ratios)
- IBKR Market Data → `raw_ibkr_nse.mkt_data` (JSON snapshots)

**Phase 2: Data Transformation**
- Fundamentals Flattening → `stock_fundamentals` (81-column analytical table)
- Market Data Flattening → `current_market_data` (structured current prices)

**Phase 3: Historical Data Collection**
- YFinance Bulk Download → `prices_daily` (2-year OHLCV history)

### **🗂️ Complete Table Architecture**

#### **📥 Raw Data Layer (Archival)**
| Table | Source | Purpose | Data Type | Frequency |
|-------|--------|---------|-----------|-----------|
| `raw_fd_nse` | FinanceDatabase | Company metadata | JSONB | Quarterly |
| `raw_ibkr_nse` | IBKR | Fundamentals XML + Market snapshots | TEXT + JSONB | Daily |
| `raw_yf_nse` | YFinance | Company info | JSONB | As needed |

#### **🔄 Analytical Layer (Structured)**
| Table | Source | Purpose | Key Fields | Update Frequency |
|-------|--------|---------|------------|------------------|
| `stock_fundamentals` | IBKR/FD | Company fundamentals | 81+ financial metrics | Quarterly |
| `current_market_data` | IBKR | Current market state | last_price, open, high, low, volume | Daily |
| `prices_daily` | YFinance | Historical OHLCV bars | OHLCV by date | One-time bulk |

#### **🎯 Application Layer (Query-Ready)**
| Table | Purpose | Primary Use Case |
|-------|---------|------------------|
| `tickers` | Universe management | Active/inactive status tracking |
| `stock_fundamentals` | Fundamental analysis | Valuation, ratios, company health |
| `current_market_data` | Current market state | Real-time price monitoring |
| `prices_daily` | Historical analysis | Technical analysis, charting |

### **📈 Market Data Collection Systems**

#### **1. YFinance Historical Data Collection**
**Purpose**: One-time bulk download of 2 years of daily OHLCV data for all fundamentals tickers.

**Script**: `collect_historical_yfinance.py`
```bash
python collect_historical_yfinance.py
```

**Features**:
- ✅ Bulk download with threading (avoids rate limits)
- ✅ Automatic ticker format conversion (`.NSE` → `.NS`)
- ✅ Error handling and progress tracking
- ✅ Stores in `prices_daily` with `source='yf'`

**Data Flow**:
```
stock_fundamentals.ticker → YFinance API → prices_daily (OHLCV history)
```

#### **2. IBKR Current Market Data Flattening**
**Purpose**: Extract current market state from stored IBKR snapshots into structured table.

**Script**: `flatten_ibkr_market_data.py`
```bash
python flatten_ibkr_market_data.py
```

**Features**:
- ✅ Extracts 6 price fields from JSON: last, open, high, low, close, volume
- ✅ Creates `current_market_data` table automatically
- ✅ Data validation and error handling
- ✅ Summary statistics and quality checks

**Data Flow**:
```
raw_ibkr_nse.mkt_data (JSON) → current_market_data (structured)
```

#### **3. Audit & Inspection Tools**
**IBKR Market Data Audit**: `audit_mkt_json.py`
```bash
python audit_mkt_json.py  # Displays extracted market data in table format
```

**Database Health Check**: `check_progress.py`
```bash
python check_progress.py  # Shows row counts for all tables
```

### **🔄 Data Relationships & Flow**

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                         │
├─────────────────────────────────────────────────────────────────┤
│  FinanceDatabase    IBKR Fundamentals    IBKR Market     YFinance │
│  (Company Data)     (XML + Ratios)       (Snapshots)     (OHLCV) │
└─────────────────────┬─────────────────────┬─────────────┬─────────┘
                      │                     │             │
                      ▼                     ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RAW DATA LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  raw_fd_nse         raw_ibkr_nse         raw_ibkr_nse    prices_daily │
│  (JSON)             (XML + JSON)         .mkt_data       (YFinance)   │
└─────────────────────┼─────────────────────┼─────────────┼─────────────┘
                      │                     │             │
                      ▼                     ▼             │
┌─────────────────────────────────────────────────────────────────┐
│                  ANALYTICAL LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  stock_fundamentals ←───── flatten_ibkr_mega.py                 │
│  (81+ columns)                                                  │
│                                                                 │
│  current_market_data ←─── flatten_ibkr_market_data.py           │
│  (Current prices)                                               │
│                                                                 │
│  prices_daily ────────────── collect_historical_yfinance.py ────┘
│  (Historical OHLCV)                                             │
└─────────────────────────────────────────────────────────────────┘
```

### **💾 Key Data Structures**

#### **current_market_data Table**
```sql
CREATE TABLE current_market_data (
    ticker TEXT PRIMARY KEY,
    last_price NUMERIC,      -- Current/last traded price
    close_price NUMERIC,     -- Previous close
    open_price NUMERIC,      -- Today's open
    high_price NUMERIC,      -- Today's high
    low_price NUMERIC,       -- Today's low
    volume BIGINT,           -- Trading volume
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### **prices_daily Table** (Enhanced)
```sql
CREATE TABLE prices_daily (
    ticker TEXT,
    trade_date DATE,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    adj_close NUMERIC,
    volume BIGINT,
    source TEXT NOT NULL,    -- 'yf' for YFinance, 'ibkr' for IBKR
    PRIMARY KEY (ticker, trade_date, source)
);
```

### **🔧 ETL Pipeline Scripts**

| Script | Purpose | Input | Output | Frequency |
|--------|---------|-------|--------|-----------|
| `collect_historical_yfinance.py` | Bulk YFinance download | Fundamentals tickers | prices_daily | One-time |
| `flatten_ibkr_market_data.py` | IBKR market data flattening | raw_ibkr_nse.mkt_data | current_market_data | As needed |
| `flatten_ibkr_mega.py` | Fundamentals flattening | raw_ibkr_nse XML | stock_fundamentals | Quarterly |
| `flatten_fd_nse.py` | FD data flattening | raw_fd_nse | stock_fundamentals_fd | As needed |

### **📊 Data Quality & Monitoring**

- **Audit Tools**: `audit_mkt_json.py`, `audit_raw.py`, `check_progress.py`
- **Data Validation**: Automatic null checking and type validation
- **Error Handling**: Graceful failure with detailed logging
- **Progress Tracking**: Real-time progress bars and completion summaries

**This architecture ensures clean separation between current market state and historical time series data, enabling efficient querying for both real-time monitoring and technical analysis.**

## 📚 How it works
- **Universe refresh** (`screener/universe.py`):
  - Checks `db.is_market_fresh()` (7‑day TTL). If stale, pulls from FinanceDatabase and saves via `db.save_tickers()`.
  - Retrieves actionable tickers via `db.get_actionable_tickers()` (includes parole logic).
- **IBKR provider** (`data/providers.py`):
  - Qualifies contracts; on failure updates `tickers` status to `INACTIVE` with the error message.
  - Stores fundamentals in the cache.
- **YFinance provider** works as a fallback and also updates the fundamentals cache.

## 🛠️ Development notes
- The `TEST_MODE` flag is now **runtime configurable** via `--mode`.
- All modules import `config` directly, so changes to `config.TEST_MODE` are respected across the codebase.
- Logging now writes timestamps to `recent_catches.csv`.

## 📈 Future work
- Add performance benchmarks for the full NSE scan.
- Implement a web UI/dashboard.
- Extend the parole period to be configurable per market.

---
*Generated by Antigravity – your AI coding assistant.*