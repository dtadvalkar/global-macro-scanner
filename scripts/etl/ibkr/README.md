# IBKR Data Collection Architecture

## Overview

The IBKR data collection system is now properly separated by **update frequency** and **data type**:

### 🎯 **Separation of Concerns**

| Data Type | Update Frequency | Script | Purpose |
|-----------|------------------|--------|---------|
| **Fundamentals** | Quarterly | `collect_ibkr_fundamentals.py` | ReportSnapshot, ReportRatios, ContractDetails |
| **Market Data** | Daily/Hourly | `collect_ibkr_market_data.py` | OHLCV, Volume, Bid/Ask |

### 📁 **File Organization**

```
scripts/etl/ibkr/
├── collect_ibkr_fundamentals.py      # Quarterly fundamentals collection
├── collect_ibkr_market_data.py       # Frequent market data collection
├── collect_daily_ibkr_market_data.py # Legacy daily script (updated)
├── schedule_quarterly_fundamentals.py # Quarterly scheduler
├── test_raw_ingestion.py            # Moved from yfinance/ (legacy)
└── README.md                        # This file
```

## 🚀 **Fundamentals Collection** (Quarterly)

**What it collects:**
- Company profiles (ReportSnapshot)
- Financial ratios (ReportRatios)
- Contract specifications (ContractDetails)

**When to run:**
- Quarterly (Jan, Apr, Jul, Oct)
- When new tickers are added
- After earnings seasons

**Usage:**
```bash
# Collect for specific tickers
python collect_ibkr_fundamentals.py RELIANCE.NS TCS.NS

# Collect for all tickers in investment universe
python collect_ibkr_fundamentals.py --all-universe

# Scheduled quarterly run
python schedule_quarterly_fundamentals.py --run
```

## 📊 **Market Data Collection** (Frequent)

**What it collects:**
- Real-time OHLCV data
- Volume information
- Bid/ask prices
- Market depth

**When to run:**
- Daily before screening
- Hourly during market hours
- Before any trading decisions

**Usage:**
```bash
# Update market data for specific tickers
python collect_ibkr_market_data.py RELIANCE.NS TCS.NS

# Update for all tickers in investment universe
python collect_ibkr_market_data.py --all-universe
```

## 🗂️ **Database Schema**

The `raw_ibkr_nse` table stores both types of data:

```sql
CREATE TABLE raw_ibkr_nse (
    ticker TEXT PRIMARY KEY,

    -- Fundamentals (Quarterly updates)
    xml_snapshot TEXT,           -- Company profile XML
    xml_ratios TEXT,             -- Financial ratios XML
    contract_details JSONB,      -- Contract specifications

    -- Market Data (Frequent updates)
    mkt_data JSONB,              -- OHLCV, volume, bid/ask

    last_updated TIMESTAMP
);
```

## 🔄 **Data Flow**

```
FinanceDatabase API → raw_fd_nse (universe)
    ↓
Quarterly: IBKR Fundamentals API → ibkr_fundamentals (XML data)
    ↓
Daily: IBKR Market Data API → ibkr_market_data (JSON snapshots)
    ↓
Flattening → current_market_data (structured data ready for criteria)
    ↓
Screening Engine → Uses current_market_data (STORED FRESH DATA)
    ↓
Telegram Alerts → Criteria matches sent to users
```

**Key Improvements:**
- ✅ **Separate Tables**: Fundamentals vs Market Data in dedicated tables
- ✅ **Stored Fresh Data**: Screening uses `current_market_data` (collected same pipeline)
- ✅ **No API Calls During Screening**: Faster, more reliable, cost-effective
- ✅ **Clean Architecture**: Each step has clear input/output

## 📅 **Scheduling Recommendations**

### **Fundamentals (Quarterly)**
- **Frequency**: Every 3 months
- **Timing**: Start of quarter (1st of Jan/Apr/Jul/Oct)
- **Trigger**: `schedule_quarterly_fundamentals.py`
- **Runtime**: 30-60 minutes for ~2000 tickers

### **Market Data (Daily/Hourly)**
- **Frequency**: Daily (before screening) or hourly (during market hours)
- **Timing**: 9:00 AM IST (market open) to 3:30 PM IST (market close)
- **Trigger**: Cron job or manual execution
- **Runtime**: 5-15 minutes for ~400 tickers

## 🛠️ **Error Handling & Recovery**

### **Failed Fundamentals Collection**
- Script logs specific failures per ticker
- Can retry individual tickers
- Separate from market data failures

### **Failed Market Data Collection**
- Often due to network issues or IBKR connectivity
- Can retry immediately (market data is volatile)
- Doesn't affect fundamentals data integrity

## 🔧 **Migration Notes**

### **From Legacy System**
- `test_raw_ingestion.py` moved from `yfinance/` folder
- Fundamentals and market data now separated
- Database schema unchanged (backward compatible)

### **Benefits of New Architecture**
- ✅ **Efficiency**: Only collect what changed
- ✅ **Reliability**: Fundamentals failures don't break market data
- ✅ **Performance**: Faster market data updates
- ✅ **Maintainability**: Clear separation of concerns
- ✅ **Cost**: Reduced API calls (fundamentals are expensive)

## 🎯 **Usage Examples**

### **Initial Setup (One-time)**
```bash
# 1. Populate fundamentals for all universe tickers
python scripts/etl/ibkr/collect_ibkr_fundamentals.py --all-universe

# 2. Process fundamentals into stock_fundamentals
python scripts/etl/ibkr/flatten_ibkr_final.py

# 3. Collect initial market data
python scripts/etl/ibkr/collect_ibkr_market_data.py --missing-market-data

# 4. Flatten for screening
python scripts/etl/ibkr/flatten_ibkr_market_data.py
```

### **Daily Operations (Use main.py)**
```bash
# Complete pipeline: collect → flatten → screen → alert
python main.py

# Breakdown of what main.py does:
# 1. Collect fresh market data → ibkr_market_data
# 2. Flatten structured data → current_market_data
# 3. Screen using stored data (FAST, no API calls)
# 4. Send alerts for matches
```

### **Maintenance Operations**
```bash
# Quarterly: Update fundamentals only
python scripts/etl/ibkr/schedule_quarterly_fundamentals.py --run

# Manual: Update specific market data
python scripts/etl/ibkr/collect_ibkr_market_data.py RELIANCE.NS TCS.NS
```

This architecture ensures efficient data collection while maintaining data integrity and reliability.