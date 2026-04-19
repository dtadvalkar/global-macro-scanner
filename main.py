#!/usr/bin/env python3
"""
Global Macro Scanner - Daily Orchestration Script

This is the main daily pipeline that:
1. Collects fresh IBKR market data → ibkr_market_data (raw JSON)
2. Flattens data into current_market_data (structured, ready for criteria)
3. Validates data freshness (< 24 hours)
4. Runs screener using STORED data (no API calls) → alerts if criteria met

ARCHITECTURE:
- Fresh data collection + storage (steps 1-2)
- Fast screening using stored data (steps 3-4)
- Separates data collection from screening for reliability

USAGE:
    python main.py                    # Full daily pipeline (recommended)
    python main.py --mode test        # Test mode (skip alerts)
    python main.py --skip-collection  # Skip data collection, just screen
"""

import os
import time
import asyncio
import subprocess
import sys
import io
from datetime import datetime, timedelta
import argparse
import json

from config import CRITERIA, MARKETS, TELEGRAM, DB_CONFIG, TEST_MODE
from db import get_db
from screener.universe import get_universe
from screener.core import screen_universe
from storage.csvlogging import log_catches
from alerts.telegram import send_alerts

# Force UTF-8 encoding for stdout to support emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_data_freshness():
    """Check if data is fresh enough for screening"""
    print("[SCAN] Checking data freshness...")

    try:
        db = get_db()

        # Check current_market_data freshness (should be < 24 hours old)
        result = db.query("""
            SELECT COUNT(*),
                   MAX(last_updated),
                   EXTRACT(EPOCH FROM (NOW() AT TIME ZONE 'utc' - MAX(last_updated)))/3600 as hours_old
            FROM current_market_data
        """, fetch='one')

        if result:
            current_count, latest_update, hours_old = result
        else:
            current_count, latest_update, hours_old = 0, None, None

        print(f"   📊 Current market data: {current_count} records")
        if latest_update:
            print(f"   TIME: {latest_update.strftime('%Y-%m-%d %H:%M UTC')}")
            print(f"   AGE: {hours_old:.1f} hours old")

            if hours_old > 24:
                print("   ⚠️  WARNING: Current market data is stale (>24 hours)")
                return False
        else:
            print("   ❌ No current market data found")
            return False

        # Check prices_daily freshness (historical data should exist)
        historical_count = db.get_price_data_count()
        print(f"   DATA: Historical data: {historical_count} records")

        if current_count > 0 and historical_count > 0:
            print("   [OK] Data freshness check passed")
            return True
        else:
            print("   ❌ Insufficient data for screening")
            return False

    except Exception as e:
        print(f"   ❌ Error checking data freshness: {e}")
        return False

def run_ibkr_collection():
    """Run the daily IBKR market data collection"""
    print("\n🏦 Starting IBKR Market Data Collection...")
    print("💡 Note: This will run for 10-20 minutes. Let it complete!")

    try:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        
        # Run the collection script directly
        result = subprocess.run([
            sys.executable, "scripts/etl/ibkr/collect_daily_ibkr_market_data.py"
        ], cwd=".", env=env)

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Failed to run IBKR collection: {e}")
        return False

