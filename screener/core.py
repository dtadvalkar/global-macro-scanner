from data.providers import OptimizedYFinanceProvider, IBKRProvider, IBKRScannerProvider
from config import DATA_SOURCE, IBKR_CONFIG
import asyncio
import time

def screen_universe(universe, criteria, markets=None):
    """Multi-provider fishing net: Option B (Scanner) -> Option A (Bulk)"""
    
    # Default to all markets if not provided (though practically usually provided)
    if markets is None:
        from config import MARKETS
        markets = MARKETS

    # 1. Try Option B: IBKR Server-Side Scanner (Fast & Directed)
    # Only run if explicitly enabled and supported
    if DATA_SOURCE in ['ibkr', 'auto']:
        print(f"Option B: Connecting to IBKR on {IBKR_CONFIG['host']}:{IBKR_CONFIG['port']}...")
        scanner = IBKRScannerProvider(IBKR_CONFIG['host'], IBKR_CONFIG['port'], IBKR_CONFIG['client_id'])
        
        # 🧪 Expansion Hub: Just add new countries here!
        # Format: (Instrument, LocationCode, ScanCode, MarketKey, IBKRExchange)
        # IBKRExchange must match a MARKET_REGISTRY key in config/markets.py so that
        # ibkr_to_yfinance() applies the correct per-exchange symbol transformation.
        # Location codes are IBKR TWS Scanner API codes — if a scan returns 0 results
        # verify the location code against live TWS scanner parameters.
        # Location codes verified via reqScannerParameters() on 2026-04-22.
        # LSE / TADAWUL are access-restricted in IBKR's scanner XML — if they
        # return 0 results at runtime, that's a market-data subscription gap.
        # JSE has no scanner location code at all (South Africa absent from the
        # scanner location tree) — seed JSE universe from a static curated list.
        ALL_SCANS = [
            ('STK',      'STK.HK.SEHK',    'MOST_ACTIVE', 'sehk',    'SEHK'),     # Hong Kong [IBKR free]
            ('STK',      'STK.EU.LSE',     'MOST_ACTIVE', 'lse',     'LSE'),      # UK LSE    [IBKR restricted]
            ('STK',      'STK.ME.TADAWUL', 'MOST_ACTIVE', 'tadawul', 'TADAWUL'),  # Saudi     [IBKR restricted]
            ('STOCK.NA', 'STK.NA',    'MOST_ACTIVE', 'tsx',     'TSE'),      # Canada    [IBKR paid]
            # ('STK',    'STK.US.MAJOR','MOST_ACTIVE','smart',  'SMART'),    # US        [IBKR paid]
            # ('STOCK.HK','STK.HK.NSE','MOST_ACTIVE','nse',    'NSE'),       # India NSE — verify location code first
        ]

        # Filter scans based on enabled markets
        option_b_scans = []
        for inst, loc, scan, m_key, ibkr_exchange in ALL_SCANS:
            if markets.get(m_key, False):
                option_b_scans.append((inst, loc, scan, ibkr_exchange))

        hot_tickers = []
        if option_b_scans:
            for inst, loc, scan, ibkr_exchange in option_b_scans:
                try:
                    print(f"Requesting scan: {loc} | {scan}...")
                    found = scanner.get_scanner_results(inst, loc, scan, ibkr_exchange)
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
        else:
            print("Option B skipped: No enabled markets have server-side scanning configured.")

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
            if option_b_scans:
                print("Option B (Scanner) found no tickers.")

    # 2. Option A Fallback: Bulk Scan on the full Universe (Reliable & Thorough)
    if DATA_SOURCE in ['ibkr', 'auto']:
        print("Option B gave no results. Attempting Option A (Bulk Historical Scan on full universe)...")
        ib_bulk = IBKRProvider(IBKR_CONFIG['host'], IBKR_CONFIG['port'], IBKR_CONFIG['client_id'])
        results = ib_bulk.get_market_data(universe, criteria)
        if results is not None:
            return results

    # 3. Last Resort: Optimized YFinance (Toggleable)
    from config import ENABLE_FALLBACKS
    if ENABLE_FALLBACKS or DATA_SOURCE == 'yfinance':
        print("Falling back to Optimized Scan (yfinance with caching)...")
        provider = OptimizedYFinanceProvider()
        return provider.get_market_data(universe, criteria)
    else:
        print("Scan complete. (YFinance fallbacks disabled by config)")
        return []
