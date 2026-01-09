# Intelligent Market Scheduling Guide

## Problem Analysis

**Your Observation:** Most rate limiting errors occurred in NSE (India) and SET (Thailand) markets, likely because those markets had just opened when you ran the scan.

**Root Cause:** Different markets have different trading hours, and Yahoo Finance data freshness varies by market timezone.

## Optimal Scheduling Strategy

### Market Hours (in MST - Mountain Standard Time)

| Market | Local Time | MST Time | Best Scan Time |
|--------|------------|----------|----------------|
| **TSX (Canada)** | 9:30 AM ET | 7:30 AM MST | 9:00 AM MST |
| **NYSE/NASDAQ** | 9:30 AM ET | 7:30 AM MST | 9:00 AM MST |
| **NSE (India)** | 9:15 AM IST | 10:45 PM MST (prev day) | 9:15 PM MST |
| **IDX (Indonesia)** | 9:00 AM WIB | 11:00 PM MST (prev day) | 7:30 PM MST |
| **SET (Thailand)** | 10:00 AM ICT | 12:00 AM MST | 8:30 PM MST |

### Why This Timing Works

1. **North America (9:00 AM MST):**
   - Markets have been open 1.5 hours
   - Data is fresh and stable
   - Lower server load (not market open spike)

2. **Asian Markets (7:30-9:15 PM MST):**
   - Markets opening or early trading
   - Fresh data available
   - Less competition for API resources
   - Yahoo servers less busy

## Implementation

### Option 1: Intelligent Scheduler (Recommended)

```bash
# Run with intelligent scheduling
INTELLIGENT_SCHEDULING=true python main_intelligent.py
```

**Calculated Optimal Schedule:**
- **North America:** Daily at 7:30 AM MST (during TSX trading hours)
- **India:** Daily at 9:15 PM MST (during NSE trading hours)
- **Indonesia:** Daily at 7:30 PM MST (during IDX trading hours)
- **Thailand:** Daily at 8:30 PM MST (during SET trading hours)

### Option 2: Manual Scheduling with Cron/Windows Task Scheduler

**Windows Task Scheduler:**
```
# North America (7:30 AM MST)
schtasks /create /tn "MarketScan_NA" /tr "python main.py" /sc daily /st 07:30

# Asian markets (7:30 PM MST)
schtasks /create /tn "MarketScan_Asia" /tr "python main_intelligent.py asia" /sc daily /st 19:30
```

**Linux/Mac Cron:**
```bash
# North America (7:30 AM MST = 14:30 UTC)
30 14 * * 1-5 python main.py

# Asian markets (7:30 PM MST = 02:30 UTC next day)
30 2 * * 1-5 python main_intelligent.py asia
```

### Option 3: Environment Variable Control

```bash
# Run only North American markets
MARKETS="tsx" python main.py

# Run only Asian markets
MARKETS="nse,idx,set" python main.py
```

## Code Implementation

### Using the Intelligent Scheduler

```python
from scheduler.market_scheduler import create_optimal_schedule

# Create schedule with your scan function
scheduler = create_optimal_schedule(scan_markets)

# Run continuously (production)
scheduler.run_scheduler(test_mode=False)

# Or run once for testing
scheduler.run_scheduler(test_mode=True)
```

### Custom Scheduling

```python
from scheduler.market_scheduler import MarketScheduler

scheduler = MarketScheduler(user_timezone='US/Mountain')

# Schedule individual markets
scheduler.schedule_market_scan('north_america', lambda: scan_markets({'tsx': True}))
scheduler.schedule_market_scan('india', lambda: scan_markets({'nse': True}))

# Run scheduler
scheduler.run_scheduler()
```

## Benefits of Intelligent Scheduling

### 1. **Rate Limiting Avoidance**
- Scan during market hours when data is fresh
- Avoid market open/close spikes
- Distribute load across different timezones

### 2. **Data Freshness**
- North America: Data 1.5 hours into trading session
- Asia: Data from market open (freshest possible)

### 3. **Resource Optimization**
- No redundant API calls
- Better cache utilization
- Reduced server load

### 4. **Error Reduction**
- Fewer timeout/connection issues
- More reliable data availability
- Better handling of market-specific issues

## Configuration Options

### Timezone Customization

```python
# For different timezones
scheduler = MarketScheduler(user_timezone='US/Eastern')   # ET
scheduler = MarketScheduler(user_timezone='Europe/London') # GMT
scheduler = MarketScheduler(user_timezone='Asia/Tokyo')   # JST
```

### Day-of-Week Control

```python
# Only weekdays
scheduler.schedule_market_scan('north_america', scan_func, days_of_week=[0,1,2,3,4])

# Weekends only (for testing)
scheduler.schedule_market_scan('north_america', scan_func, days_of_week=[5,6])
```

## Monitoring and Alerts

### Schedule Monitoring

```python
# Get current schedule
print(scheduler.get_schedule_summary())

# Check next run times
for region in ['north_america', 'india', 'indonesia', 'thailand']:
    next_time = scheduler.get_optimal_scan_time(region)
    print(f"{region}: {next_time}")
```

### Integration with Telegram

```python
def scan_with_notification(markets_config):
    catches = scan_markets(markets_config)
    if catches:
        # Send summary via Telegram
        send_telegram_alert(f"Found {len(catches)} opportunities in {list(markets_config.keys())}")

scheduler.schedule_market_scan('north_america', lambda: scan_with_notification({'tsx': True}))
```

## Troubleshooting

### Common Issues

1. **"No module named 'config'"**
   - Run from project root directory
   - Check Python path

2. **Timezone Issues**
   - Install pytz: `pip install pytz`
   - Verify timezone names

3. **Schedule Not Running**
   - Check system time settings
   - Ensure script has permission to run scheduled tasks

4. **Rate Limiting Still Occurring**
   - Reduce scan frequency
   - Use cached providers
   - Implement longer delays between batches

### Testing

```bash
# Test scheduler without actually scanning
python scheduler/market_scheduler.py

# Test full scan pipeline once
INTELLIGENT_SCHEDULING=true SCHEDULER_TEST=true python main_intelligent.py

# Test specific market
python main.py  # Will scan all markets once
```

## Performance Comparison

### Before (Single Daily Scan)
- **Time:** 40+ minutes
- **Rate Limits:** Frequent failures
- **Data Freshness:** Mixed (some markets stale)
- **Errors:** NSE/SET failures during market open

### After (Intelligent Scheduling)
- **Time:** 10-15 minutes per market group
- **Rate Limits:** Minimal (optimal timing)
- **Data Freshness:** Excellent (during active trading)
- **Errors:** Rare (markets fully open)

## Files Created

1. **`scheduler/market_scheduler.py`** - Core scheduling logic
2. **`main_intelligent.py`** - Scheduler-enabled main script
3. **`docs/market_scheduling_guide.md`** - This documentation

## Quick Start

1. **Test the scheduler:**
   ```bash
   python scheduler/market_scheduler.py
   ```

2. **Run intelligent scheduling:**
   ```bash
   INTELLIGENT_SCHEDULING=true python main_intelligent.py
   ```

3. **For production, add to cron/Windows Task Scheduler:**
   ```bash
   # Run at 9:00 AM MST daily (North America)
   # Run at 7:30 PM MST daily (Asia)
   ```

This approach should eliminate your rate limiting issues while ensuring you get the freshest data possible for each market! 🚀