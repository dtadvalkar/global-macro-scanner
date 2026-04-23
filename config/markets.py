# 🌍 MARKET CONFIGURATION & REGISTRY
#
# Two-source strategy (2026-04-22):
#   Historical OHLCV  → always yf.download() bulk → prices_daily
#   Live(ish) / scan  → IBKR Type 3 Delayed primary; yfinance fallback if IBKR fails
#
# IBKR free delayed data (confirmed): NSE, BSE, ASX, SGX, SEHK, LSE, JSE, TADAWUL
# IBKR paid subscription required:    SMART (US), TSE (Canada), IBIS (Germany), SBF (France)
# IBKR not supported (yfinance-only): SET, IDX, BOVESPA, KSE, TWSE, Bursa, TSEJ

# 1. Market Activation (Toggle Markets On/Off)
MARKETS = {
    # IBKR Free Delayed Data — enabled
    'nse':     True,   # India NSE     (.NS) [IBKR free]
    'asx':     True,   # Australia ASX (.AX) [IBKR free]
    'sgx':     True,   # Singapore SGX (.SI) [IBKR free]
    'sehk':    True,   # Hong Kong     (.HK) [IBKR free] — strip leading zeros: 0005→5
    'lse':     True,   # UK LSE        (.L)  [IBKR free] — trailing period: BP→BP.
    'jse':     True,   # South Africa  (.JO) [IBKR free]
    'tadawul': True,   # Saudi Arabia  (.SR) [IBKR free] — numeric codes e.g. 2222

    # IBKR Paid Subscription Required — disabled until subscriptions enabled
    'tsx':     False,  # Canada TSE    (.TO) [IBKR paid] — Error 162 confirmed 2026-04-22
    'xetra':   False,  # Germany IBIS  (.DE) [IBKR paid] — Error 162 confirmed 2026-04-22
    'sbf':     False,  # France SBF    (.PA) [IBKR paid] — Error 162 confirmed 2026-04-22
    'smart':   False,  # US SMART/NYSE        [IBKR paid] — Error 162 confirmed 2026-04-22

    # YFinance-Only Markets (IBKR not supported)
    'idx':     True,   # Indonesia IDX (.JK) [YFINANCE]
    'set':     True,   # Thailand SET  (.BK) [YFINANCE]
    'bovespa': False,  # Brazil B3     (.SA) [YFINANCE] — pending ticker universe build
    'kse':     False,  # Korea KOSPI   (.KS) [YFINANCE] — pending ticker universe build
    'twse':    False,  # Taiwan        (.TW) [YFINANCE] — pending ticker universe build
    'bursa':   False,  # Malaysia      (.KL) [YFINANCE] — pending ticker universe build
}

# 2. Market Registry (Classification, Mapping, Symbol Rules)
MARKET_REGISTRY = {
    # IBKR Free Delayed Data
    'NSE':     {'type': 'EMERGING', 'threshold_usd': 150_000_000, 'provider': 'IBKR',     'yf_suffix': '.NS', 'ibkr_currency': 'INR'},
    'BSE':     {'type': 'EMERGING', 'threshold_usd': 150_000_000, 'provider': 'IBKR',     'yf_suffix': '.BO', 'ibkr_currency': 'INR'},
    'ASX':     {'type': 'MAJOR',    'threshold_usd': 500_000_000, 'provider': 'IBKR',     'yf_suffix': '.AX', 'ibkr_currency': 'AUD'},
    'SGX':     {'type': 'MAJOR',    'threshold_usd': 500_000_000, 'provider': 'IBKR',     'yf_suffix': '.SI', 'ibkr_currency': 'SGD'},
    'SEHK':    {'type': 'MAJOR',    'threshold_usd': 500_000_000, 'provider': 'IBKR',     'yf_suffix': '.HK', 'ibkr_currency': 'HKD', 'symbol_rule': 'strip_leading_zeros'},
    'LSE':     {'type': 'MAJOR',    'threshold_usd': 500_000_000, 'provider': 'IBKR',     'yf_suffix': '.L',  'ibkr_currency': 'GBP', 'symbol_rule': 'trailing_period'},
    'JSE':     {'type': 'EMERGING', 'threshold_usd': 150_000_000, 'provider': 'IBKR',     'yf_suffix': '.JO', 'ibkr_currency': 'ZAR'},
    'TADAWUL': {'type': 'EMERGING', 'threshold_usd': 150_000_000, 'provider': 'IBKR',     'yf_suffix': '.SR', 'ibkr_currency': 'SAR'},

    # IBKR Paid (disabled — Error 162 on historical data)
    'SMART':   {'type': 'MAJOR',    'threshold_usd': 500_000_000, 'provider': 'IBKR_PAID', 'yf_suffix': '',    'ibkr_currency': 'USD'},
    'TSE':     {'type': 'MAJOR',    'threshold_usd': 500_000_000, 'provider': 'IBKR_PAID', 'yf_suffix': '.TO', 'ibkr_currency': 'CAD'},
    'IBIS':    {'type': 'MAJOR',    'threshold_usd': 500_000_000, 'provider': 'IBKR_PAID', 'yf_suffix': '.DE', 'ibkr_currency': 'EUR'},
    'SBF':     {'type': 'MAJOR',    'threshold_usd': 500_000_000, 'provider': 'IBKR_PAID', 'yf_suffix': '.PA', 'ibkr_currency': 'EUR'},

    # YFinance-Only
    'IDX':     {'type': 'EMERGING', 'threshold_usd': 150_000_000, 'provider': 'YFINANCE',  'yf_suffix': '.JK'},
    'SET':     {'type': 'EMERGING', 'threshold_usd': 150_000_000, 'provider': 'YFINANCE',  'yf_suffix': '.BK'},
    'BOVESPA': {'type': 'EMERGING', 'threshold_usd': 150_000_000, 'provider': 'YFINANCE',  'yf_suffix': '.SA'},
    'KSE':     {'type': 'MAJOR',    'threshold_usd': 500_000_000, 'provider': 'YFINANCE',  'yf_suffix': '.KS'},
    'TWSE':    {'type': 'MAJOR',    'threshold_usd': 500_000_000, 'provider': 'YFINANCE',  'yf_suffix': '.TW'},
    'BURSA':   {'type': 'EMERGING', 'threshold_usd': 150_000_000, 'provider': 'YFINANCE',  'yf_suffix': '.KL'},
}


