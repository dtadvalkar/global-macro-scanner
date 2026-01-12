import financedatabase as fd
from config import CRITERIA, MARKETS, TEST_MODE
from storage.database import DatabaseManager

db = DatabaseManager()

def get_universe(markets):
    """Get stock universe based on market config with PG caching"""
    universe = []
    
    mapping = {
        # IBKR Supported Markets
        'nse': ('NSE', 'NSE'),           # India NSE (.NS)
        'tsx': ('TOR', 'TSE'),           # Canada TSE (.TO) - Fixed: TSE not TSX
        'asx': ('ASX', 'ASX'),           # Australia ASX (.AX)
        'sgx': ('SG', 'SGX'),            # Singapore SGX (.SI) - FD uses 'SG'
        'xetra': ('GER', 'XETRA'),       # Germany XETRA (.DE)
        'sbf': ('FRA', 'SBF'),           # France Euronext (.PA)

        # YFinance Only Markets
        'idx': ('JKT', 'IDX'),           # Indonesia IDX (.JK)
        'set': ('SET', 'SET')            # Thailand SET (.BK)
    }
    
    for m_key, (fd_key, db_key) in mapping.items():
        if not markets.get(m_key):
            continue
            
        # Check if only NSE is enabled (from --exchanges NSE parameter)
        enabled_markets = [k for k, v in markets.items() if v]
        nse_only = (m_key == 'nse' and len(enabled_markets) == 1 and 'nse' in enabled_markets)

        if nse_only:
            # Use verified NSE stocks when only NSE is enabled
            verified_nse_stocks = [
                'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'INFY.NS',
                'ITC.NS', 'HINDUNILVR.NS', 'AXISBANK.NS', 'LT.NS', 'MARUTI.NS',
                'BAJFINANCE.NS', 'BAJAJ-AUTO.NS', 'WIPRO.NS', 'BHARTIARTL.NS', 'NESTLEIND.NS'
            ]
            universe.extend(verified_nse_stocks)
            print(f"Using {len(verified_nse_stocks)} verified NSE stocks (IBKR-compatible)")
            # Skip cache loading for NSE when using verified stocks
            continue

        # Try Cache First (skip for NSE when only NSE is enabled)
        cached = db.get_cached_tickers(db_key)
        if cached and not nse_only:
            print(f"Loaded {len(cached)} {db_key} tickers from PostgreSQL cache.")
            universe.extend(cached)
            continue

        # Fetch from FinanceDatabase
        print(f"Loading {db_key} universe (financedatabase)...")
        try:
            equities = fd.Equities()
            selection = equities.search(exchange=fd_key)
            
            suffix = {
                # IBKR Supported Markets
                'NSE': '.NS',           # India
                'TSE': '.TO',           # Canada
                'ASX': '.AX',           # Australia
                'SGX': '.SI',           # Singapore
                'XETRA': '.DE',         # Germany
                'SBF': '.PA',           # France

                # YFinance Only Markets
                'IDX': '.JK',           # Indonesia
                'SET': '.BK'            # Thailand
            }.get(db_key, '')
            
            tickers = [f"{s}{suffix}" if not s.endswith(suffix) else s for s in selection.index]
            
            if TEST_MODE and m_key == 'nse':
                tickers = tickers[:CRITERIA.get('nse_top_limit', 200)]
            
            db.save_tickers(db_key, tickers)
            universe.extend(tickers)
            print(f"  → Found {len(tickers)} {db_key} stocks (Cached to DB)")
            
        except Exception as e:
            print(f"Warning: {db_key} load failed: {e}")
            fallback = {
                'NSE': ['RELIANCE.NS', 'TCS.NS'],
                'TSX': ['RY.TO', 'TD.TO']
            }.get(db_key, [])
            universe.extend(fallback)
        
    print(f"Loaded {len(universe)} stocks total")
    return universe
