STOCK_CRITERIA = {
    'price_52w_low_pct': 1.01,
    'min_market_cap_usd': 5e8,
    'rsi_oversold': 25,
    'volume_spike': 2.0
}

MACRO_CRITERIA = {
    'es_breakout': True,      # S&P futures breakout
    'vix_spike': 1.5,         # VIX > 1.5x 20d avg
    'dollar_index': 90,       # DXY threshold
    'gold_surge': 2.0         # Gold > 2% daily
}

CME_FUTURES = ['ES=F', 'NQ=F', 'CL=F', 'GC=F']  # S&P, Nasdaq, Oil, Gold
