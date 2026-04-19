# 📋 Usage Examples

## Overview

Common usage patterns and workflows for Global Market Scanner.

## Basic Scanning

### NSE Full Scan
```bash
# Scan all NSE stocks
python main.py --exchanges NSE --mode live
```

### Test Mode (Limited Dataset)
```bash
# Scan top 200 NSE stocks for testing
python main.py --exchanges NSE --mode test
```

### Multiple Exchanges
```bash
# Scan multiple exchanges
python main.py --exchanges NSE,Australia,Singapore
```

## Market Data Collection

### Historical Data Download
```bash
# Download 2 years of YFinance data for all tracked tickers
python scripts/etl/yfinance/collect_historical_yfinance.py
```

### Current Market Data Update
```bash
# Flatten latest IBKR market data
python scripts/etl/ibkr/flatten_ibkr_market_data.py
```

## Data Analysis Workflows

### Check Database Status
```bash
python check_progress.py
```

### Audit Market Data
```bash
python audit_mkt_json.py
```

### Filter Results
```bash
# View scan results
cat recent_catches.csv
```

## Advanced Usage

### Custom Criteria
```python
# Modify config/criteria.py for custom filters
# Example: Adjust RSI thresholds
RSI_MIN = 25  # Instead of default 20
RSI_MAX = 40  # Instead of default 45
```

### Database Queries
```sql
-- View active tickers
SELECT symbol, market, status FROM tickers WHERE status = 'ACTIVE';

-- Check market data quality
SELECT COUNT(*) FROM current_market_data WHERE last_price > 0;

-- Analyze scan results
SELECT symbol, price, pct_from_low FROM recent_catches
ORDER BY pct_from_low ASC LIMIT 10;
```

## Automation

### Scheduled Scans
```bash
# Windows Task Scheduler
schtasks /create /tn "MarketScan" /tr "python main.py --exchanges NSE" /sc daily /st 09:00

# Linux cron
0 9 * * 1-5 python /path/to/main.py --exchanges NSE
```

### Telegram Notifications
Configure in `.env`:
```bash
TELEGRAM_TOKEN=your_bot_token
CHAT_ID=your_chat_id
```

## Performance Optimization

### Rate Limiting
```python
# Adjust in config/settings.py
YF_REQUESTS_PER_MINUTE = 50  # Default: 100
IBKR_MAX_CONCURRENT = 3      # Default: 5
```

### Database Tuning
```sql
-- Create indexes for better performance
CREATE INDEX idx_tickers_status ON tickers(status);
CREATE INDEX idx_prices_date ON prices_daily(trade_date);
```

## Integration Examples

### Export to CSV
```python
import pandas as pd
from config import DB_CONFIG
import psycopg2

conn = psycopg2.connect(**DB_CONFIG)
df = pd.read_sql("SELECT * FROM stock_fundamentals", conn)
df.to_csv('fundamentals_export.csv', index=False)
```

### API Integration
```python
from data.providers import IBKRProvider

provider = IBKRProvider()
results = provider.get_market_data(['RELIANCE.NSE', 'TCS.NSE'], criteria)
```

## Related Documentation

- **[Getting Started](./getting_started.md)** - Basic setup
- **[Installation](./installation.md)** - Complete setup
- **[Troubleshooting](./troubleshooting.md)** - Fix issues
- **[Architecture](../developer_guide/architecture.md)** - System design

---