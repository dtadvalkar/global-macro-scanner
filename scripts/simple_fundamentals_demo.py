#!/usr/bin/env python3
"""
Simple demo: How stock_fundamentals table gets populated
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from data.providers import IBKRProvider
from data.cache_manager import FundamentalCacheManager

def simple_fundamentals_demo():
    print('SIMPLE NSE FUNDAMENTALS POPULATION DEMO')
    print('=' * 50)

    # Create ultra-simple criteria that should pass
    simple_criteria = {
        'price_52w_low_pct': 10.0,     # Allow stocks up to 1000% above low
        'min_rvol': 0.01,              # Allow very low RVOL
        'min_volume': 100,             # Very low volume
        'min_history_days': 200,       # Reasonable history
        'rsi_enabled': False,
        'ma_enabled': False,
        'atr_enabled': False,
        'pattern_enabled': False,
        'max_price': 100000,           # High price limit
        'min_price': 0.01,             # Low price limit
        'min_market_cap_emerging': 1000000,  # $1M minimum
    }

    print('Using ultra-simple criteria that should always pass')
    print('Testing RELIANCE.NS with IBKR...')

    # Initialize provider
    ibkr_provider = IBKRProvider(
        host=config.IBKR_CONFIG['host'],
        port=config.IBKR_CONFIG['port'],
        client_id=config.IBKR_CONFIG['client_id']
    )

    connection_ok = ibkr_provider.connect()
    if not connection_ok:
        print('IBKR connection failed')
        return

    # Enable fundamentals caching with database storage
    ibkr_provider.fundamentals_cache = FundamentalCacheManager(use_database=True)
    print('Fundamentals cache with database storage enabled')

    # Test single stock
    test_stocks = ['RELIANCE.NS']
    results = ibkr_provider.get_market_data(test_stocks, simple_criteria)

    ibkr_provider.disconnect_sync()

    print(f'\\nRESULT: {len(results)} stocks processed')

    if results:
        result = results[0]
        print('\\nSUCCESS! Stock fundamentals cached:')
        symbol = result.get('symbol', 'Unknown')
        price = result.get('price', 0)
        usd_mcap = result.get('usd_mcap', 0)
        print(f'  Ticker: {symbol}')
        print(f'  Price: ${price:.2f}')
        print(f'  Market Cap: ${usd_mcap/1000:.1f}B')

        print('\\nThe stock_fundamentals table now contains:')
        print('  - ticker, symbol, exchange')
        print('  - market_cap_usd (key for filtering)')
        print('  - sector, industry')
        print('  - last_updated, data_source (\"ibkr\")')
        print('  - And more fields for future filtering')
    else:
        print('No results - check if RELIANCE.NS is available in IBKR')

if __name__ == '__main__':
    simple_fundamentals_demo()