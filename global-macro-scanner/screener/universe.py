import financedatabase as fd
from config import CRITERIA, MARKETS, TEST_MODE
from storage.database import DatabaseManager

db = DatabaseManager()

def get_universe(markets):
    """Get stock universe based on market config with PG caching"""
    universe = []
    
    mapping = {
        'nse': ('NSE', 'NSE'),
        'idx': ('JKT', 'IDX'),
        'set': ('SET', 'SET'),
        'tsx': ('TOR', 'TSX')
    }
    
    for m_key, (fd_key, db_key) in mapping.items():
        if not markets.get(m_key):
            continue
            
        # Try Cache First
        cached = db.get_cached_tickers(db_key)
        if cached:
            print(f"Loaded {len(cached)} {db_key} tickers from PostgreSQL cache.")
            universe.extend(cached)
            continue

        # Fetch from FinanceDatabase
        print(f"Loading {db_key} universe (financedatabase)...")
        try:
            equities = fd.Equities()
            selection = equities.search(exchange=fd_key)
            
            suffix = {
                'NSE': '.NS',
                'IDX': '.JK',
                'SET': '.BK',
                'TSX': '.TO'
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
