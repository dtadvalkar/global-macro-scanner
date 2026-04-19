#!/usr/bin/env python3
"""
Automated Global Market Scanner
Runs intelligent scheduling for optimal market scanning times.
"""

import sys
import os
import time
from datetime import datetime
import argparse

# Add scanner root (parent of this file's directory) to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CRITERIA, MARKETS, TEST_MODE
from screener.universe import get_universe
from screener.core import screen_universe
from storage.csvlogging import log_catches
from alerts.telegram import send_alerts
from scheduler.market_scheduler import create_optimal_schedule

def scan_markets(markets_config=None):
    """
    Scan specified markets or all markets if none specified.
    Uses optimized providers with fundamental caching for efficient filtering.
    """
    start_time = datetime.now()

    # Use provided config or default to all markets
    markets_to_scan = markets_config if markets_config else MARKETS

    print(f"\n{'='*60}")
    print(f"SCAN {start_time.strftime('%H:%M:%S')} | Automated Market Scan")
    print(f"Markets: {', '.join([k.upper() for k, v in markets_to_scan.items() if v])}")
    print(f"Criteria: RVOL >={CRITERIA['min_rvol']}x OR Vol >={CRITERIA['min_volume']:,}")
    print(f"Within {CRITERIA['price_52w_low_pct']*100:.0f}% of 52w low")
    print(f"{'='*60}")

    try:
        # Build universe
        universe = get_universe(markets_to_scan)
        if not universe:
            print("No universe generated - check market configurations")
            return []

        print(f"Initial universe: {len(universe)} stocks")

        # Screen universe
        catches = screen_universe(universe, CRITERIA)

        # Log catches
        log_catches(catches)

        # Send alerts (only if not in test mode)
        if catches and not TEST_MODE:
            try:
                send_alerts(catches)
                print(f"Alerts sent: {len(catches)} catches")
            except Exception as e:
                print(f"Alert error: {e}")

        end_time = datetime.now()
        duration = end_time - start_time

        print(f"Complete: {len(catches)} catches")
        print(f"Duration: {duration.total_seconds():.1f}s")

        return catches

    except Exception as e:
        print(f"Scan failed: {e}")
        return []

def run_scheduler():
    """
    Run the intelligent scheduler.
    """
    print("Global Market Scanner - Automated Scheduling")
    print("Intelligent timing to avoid rate limiting")
    print("=" * 50)

    # Create schedule based on enabled markets
    scheduler = create_optimal_schedule(scan_markets)

    # Show schedule
    print("\n" + scheduler.get_schedule_summary())

    # Test mode?
    test_mode = TEST_MODE or os.getenv('SCHEDULER_TEST', '').lower() == 'true'

    if test_mode:
        print("\nTEST MODE: Running all scans once")
        scheduler.run_scheduler(test_mode=True)
    else:
        print("\nPRODUCTION MODE: Continuous scheduler")
        print("Press Ctrl+C to stop")
        scheduler.run_scheduler(test_mode=False)

def main():
    parser = argparse.ArgumentParser(description='Global Market Scanner')
    parser.add_argument('--test-scheduler', action='store_true',
                       help='Test scheduler (run all scans once)')
    parser.add_argument('--single-run', action='store_true',
                       help='Single scan of all enabled markets')

    args = parser.parse_args()

    if args.test_scheduler:
        os.environ['SCHEDULER_TEST'] = 'true'
        run_scheduler()
    elif args.single_run:
        print("Global Market Scanner - Single Run")
        scan_markets()
    else:
        # Default to scheduler
        run_scheduler()

if __name__ == '__main__':
    main()