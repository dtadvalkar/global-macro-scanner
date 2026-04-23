import financedatabase as fd
import os
import config
from config import CRITERIA, MARKETS
from db import get_db

db = get_db()

def get_universe(markets):
    """Get stock universe based on market config with PG caching"""
    universe = []
    
    mapping = {
        # IBKR Supported Markets — FinanceDatabase key (fd_key) or None if FD not available
        'nse':     ('NSE', 'NSE'),      # India NSE (.NS)      — FD seeded
        'tsx':     ('TOR', 'TSE'),      # Canada TSE (.TO)     — FD seeded
        'asx':     ('ASX', 'ASX'),      # Australia ASX (.AX)  — FD seeded
        'sgx':     ('SG',  'SGX'),      # Singapore SGX (.SI)  — FD uses 'SG'
        'xetra':   ('GER', 'XETRA'),    # Germany XETRA (.DE)  — FD seeded
        'sbf':     ('FRA', 'SBF'),      # France Euronext (.PA) — FD seeded
        # IBKR free delayed — no FinanceDatabase key; seeded via scripts/etl/ibkr/seed_exchange_tickers.py
        'sehk':    (None,  'SEHK'),     # Hong Kong SEHK (.HK)
        'lse':     (None,  'LSE'),      # UK LSE (.L)
        'jse':     (None,  'JSE'),      # South Africa JSE (.JO)
        'tadawul': (None,  'TADAWUL'),  # Saudi Arabia TADAWUL (.SR)
        # YFinance Only Markets
        'idx':     ('JKT', 'IDX'),      # Indonesia IDX (.JK)
        'set':     ('SET', 'SET'),      # Thailand SET (.BK)
    }

    for m_key, (fd_key, db_key) in mapping.items():
        if not markets.get(m_key):
            continue

        # 1. Check if we need to sync with Upstream (FinanceDatabase)
        # In LIVE mode, we expect a large universe (e.g. 1500+ for NSE); in TEST mode, 100 is enough.
        # IBKR-free exchanges have no fd_key — skip FD refresh entirely; rely on seeded tickers.
        min_threshold = 1500 if (not config.TEST_MODE and db_key == 'NSE') else 100

        if fd_key is not None and not db.is_market_fresh(db_key, min_count=min_threshold):
            print(f"Refreshing {db_key} universe from FinanceDatabase...")
            try:
                equities = fd.Equities()
                selection = equities.search(exchange=fd_key)

                suffix = {
                    'NSE': '.NS', 'TSE': '.TO', 'ASX': '.AX',
                    'SGX': '.SI', 'XETRA': '.DE', 'SBF': '.PA',
                    'IDX': '.JK', 'SET': '.BK'
                }.get(db_key, '')

                tickers = [f"{s}{suffix}" if not s.endswith(suffix) else s for s in selection.index]

                if config.TEST_MODE and m_key == 'nse':
                    tickers = tickers[:CRITERIA.get('nse_top_limit', 200)]

                if tickers:
                    db.save_tickers(db_key, tickers)
                    print(f"  ✅ Skipping fundamentals sync - data already exists in stock_fundamentals table")
                else:
                    print(f"  Warning: No tickers found for {db_key} in FinanceDatabase.")

            except Exception as e:
                print(f"Warning: {db_key} FD load failed: {e}")
                # If FD fails, we might still have old actionable tickers in DB, so we proceed.

        elif fd_key is None:
            actionable_count = len(db.get_actionable_tickers(db_key))
            if actionable_count == 0:
                print(f"  ℹ️  {db_key}: no tickers seeded yet — run scripts/etl/ibkr/seed_exchange_tickers.py first.")

        # 2. Load Actionable Tickers (Active + Parole)
        actionable = db.get_actionable_tickers(db_key)
        print(f"Loaded {len(actionable)} actionable {db_key} tickers from DB.")
        universe.extend(actionable)
        
    print(f"Loaded {len(universe)} stocks total")
    return universe
