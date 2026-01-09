# 🌍 MARKET CONFIGURATION & REGISTRY

# 1. Market Activation (Toggle Markets On/Off)
MARKETS = {
    'nse': True,                        # India NSE (.NS)
    'idx': True,                        # Indonesia IDX (.JK) - YFinance only (IBKR not supported)
    'set': True,                        # Thailand SET (.BK) - YFinance only (IBKR not supported)
    'tsx': True,                        # Canada TSX (.TO)
    'cme_futures': False                # CME ES=F, NQ=F (In Progress)
}

# NOTE: Thailand SET and Indonesia IDX exchanges are not available via IBKR (even with delayed data).
# .BK and .JK stocks are automatically routed to YFinance fallback for all data requests.

# 2. Market Registry (Classification & Mapping)
# Defines scanning thresholds for "Major" vs "Emerging" markets
MARKET_REGISTRY = {
    'SMA': {'type': 'MAJOR', 'threshold_usd': 500_000_000}, # US
    'TSE': {'type': 'MAJOR', 'threshold_usd': 500_000_000}, # Canada (Note: Code handles CAD conversion)
    'NSE': {'type': 'EMERGING', 'threshold_usd': 150_000_000}, # India
    'IDX': {'type': 'EMERGING', 'threshold_usd': 150_000_000}, # Indonesia
    'SET': {'type': 'EMERGING', 'threshold_usd': 150_000_000}, # Thailand
}

def get_market_type(exchange):
    """Return 'MAJOR' or 'EMERGING' for a given exchange code"""
    return MARKET_REGISTRY.get(exchange, {}).get('type', 'MAJOR')

def get_min_market_cap(exchange):
    """Return the minimum market cap (USD) for this exchange"""
    return MARKET_REGISTRY.get(exchange, {}).get('threshold_usd', 500_000_000)
