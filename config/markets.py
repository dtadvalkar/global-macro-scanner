# 🌍 MARKET CONFIGURATION & REGISTRY

# 1. Market Activation (Toggle Markets On/Off)
MARKETS = {
    # IBKR Supported Markets
    'nse': True,                        # India NSE (.NS) [IBKR]
    'tsx': True,                        # Canada TSE (.TO) [IBKR] - Fixed: TSE exchange
    'asx': False,                       # Australia ASX (.AX) [IBKR] - Needs permissions
    'sgx': False,                       # Singapore SGX (.SI) [IBKR] - Needs permissions
    'xetra': False,                     # Germany XETRA (.DE) [IBKR] - Needs permissions
    'sbf': False,                       # France Euronext (.PA) [IBKR] - Needs permissions

    # YFinance Only Markets
    'idx': True,                        # Indonesia IDX (.JK) [YFINANCE]
    'set': True,                        # Thailand SET (.BK) [YFINANCE]

    # Future Options
    'cme_futures': False                # CME ES=F, NQ=F (In Progress)
}

# NOTE: Thailand SET and Indonesia IDX exchanges are not available via IBKR (even with delayed data).
# .BK and .JK stocks are automatically routed to YFinance fallback for all data requests.

# 2. Market Registry (Classification & Mapping)
# Defines scanning thresholds for "Major" vs "Emerging" markets
# IBKR supported markets marked with [IBKR], others use YFinance
MARKET_REGISTRY = {
    # IBKR Supported Markets
    'SMART': {'type': 'MAJOR', 'threshold_usd': 500_000_000, 'provider': 'IBKR'}, # US [IBKR]
    'TSE': {'type': 'MAJOR', 'threshold_usd': 500_000_000, 'provider': 'IBKR'}, # Canada [IBKR] - Fixed: TSE not TSX
    'NSE': {'type': 'EMERGING', 'threshold_usd': 150_000_000, 'provider': 'IBKR'}, # India [IBKR]
    'IBIS': {'type': 'MAJOR', 'threshold_usd': 500_000_000, 'provider': 'IBKR'}, # Germany [IBKR]
    'SBF': {'type': 'MAJOR', 'threshold_usd': 500_000_000, 'provider': 'IBKR'}, # France [IBKR]
    'ASX': {'type': 'MAJOR', 'threshold_usd': 500_000_000, 'provider': 'IBKR'}, # Australia [IBKR]
    'SGX': {'type': 'MAJOR', 'threshold_usd': 500_000_000, 'provider': 'IBKR'}, # Singapore [IBKR]

    # YFinance Fallback Markets
    'IDX': {'type': 'EMERGING', 'threshold_usd': 150_000_000, 'provider': 'YFINANCE'}, # Indonesia [YFINANCE]
    'SET': {'type': 'EMERGING', 'threshold_usd': 150_000_000, 'provider': 'YFINANCE'}, # Thailand [YFINANCE]
}

def get_market_type(exchange):
    """Return 'MAJOR' or 'EMERGING' for a given exchange code"""
    return MARKET_REGISTRY.get(exchange, {}).get('type', 'MAJOR')

def get_min_market_cap(exchange):
    """Return the minimum market cap (USD) for this exchange"""
    return MARKET_REGISTRY.get(exchange, {}).get('threshold_usd', 500_000_000)