def normalise_ibkr_symbol(symbol: str, exchange: str) -> str:
    """Convert a yfinance-format base symbol to IBKR format before sending to IBKR.

    Direction: yfinance → IBKR  (e.g. for contract qualification)
      strip_leading_zeros (SEHK): '0005' → '5'
      trailing_period     (LSE):  'BP'   → 'BP.'
    """
    rule = MARKET_REGISTRY.get(exchange, {}).get('symbol_rule')
    if rule == 'strip_leading_zeros':
        return symbol.lstrip('0') or symbol  # SEHK: 0005 → 5
    if rule == 'trailing_period':
        return symbol if symbol.endswith('.') else symbol + '.'  # LSE: BP → BP.
    return symbol


def ibkr_to_yfinance(ibkr_symbol: str, exchange: str) -> str:
    """Convert an IBKR scanner output symbol to yfinance-format ticker.

    Direction: IBKR scanner → yfinance  (e.g. after reqScannerData)
    This is the counterpart to normalise_ibkr_symbol().

    Rules applied per MARKET_REGISTRY symbol_rule:
      trailing_period (LSE):       'BP.'   → strip period → 'BP.L'
      strip_leading_zeros (SEHK):  '5'     → no change needed; yfinance accepts '5.HK'
      (all others)                 symbol  → symbol + yf_suffix

    Single source of truth: all edge-case logic lives here, not in callers.
    """
    rule = MARKET_REGISTRY.get(exchange, {}).get('symbol_rule')
    if rule == 'trailing_period':
        symbol = ibkr_symbol.rstrip('.')  # 'BP.' → 'BP'
    else:
        symbol = ibkr_symbol              # no transformation for other exchanges
    return symbol + get_yf_suffix(exchange)


def exchange_from_yf_ticker(yf_ticker: str) -> str:
    """Reverse-lookup: return MARKET_REGISTRY exchange code for a yfinance-format ticker.

    Derived from MARKET_REGISTRY yf_suffix values — stays in sync automatically
    as new exchanges are added.  Returns '' for US stocks (no suffix).

    Examples:
        'RELIANCE.NS' → 'NSE'
        '5.HK'        → 'SEHK'
        'BP.L'        → 'LSE'
        '2222.SR'     → 'TADAWUL'
    """
    if '.' not in yf_ticker:
        return ''  # US / no suffix
    suffix = '.' + yf_ticker.rsplit('.', 1)[1]
    for exchange, cfg in MARKET_REGISTRY.items():
        if cfg.get('yf_suffix') == suffix:
            return exchange
    return ''


def get_market_type(exchange: str) -> str:
    """Return 'MAJOR' or 'EMERGING' for a given exchange code."""
    return MARKET_REGISTRY.get(exchange, {}).get('type', 'MAJOR')


def get_min_market_cap(exchange: str) -> int:
    """Return the minimum market cap (USD) for this exchange."""
    return MARKET_REGISTRY.get(exchange, {}).get('threshold_usd', 500_000_000)


def get_yf_suffix(exchange: str) -> str:
    """Return the yfinance ticker suffix for a given IBKR exchange code."""
    return MARKET_REGISTRY.get(exchange, {}).get('yf_suffix', '')
