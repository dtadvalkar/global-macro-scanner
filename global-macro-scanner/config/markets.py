MARKETS = {
    'equities': {
        'nse': {'limit': 200, 'suffix': '.NS'},
        'idx': {'tickers': ['BBCA.JK', 'BBRI.JK']},
        'set': {'tickers': ['PTT.BK', 'CPALL.BK']}
    },
    'futures': ['ES=F', 'NQ=F', 'CL=F', 'GC=F', 'ZB=F'],  # Bonds
    'commodities': ['GLD', 'SLV', 'COPX'],                # Gold, Silver, Copper
    'macro': ['^VIX', 'DX-Y.NYB', 'TLT']                  # VIX, Dollar, Bonds
}
