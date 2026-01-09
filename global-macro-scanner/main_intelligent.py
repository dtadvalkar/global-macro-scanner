#!/usr/bin/env python3
"""
Intelligent Market Scanner with Optimal Scheduling
Runs different market scans at optimal times to avoid rate limiting.
"""

import time
from datetime import datetime
from config import CRITERIA, MARKETS, TEST_MODE
from screener.universe import get_universe
from screener.core import screen_universe
from storage.csvlogging import log_catches
from alerts.telegram import send_alerts
from scheduler.market_scheduler import create_optimal_schedule

def scan_markets(markets_config=None):
    """
    Scan specified markets or all markets if none specified.

    Args:
        markets_config: Dict of market toggles (e.g., {'nse': True, 'tsx': True})
    """
    # Use provided config or default to all markets
    markets_to_scan = markets_config if markets_config else MARKETS

    print(f"\n{'='*60}")
    print(f"🕐 {datetime.now()} | Market Scan")
    print(f"🎯 Markets: {', '.join([k.upper() for k, v in markets_to_scan.items() if v])}")
    print(f"🎯 Criteria: RVOL ≥{CRITERIA['min_rvol']}x OR Vol ≥{CRITERIA['min_volume']:,}")
    print(f"🎯 Within {CRITERIA['price_52w_low_pct']*100:.0f}% of 52w low")
    print(f"{'='*60}")

    # Build universe for specified markets
    universe = get_universe(markets_to_scan)

    # Screen universe
    catches = screen_universe(universe, CRITERIA)

    # Log + alert (only if not in test mode)
    log_catches(catches)
    if catches and not TEST_MODE:
        send_alerts(catches)

    print(f"✅ Scan complete: {len(catches)} catches found")
    return catches

def run_intelligent_scheduler():
    """
    Run the intelligent scheduler that scans markets at optimal times.
    """
    print("🚀 Global Macro Scanner - Intelligent Scheduling Mode")
    print("📅 Scans scheduled at optimal market times to avoid rate limiting")
    print()

    # Create optimal schedule
    scheduler = create_optimal_schedule(scan_markets)

    # Show current schedule
    print("\n" + scheduler.get_schedule_summary())
    print()

    # Determine if we should run in test mode
    test_mode = TEST_MODE or os.getenv('SCHEDULER_TEST', '').lower() == 'true'

    if test_mode:
        print("🧪 TEST MODE: Running all scans once for testing")
        scheduler.run_scheduler(test_mode=True)
    else:
        print("🏃 PRODUCTION MODE: Running continuous scheduler")
        print("💡 Press Ctrl+C to stop")
        scheduler.run_scheduler(test_mode=False)

if __name__ == '__main__':
    import os

    # Check if intelligent scheduling is requested
    if os.getenv('INTELLIGENT_SCHEDULING', '').lower() == 'true':
        run_intelligent_scheduler()
    else:
        # Original behavior - scan all markets once
        print("🚀 Global Macro Scanner v1.0 - Single Run Mode")
        scan_markets()