def run_ibkr_flattening():
    """Run the IBKR data flattening script"""
    print("\n🔄 Starting IBKR Data Flattening...")

    try:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        
        # Run the flattening script with captured output
        # Use errors='replace' to safely handle emojis even if the pipe encoding is mismatched
        result = subprocess.run([
            sys.executable, "scripts/etl/ibkr/flatten_ibkr_market_data.py"
        ], capture_output=True, text=True, cwd=".", env=env, errors='replace')

        print("IBKR Flattening Output:")
        print(result.stdout)

        if result.stderr:
            print("IBKR Flattening Errors:")
            print(result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Failed to run IBKR flattening: {e}")
        return False

def daily_screen(markets=None):
    """Main screening execution after data collection"""
    print(f"\n🎯 {datetime.now()} | Global Macro Screen")
    print(f"Target: RVOL >={CRITERIA['min_rvol']}x OR Volume >={CRITERIA['min_volume']:,}, within {CRITERIA['price_52w_low_pct']*100:.0f}% of 52w low")

    # Use provided markets or default to MARKETS
    scan_markets = markets if markets is not None else MARKETS

    # Build universe + screen
    universe = get_universe(scan_markets)
    catches = screen_universe(universe, CRITERIA, scan_markets)

    # Log + alert
    log_catches(catches)
    if catches and not TEST_MODE:
        send_alerts(catches)

    print(f"[OK] Scan complete: {len(catches)} catches found")
    return catches

async def run_daily_pipeline(filtered_markets, skip_collection=False, skip_flattening=False):
    """Run the complete daily pipeline"""

    print("="*80)
    print("🚀 GLOBAL MACRO SCANNER - DAILY PIPELINE")
    print("="*80)
    print(f"📅 {datetime.now()}")
    print(f"🎯 Markets: {', '.join([k.upper() for k, v in filtered_markets.items() if v])}")
    print(f"📊 Telegram: {'Enabled' if TELEGRAM['token'] else 'Disabled'}")
    print("="*80)

    pipeline_success = True

    # STEP 1: IBKR Market Data Collection
    if not skip_collection:
        print("\n📥 STEP 1: IBKR Market Data Collection")
        if run_ibkr_collection():
            print("✅ IBKR collection completed successfully")
        else:
            print("❌ IBKR collection failed")
            pipeline_success = False
    else:
        print("\n⏭️  STEP 1: Skipping IBKR collection (--skip-collection)")

    # STEP 2: IBKR Data Flattening
    if not skip_flattening and pipeline_success:
        print("\n🔄 STEP 2: IBKR Data Flattening")
        if run_ibkr_flattening():
            print("✅ IBKR flattening completed successfully")
        else:
            print("❌ IBKR flattening failed")
            pipeline_success = False
    else:
        print("\n⏭️  STEP 2: Skipping IBKR flattening (--skip-flattening)")

    # STEP 3: Data Freshness Validation
    print("\n🔍 STEP 3: Data Freshness Validation")
    if check_data_freshness():
        print("✅ Data freshness check passed")
    else:
        print("❌ Data freshness check failed - screening may be unreliable")
        if not TEST_MODE:
            print("⚠️  Continuing with screening anyway (use --mode test to skip)")
            pipeline_success = False

    # STEP 4: Market Screening & Alerting (Using Stored Flattened Data)
    if pipeline_success:
        print("\n🎯 STEP 4: Market Screening & Alerting")
        print("   Using fresh market data from current_market_data table")
        catches = daily_screen(filtered_markets)

        print("\n" + "="*80)
        print("🎉 DAILY PIPELINE COMPLETE")
        print("="*80)
        print(f"📊 Found {len(catches)} trading opportunities")

        if catches:
            print("🚨 Alerts sent!" if not TEST_MODE else "🧪 Test mode - no alerts sent")
        else:
            print("📭 No opportunities found today")

        return len(catches)
    else:
        print("\n" + "="*80)
        print("⚠️  DAILY PIPELINE INCOMPLETE")
        print("="*80)
        print("❌ Pipeline failed - check errors above")
        return -1

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Global Macro Scanner - Daily Pipeline')
    parser.add_argument('--exchanges', type=str,
                       help='Comma-separated list of exchanges to scan (e.g., NSE,SMART). If not provided, scans all enabled markets.')
    parser.add_argument('--mode', type=str, choices=['test', 'live'], default='test',
                       help='Run mode: test (single run, no alerts) or live (with alerts). Default: test')
    parser.add_argument('--skip-collection', action='store_true',
                       help='Skip IBKR data collection step')
    parser.add_argument('--skip-flattening', action='store_true',
                       help='Skip IBKR data flattening step')
    args = parser.parse_args()

    # Filter markets based on command line arguments
    filtered_markets = MARKETS.copy()
    if args.exchanges:
        requested_exchanges = [e.strip().upper() for e in args.exchanges.split(',')]
        print(f"Scanning only exchanges: {requested_exchanges}")

        # Map exchange codes to market keys (based on config/markets.py)
        exchange_to_market_key = {
            'NSE': 'nse',      # India NSE
            'TSE': 'tsx',      # Canada TSE
            'ASX': 'asx',      # Australia ASX
            'SGX': 'sgx',      # Singapore SGX
            'IBIS': 'xetra',   # Germany IBIS/XETRA
            'SBF': 'sbf',      # France SBF
            'SET': 'set',      # Thailand SET (YFinance only)
            'IDX': 'idx',      # Indonesia IDX (YFinance only)
        }

        # Disable all markets first
        for key in filtered_markets:
            filtered_markets[key] = False

        # Enable only requested markets
        enabled_count = 0
        unsupported_exchanges = []
        for exchange in requested_exchanges:
            market_key = exchange_to_market_key.get(exchange.upper())
            if market_key and market_key in filtered_markets:
                filtered_markets[market_key] = True
                enabled_count += 1
            else:
                unsupported_exchanges.append(exchange)

        if unsupported_exchanges:
            print(f"Warning: These exchanges are not supported or not configured: {', '.join(unsupported_exchanges)}")
            print("Available exchanges: NSE, TSE, ASX, SGX, IBIS, SBF, SET, IDX")

        if enabled_count == 0:
            print("No valid exchanges found. Available exchanges:")
            available_exchanges = sorted(exchange_to_market_key.keys())
            print(", ".join(available_exchanges))
            exit(1)
    else:
        enabled_exchanges = [k.upper() for k, v in filtered_markets.items() if v]
        if enabled_exchanges:
            print(f"Scanning all enabled markets: {', '.join(enabled_exchanges)}")
        else:
            print("No markets are currently enabled in config/markets.py")

    # Set global TEST_MODE
    import config
    if args.mode == 'test':
        config.TEST_MODE = True
        print("🧪 MODE: TEST (No alerts, limited data)")
    else:
        config.TEST_MODE = False
        print("🏃 MODE: LIVE (Production with alerts)")

    print(f"📊 Telegram: {'Enabled' if TELEGRAM['token'] else 'Disabled'}")

    # Run the daily pipeline
    asyncio.run(run_daily_pipeline(filtered_markets, args.skip_collection, args.skip_flattening))