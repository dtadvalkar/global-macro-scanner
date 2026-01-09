from data.providers import YFinanceProvider, IBKRProvider, IBKRScannerProvider
from config import DATA_SOURCE, IBKR_CONFIG
import asyncio
import time

def screen_universe(universe, criteria):
    """Multi-provider fishing net: Option B (Scanner) -> Option A (Bulk)"""
    
    # 1. Try Option B: IBKR Server-Side Scanner (Fast & Directed)
    if DATA_SOURCE in ['ibkr', 'auto']:
        print(f"Option B: Connecting to IBKR on {IBKR_CONFIG['host']}:{IBKR_CONFIG['port']}...")
        scanner = IBKRScannerProvider(IBKR_CONFIG['host'], IBKR_CONFIG['port'], IBKR_CONFIG['client_id'])
        
        # 🧪 Expansion Hub: Just add new countries here!
        # Format: (Instrument, LocationCode, ScanCode)
        OPTION_B_SCANS = [
            ('STK', 'STK.US.MAJOR', 'MOST_ACTIVE'),        # US Major
            ('STOCK.NA', 'STK.NA', 'MOST_ACTIVE'),        # Canada (TSE/Venture)
            ('STOCK.HK', 'STK.HK.NSE', 'MOST_ACTIVE'),    # India (NSE)
        ]
        
        hot_tickers = []
        for inst, loc, scan in OPTION_B_SCANS:
            try:
                print(f"Requesting scan: {loc} | {scan}...")
                found = scanner.get_scanner_results(inst, loc, scan)
                if found:
                    print(f"  Found {len(found)} candidates from {loc} Scanner.")
                    hot_tickers.extend(found)
                else:
                    print(f"  ⚪ No results from {loc} Scanner.")
                
                # Small sleep to allow IBKR to clear the connection
                time.sleep(1)
            except Exception as e:
                print(f"  Warning: Scanner Option B failed for {loc}: {e}")
                time.sleep(2)

        # If we found "Hot" tickers, we prioritize them for a deep scan
        if hot_tickers:
            print(f"Running deep analysis on {len(hot_tickers)} server-side candidates...")
            ib_bulk = IBKRProvider(IBKR_CONFIG['host'], IBKR_CONFIG['port'], IBKR_CONFIG['client_id'])
            # We filter out any duplicates from the scanner
            unique_hot = list(set(hot_tickers))
            results = ib_bulk.get_market_data(unique_hot, criteria)
            if results:
                print(f"Option B successful: {len(results)} confirmed catches.")
                return results
        else:
            print("Option B (Scanner) found no tickers.")

    # 2. Option A Fallback: Bulk Scan on the full Universe (Reliable & Thorough)
    if DATA_SOURCE in ['ibkr', 'auto']:
        print("Option B gave no results. Attempting Option A (Bulk Historical Scan on full universe)...")
        ib_bulk = IBKRProvider(IBKR_CONFIG['host'], IBKR_CONFIG['port'], IBKR_CONFIG['client_id'])
        results = ib_bulk.get_market_data(universe, criteria)
        if results:
            return results

    # 3. Last Resort: yfinance
    print("Final Fallback: Standard Scan (yfinance)...")
    provider = YFinanceProvider()
    return provider.get_market_data(universe, criteria)
