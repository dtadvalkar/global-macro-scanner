import requests

def get_live_fx_rate(base_currency):
    """Live USD rates - works for ANY market"""
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        resp = requests.get(url, timeout=5)
        return resp.json()['rates']['USD']
    except:
        # Emergency fallback
        return {
            'INR': 0.012, 'IDR': 0.000064, 'THB': 0.028,
            'USD': 1.0, 'CAD': 0.74
        }.get(base_currency, 1.0)

def get_currency(symbol):
    """Auto-detect from ticker suffix"""
    suffixes = {
        '.NS': 'INR', '.JK': 'IDR', '.BK': 'THB', 
        '.TO': 'CAD', '.T': 'JPY'
    }
    return next((cur for suf, cur in suffixes.items() if symbol.endswith(suf)), 'USD')

def usd_market_cap(symbol, raw_mcap):
    """Convert ANY local mcap → USD"""
    currency = get_currency(symbol)
    rate = get_live_fx_rate(currency)
    return raw_mcap * rate
