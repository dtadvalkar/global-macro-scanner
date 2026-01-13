
import os
import sys
import argparse
import time

# 1. Force Paper Trading Port BEFORE importing config
os.environ["IBKR_PORT"] = "7497"
print("🚀 Starting in PAPER TRADING mode (Port 7497)...")
print("   (To switch to Live, use main.py)")

# 2. Now import main and config
from config import MARKETS, TEST_MODE
from main import daily_scan

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Global Macro Scanner (Paper Trading)')
    parser.add_argument('--exchanges', type=str,
                       help='Comma-separated list of exchanges to scan (e.g., NSE,SMART).')
    parser.add_argument('--mode', type=str, choices=['test', 'live'], default='test',
                       help='Run mode: test (single run) or live (scheduled, full universe). Default: test')
    args = parser.parse_args()

    # Filter markets based on command line arguments
    filtered_markets = MARKETS.copy()
    if args.exchanges:
        # ... (same logic) ...
        reversed_map = {} # simplified for this snippet context, assuming duplication of logic

    if args.exchanges:
         requested_exchanges = [e.strip().upper() for e in args.exchanges.split(',')]
         print(f"Scanning only exchanges: {', '.join(requested_exchanges)}")
         
         exchange_to_market_key = {
            'NSE': 'nse', 'TSE': 'tsx', 'ASX': 'asx', 'SGX': 'sgx',
            'IBIS': 'xetra', 'SBF': 'sbf', 'SET': 'set', 'IDX': 'idx',
        }
         # Reset
         for k in filtered_markets: filtered_markets[k] = False
         for exc in requested_exchanges:
             k = exchange_to_market_key.get(exc)
             if k: filtered_markets[k] = True

    # Determine mode
    current_mode = args.mode.lower() if args.mode else 'test'
    
    import config
    if current_mode == 'test':
        config.TEST_MODE = True
        print("MODE: TEST (Fast scan, limited universe)")
        daily_scan(filtered_markets)
    else:
        config.TEST_MODE = False
        print("MODE: LIVE (Scheduled, full universe)")
        import schedule
        # schedule.every(30).minutes.do(lambda: daily_scan(filtered_markets))
        daily_scan(filtered_markets)
        # while True:
        #     schedule.run_pending()
        #     time.sleep(60)
