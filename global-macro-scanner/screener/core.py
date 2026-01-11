from data.providers import OptimizedYFinanceProvider, IBKRProvider, IBKRScannerProvider
from data.cache_manager import FundamentalCacheManager
from config import DATA_SOURCE, IBKR_CONFIG
import asyncio
import time

def prefilter_universe_by_fundamentals(universe, criteria):
    """
    Pre-filter universe using cached fundamentals to avoid unnecessary API calls.
    Returns only tickers that should be scanned based on basic criteria.
    """
    if not universe:
        return []

    fundamentals_cache = FundamentalCacheManager()
    viable_tickers = []

    print(f"Prefiltering {len(universe)} tickers using fundamentals cache...")

    for ticker in universe:
        can_skip, reason = fundamentals_cache.can_skip_by_fundamentals(ticker, criteria)
        if can_skip:
            # Skip this ticker - doesn't meet basic criteria
            continue
        else:
            viable_tickers.append(ticker)

    efficiency = f"({len(viable_tickers)}/{len(universe)} viable)"
    print(f"Prefiltering complete {efficiency}")

    return viable_tickers

def screen_universe(universe, criteria):
    """Multi-provider fishing net: Option B (Scanner) -> Option A (Bulk)"""

    # Pre-filter universe using fundamentals cache to reduce API calls
    filtered_universe = prefilter_universe_by_fundamentals(universe, criteria)
    if not filtered_universe:
        print("No tickers passed fundamental prefiltering")
        return []
    
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

        # If we found "Hot" tickers, prioritize them for a deep scan
        if hot_tickers:
            # Filter hot tickers by fundamentals too
            unique_hot = list(set(hot_tickers))
            filtered_hot = [t for t in unique_hot if not FundamentalCacheManager().can_skip_by_fundamentals(t, criteria)[0]]

            if filtered_hot:
                print(f"Running deep analysis on {len(filtered_hot)} filtered server-side candidates...")
                ib_bulk = IBKRProvider(IBKR_CONFIG['host'], IBKR_CONFIG['port'], IBKR_CONFIG['client_id'])
                results = ib_bulk.get_market_data(filtered_hot, criteria)
            else:
                print("All hot tickers filtered out by fundamentals")
                results = []
            if results:
                print(f"Option B successful: {len(results)} confirmed catches.")
                return results
        else:
            print("Option B (Scanner) found no tickers.")

    # 2. Option A Fallback: Bulk Scan on the full Universe (Reliable & Thorough)
    if DATA_SOURCE in ['ibkr', 'auto']:
        print("Option B gave no results. Attempting Option A (Bulk Historical Scan on full universe)...")
        ib_bulk = IBKRProvider(IBKR_CONFIG['host'], IBKR_CONFIG['port'], IBKR_CONFIG['client_id'])
        results = ib_bulk.get_market_data(filtered_universe, criteria)
        if results:
            return results

    # 3. Last Resort: Optimized YFinance with caching and parallel processing
    print("Final Fallback: Optimized Scan (yfinance with caching)...")
    provider = OptimizedYFinanceProvider()
    return provider.get_market_data(universe, criteria)
