import financedatabase as fd
import os
import config
from config import CRITERIA, MARKETS
from db import get_db

db = get_db()

# Exchanges that should have the Large+Mid+Small market-cap filter applied
# after FD search. Matches the criterion behind the 398 NSE stock_fundamentals
# tickers (see project_nse_universe_criterion memory). NSE itself is intentionally
# NOT in this set — its pipeline seeds the full FD list into `tickers` and does
# fundamentals-collection filtering downstream.
CAP_FILTERED_EXCHANGES = {'SEHK', 'LSE', 'JSE', 'TADAWUL'}

# FD 2.3.1 renamed market_cap_category -> market_cap.
FD_CAP_COLUMN = 'market_cap'
FD_ALLOWED_CAPS = {'Large Cap', 'Mid Cap', 'Small Cap'}


def get_universe(markets):
    """Get stock universe based on market config with PG caching"""
    universe = []

    mapping = {
        # (fd_key, db_key) — fd_key is the FinanceDatabase exchange code (None if unsupported)
        # FD codes verified against fd.Equities() 2026-04-22 — see project_fd_codes memory.
        'nse':     ('NSE', 'NSE'),      # India NSE (.NS)
        'tsx':     ('TOR', 'TSE'),      # Canada TSE (.TO)
        'asx':     ('ASX', 'ASX'),      # Australia ASX (.AX)
        'sgx':     ('SG',  'SGX'),      # Singapore SGX (.SI)  — FD uses 'SG'
        'xetra':   ('GER', 'XETRA'),    # Germany XETRA (.DE)
        'sbf':     ('FRA', 'SBF'),      # France Euronext (.PA)
        # New exchanges — FD seed with Large+Mid+Small cap filter (Task 12, 2026-04-22)
        'sehk':    ('HKG', 'SEHK'),     # Hong Kong SEHK (.HK)
        'lse':     ('LSE', 'LSE'),      # UK LSE (.L)
        'jse':     ('JNB', 'JSE'),      # South Africa JSE (.JO)
        'tadawul': ('SAU', 'TADAWUL'),  # Saudi Arabia TADAWUL (.SR)
        # YFinance Only Markets
        'idx':     ('JKT', 'IDX'),      # Indonesia IDX (.JK)
        'set':     ('SET', 'SET'),      # Thailand SET (.BK)
    }

    for m_key, (fd_key, db_key) in mapping.items():
        if not markets.get(m_key):
            continue

        # 1. Check if we need to sync with Upstream (FinanceDatabase)
        # In LIVE mode, we expect a large universe (e.g. 1500+ for NSE); in TEST mode, 100 is enough.
        min_threshold = 1500 if (not config.TEST_MODE and db_key == 'NSE') else 100

        if fd_key is not None and not db.is_market_fresh(db_key, min_count=min_threshold):
            print(f"Refreshing {db_key} universe from FinanceDatabase...")
            try:
                equities = fd.Equities()
                selection = equities.search(exchange=fd_key)

                # Apply the Large+Mid+Small cap filter for exchanges that need parity
                # with the NSE fundamentals criterion.
                if db_key in CAP_FILTERED_EXCHANGES and FD_CAP_COLUMN in selection.columns:
                    before = len(selection)
                    selection = selection[selection[FD_CAP_COLUMN].isin(FD_ALLOWED_CAPS)]
                    print(f"  Filtered {before} -> {len(selection)} by market_cap IN (Large,Mid,Small)")

                suffix = {
                    'NSE': '.NS', 'TSE': '.TO', 'ASX': '.AX',
                    'SGX': '.SI', 'XETRA': '.DE', 'SBF': '.PA',
                    'SEHK': '.HK', 'LSE': '.L', 'JSE': '.JO', 'TADAWUL': '.SR',
                    'IDX': '.JK', 'SET': '.BK'
                }.get(db_key, '')

                tickers = [f"{s}{suffix}" if not s.endswith(suffix) else s for s in selection.index]

                if config.TEST_MODE and m_key == 'nse':
                    tickers = tickers[:CRITERIA.get('nse_top_limit', 200)]

                if tickers:
                    db.save_tickers(db_key, tickers)
                    print(f"  ✅ Seeded {len(tickers)} tickers for {db_key}")
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
