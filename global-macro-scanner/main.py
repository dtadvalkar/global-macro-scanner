#!/usr/bin/env python3
"""Global Macro Scanner"""
import time
from datetime import datetime
import schedule
import argparse

from config import CRITERIA, MARKETS, TELEGRAM
from screener.universe import get_universe
from screener.core import screen_universe
from storage.csvlogging import log_catches
from alerts.telegram import send_alerts

def daily_scan(markets=None):
    """Main execution loop"""
    print(f"\n{datetime.now()} | Global Macro Scan")
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

    print(f"Scan complete: {len(catches)} catches")
    return catches

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Global Macro Scanner')
    parser.add_argument('--exchanges', type=str,
                       help='Comma-separated list of exchanges to scan (e.g., NSE,SMART). If not provided, scans all enabled markets.')
    parser.add_argument('--mode', type=str, choices=['test', 'live'], default='test',
                       help='Run mode: test (single run) or live (scheduled, full universe). Default: test')
    args = parser.parse_args()

    # Filter markets based on command line arguments
    filtered_markets = MARKETS.copy()
    if args.exchanges:
        requested_exchanges = [e.strip().upper() for e in args.exchanges.split(',')]
        print(f"Scanning only exchanges: {', '.join(requested_exchanges)}")

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

    print("Global Macro Scanner v1.0")
    print(f"Telegram: {'Enabled' if TELEGRAM['token'] else 'Disabled'}")
    print(f"Telegram: {'Enabled' if TELEGRAM['token'] else 'Disabled'}")
    
    # Determine mode from args OR default to 'test'
    # Default is 'test' if --mode not specified
    if args.mode:
        current_mode = args.mode.lower()
    else:
        current_mode = 'test' 

    # Set global TEST_MODE used by other modules/logic if necessary
    # (Though we should pass it down, but for now we follow existing pattern)
    import config
    if current_mode == 'test':
        config.TEST_MODE = True
        print("MODE: TEST (Fast scan, limited universe)")
        daily_scan(filtered_markets)
    else:
        config.TEST_MODE = False
        print("MODE: LIVE (Scheduled, full universe)")
        # For scheduled runs - DISABLED TEMPORARILY
        # schedule.every(30).minutes.do(lambda: daily_scan(filtered_markets))
        daily_scan(filtered_markets)  # First run
        # while True:
        #     schedule.run_pending()
        #     time.sleep(60)
