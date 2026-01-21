# 🔧 Troubleshooting Guide

## Overview

Solutions to common issues encountered while using Global Market Scanner.

## Installation Issues

### Python Version Problems
**Error**: `Python version 3.10+ required`

**Solution**:
```bash
python --version
# If < 3.10, download from python.org
# Ensure python command points to Python 3.x
python3 --version
```

### Dependency Installation Fails
**Error**: `pip install` failures

**Solutions**:
```bash
# Upgrade pip
pip install --upgrade pip

# Install in virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Force reinstall
pip install --force-reinstall -r requirements.txt
```

### Database Connection Issues
**Error**: `psycopg2.OperationalError: connection failed`

**Solutions**:
```bash
# Check PostgreSQL service
# Windows: services.msc → PostgreSQL
# Linux: sudo systemctl status postgresql
# macOS: brew services list

# Verify credentials in .env
DB_NAME=your_database
DB_USER=your_username
DB_PASSWORD=correct_password

# Test connection
psql -h localhost -U your_username -d your_database
```

## Runtime Issues

### IBKR Connection Problems
**Error**: `IBKR connection failed`

**Solutions**:
```bash
# Ensure TWS is running
# Check IBKR_HOST and IBKR_PORT in .env
# Verify API is enabled in TWS
# Try different CLIENT_ID if port conflict

# Test basic connectivity
python -c "from ib_insync import IB; ib = IB(); ib.connect('127.0.0.1', 7496, clientId=1)"
```

### Rate Limiting Errors
**Error**: `Too many requests` or `Rate limit exceeded`

**Solutions**:
```python
# Adjust rate limits in config/settings.py
YF_REQUESTS_PER_MINUTE = 30  # Reduce from default
IBKR_MAX_CONCURRENT = 2      # Reduce concurrent connections

# Add delays between requests
import time
time.sleep(1)  # 1 second delay
```

### Memory Issues
**Error**: `MemoryError` or slow performance

**Solutions**:
```python
# Process in smaller batches
BATCH_SIZE = 50  # Reduce from default 100

# Increase system memory
# Close other applications
# Use SSD storage for database
```

## Data Quality Issues

### Missing Market Data
**Symptom**: Many tickers show no price data

**Solutions**:
```bash
# Check IBKR market data permissions
# Verify exchange subscriptions
# Run audit: python audit_mkt_json.py

# Re-run data collection
python scripts/etl/ibkr/flatten_ibkr_market_data.py
```

### Incomplete Fundamentals
**Symptom**: Many NULL values in stock_fundamentals

**Solutions**:
```bash
# Check raw data quality
python audit_raw.py

# Re-run flattening
python flatten_ibkr_mega.py
```

### Stale Data
**Symptom**: Old timestamps in database

**Solutions**:
```sql
-- Check last updates
SELECT table_name, last_updated FROM data_status;

-- Force refresh
TRUNCATE TABLE raw_ibkr_nse;
python main.py --exchanges NSE --mode live
```

## Performance Issues

### Slow Scans
**Symptoms**: Scans taking >30 minutes

**Optimizations**:
```python
# Reduce concurrent connections
IBKR_MAX_CONCURRENT = 2

# Increase batch sizes
BATCH_SIZE = 100

# Use SSD storage
# Add database indexes
CREATE INDEX idx_tickers_status ON tickers(status);
```

### Database Performance
**Symptoms**: Slow queries

**Solutions**:
```sql
-- Add essential indexes
CREATE INDEX idx_fundamentals_ticker ON stock_fundamentals(ticker);
CREATE INDEX idx_prices_ticker_date ON prices_daily(ticker, trade_date);

-- Vacuum and analyze
VACUUM ANALYZE;
```

## Error Messages

### `Error 200: No security definition`
**Cause**: Ticker not found or delisted

**Solution**:
```sql
-- Mark as inactive
UPDATE tickers SET status = 'INACTIVE',
                   status_message = 'No security definition'
WHERE symbol = 'INVALID_TICKER.NSE';
```

### `Error 354: Requested market data is not subscribed`
**Cause**: Missing market data permissions

**Solution**:
- Check IBKR account subscriptions
- Contact IBKR support for permissions
- Use YFinance fallback for unsubscribed markets

### `TimeoutError`
**Cause**: Network issues or slow responses

**Solutions**:
```python
# Increase timeouts in config
IBKR_TIMEOUT = 30  # Default 20
YF_TIMEOUT = 15    # Default 10

# Check internet connection
# Restart IBKR TWS
```

## Logging and Debugging

### Enable Debug Logging
```python
# In config/settings.py
import logging
logging.basicConfig(level=logging.DEBUG)

# Or add to specific script
import logging
logging.basicConfig(filename='debug.log', level=logging.DEBUG)
```

### Check Logs
```bash
# View recent logs
tail -f debug.log

# Check database status
python check_progress.py
```

### Common Debug Steps
```bash
# 1. Check system resources
top  # Linux/macOS
taskmgr  # Windows

# 2. Test individual components
python -c "from ib_insync import IB; print('IBKR import OK')"

# 3. Verify database connectivity
python -c "from config import DB_CONFIG; import psycopg2; psycopg2.connect(**DB_CONFIG); print('DB OK')"

# 4. Check configuration
python -c "from config import CRITERIA; print('Config loaded')"
```

## Getting Help

### Information to Provide
When reporting issues, include:
- Error messages (full traceback)
- System information (OS, Python version)
- Configuration (redact passwords)
- Steps to reproduce
- Database status: `python check_progress.py`

### Support Resources
- Check existing issues on GitHub
- Review this troubleshooting guide
- Test with minimal configuration
- Provide complete error logs

## Related Documentation

- **[Installation](./installation.md)** - Setup issues
- **[Usage Examples](./usage_examples.md)** - Common workflows
- **[Architecture](../developer_guide/architecture.md)** - System understanding
- **[Performance Optimization](../technical_reference/performance_optimization.md)** - Advanced tuning

---

**Status**: ✅ Complete | **Last Updated**: January 2025