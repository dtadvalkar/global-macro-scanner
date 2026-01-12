#!/usr/bin/env python3
"""
Populate NSE Fundamentals
Fetches and stores fundamentals data for validated NSE stocks
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import DatabaseManager
from data.cache_manager import FundamentalCacheManager

def populate_nse_fundamentals():
    print('POPULATING NSE FUNDAMENTALS')
    print('=' * 40)

    # Get validated NSE stocks
    db = DatabaseManager()
    nse_stocks = db.get_cached_tickers('NSE')
    print(f'Found {len(nse_stocks)} validated NSE stocks')

    if not nse_stocks:
        print('No NSE stocks found. Run NSE validation first.')
        return

    # Initialize fundamentals cache
    cache = FundamentalCacheManager(use_database=True)

    # Track progress
    populated = 0
    failed = 0

    print('Starting fundamentals population...')
    print('This may take several minutes due to rate limits')

    for i, stock in enumerate(nse_stocks):
        try:
            # Check if we already have fundamentals
            existing = cache.get_fundamentals(stock)
            if existing:
                print(f'[{i+1}/{len(nse_stocks)}] {stock} - Already cached')
                continue

            # Fetch from YFinance with rate limiting
            print(f'[{i+1}/{len(nse_stocks)}] {stock} - Fetching...')

            import yfinance as yf
            ticker_obj = yf.Ticker(stock)
            info = ticker_obj.info

            if info and 'marketCap' in info:
                # Prepare fundamentals data
                fundamentals_data = {
                    'symbol': stock.split('.')[0],
                    'exchange': 'NSE',
                    'market_cap_usd': info.get('marketCap', 0),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', ''),
                    'currency': 'INR',
                    'country': info.get('country', ''),
                    'data_source': 'yfinance'
                }

                # Store in cache
                cache.set_fundamentals(stock, fundamentals_data)
                populated += 1
                print(f'  ✓ Stored: ${fundamentals_data["market_cap_usd"]/1000000:.1f}M market cap')
            else:
                failed += 1
                print(f'  ✗ No data available')

            # Rate limiting - wait between requests
            time.sleep(0.5)  # 2 requests per second max

        except Exception as e:
            failed += 1
            print(f'  ✗ Error: {e}')

    print('\n' + '=' * 40)
    print('FUNDAMENTALS POPULATION COMPLETE')
    print(f'Successfully populated: {populated}')
    print(f'Failed/No data: {failed}')
    print(f'Total processed: {populated + failed}')

    # Show sample results
    if populated > 0:
        print('\nSample populated fundamentals:')
        sample_stocks = nse_stocks[:3]
        for stock in sample_stocks:
            fundamentals = cache.get_fundamentals(stock)
            if fundamentals:
                mcap = fundamentals.get('market_cap_usd', 0) / 1000000
                sector = fundamentals.get('sector', 'N/A')
                print(f'  {stock}: ${mcap:.1f}M, {sector}')

if __name__ == '__main__':
    populate_nse_fundamentals()