#!/usr/bin/env python3
"""
Demo: How stock_fundamentals table gets populated with NSE data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
config.TEST_MODE = True

from data.providers import IBKRProvider
from data.cache_manager import FundamentalCacheManager

def demo_fundamentals_population():
    print('DEMO: NSE FUNDAMENTALS TABLE POPULATION')
    print('=' * 50)
    print('This shows how stock_fundamentals table gets populated')
    print()

    # Temporarily relax criteria for demo
    original_criteria = config.CRITERIA.copy()
    config.CRITERIA.update({
        'price_52w_low_pct': 1.50,  # Allow stocks up to 50% above low
        'min_rvol': 0.5,            # Allow RVOL as low as 0.5x
        'min_volume': 10000         # Lower volume requirement
    })

    valid_nse_stocks = ['RELIANCE.NS', 'TCS.NS']
    print(f'Testing stocks: {valid_nse_stocks}')
    print('Relaxed criteria for demo purposes')

    # Initialize IBKR provider
    ibkr_provider = IBKRProvider(
        host=config.IBKR_CONFIG['host'],
        port=config.IBKR_CONFIG['port'],
        client_id=config.IBKR_CONFIG['client_id']
    )

    print('\n1. Connecting to IBKR...')
    connection_ok = ibkr_provider.connect()
    if not connection_ok:
        print('❌ IBKR connection failed')
        return

    print('IBKR connected')

    # Enable fundamentals caching
    print('\n2. Enabling fundamentals cache...')
    ibkr_provider.fundamentals_cache = FundamentalCacheManager()
    print('Fundamentals cache ready')

    # Run the scan
    print('\n3. Running NSE scan (this populates fundamentals table)...')
    results = ibkr_provider.get_market_data(valid_nse_stocks, config.CRITERIA)

    ibkr_provider.disconnect_sync()

    # Show results
    print('\n4. RESULTS:')
    print(f'   Stocks tested: {len(valid_nse_stocks)}')
    print(f'   Stocks processed: {len(results)}')

    if results:
        print('\nSUCCESS! Fundamentals cached:')
        for result in results:
            symbol = result.get('symbol', 'Unknown')
            price = result.get('price', 0)
            usd_mcap = result.get('usd_mcap', 0)
            mcap_display = f'${usd_mcap/1000:.1f}B' if usd_mcap >= 1000 else f'${usd_mcap:.0f}M'
            print(f'   {symbol}: ${price:.2f}, Market Cap: {mcap_display}')

        print('\nstock_fundamentals table now contains:')
        print('   - ticker (primary key)')
        print('   - market_cap_usd (for filtering small stocks)')
        print('   - sector, industry (for future analysis)')
        print('   - last_updated, data_source, etc.')

        print('\nYou can now query:')
        print("   SELECT ticker, market_cap_usd/1000000 as cap_m, sector")
        print("   FROM stock_fundamentals;")
    else:
        print('No stocks passed screening')

    # Restore original criteria
    config.CRITERIA.update(original_criteria)
    print('\n📋 Original criteria restored')

if __name__ == '__main__':
    demo_fundamentals_population()