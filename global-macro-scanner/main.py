#!/usr/bin/env python3
"""Global Macro Scanner"""
import time
from datetime import datetime
import schedule

from config import CRITERIA, MARKETS, TEST_MODE, TELEGRAM
from screener.universe import get_universe
from screener.core import screen_universe
from storage.csvlogging import log_catches
from alerts.telegram import send_alerts

def daily_scan():
    """Main execution loop"""
    print(f"\n{datetime.now()} | Global Macro Scan")
    print(f"Target: RVOL >={CRITERIA['min_rvol']}x OR Volume >={CRITERIA['min_volume']:,}, within {CRITERIA['price_52w_low_pct']*100:.0f}% of 52w low")
    
    # Build universe + screen
    universe = get_universe(MARKETS)
    catches = screen_universe(universe, CRITERIA)
    
    # Log + alert
    log_catches(catches)
    if catches and not TEST_MODE:
        send_alerts(catches)
    
    print(f"Scan complete: {len(catches)} catches")
    return catches

if __name__ == '__main__':
    print("Global Macro Scanner v1.0")
    print(f"Telegram: {'Enabled' if TELEGRAM['token'] else 'Disabled'}")
    print(f"TEST_MODE: {TEST_MODE}")
    
    # Single run or scheduler
    if TEST_MODE:
        daily_scan()
    else:
        schedule.every(30).minutes.do(daily_scan)
        daily_scan()  # First run
        while True:
            schedule.run_pending()
            time.sleep(60)
