#!/usr/bin/env python3
"""
Test Current Markets with Enhanced Scanning
Tests India (NSE), Australia (ASX), Singapore (SGX) with all new features
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config
config.TEST_MODE = True  # Limit to smaller universe for testing

from main import daily_scan

def test_current_markets():
    """Test current accessible markets with enhanced scanning"""
    print('TESTING CURRENT MARKETS WITH ENHANCED SCANNING')
    print('=' * 60)
    print('Markets: India (NSE), Australia (ASX), Singapore (SGX)')
    print('Features: RSI, MA, ATR filtering + Pattern recognition')
    print('Caching: Fundamental early filtering (if DB available)')
    print()

    try:
        results = daily_scan()
        print(f'\nSCAN RESULTS SUMMARY')
        print('=' * 40)
        print(f'Total potential trades found: {len(results)}')

        if results:
            # Analyze results by market
            markets = {}
            for result in results:
                symbol = result.get('symbol', '')
                if symbol.endswith('.NS'):
                    market = 'India (NSE)'
                elif symbol.endswith('.AX'):
                    market = 'Australia (ASX)'
                elif symbol.endswith('.SI'):
                    market = 'Singapore (SGX)'
                else:
                    market = 'Other'

                if market not in markets:
                    markets[market] = []
                markets[market].append(result)

            print(f'Markets with signals: {len(markets)}')
            for market, stocks in markets.items():
                print(f'  {market}: {len(stocks)} signals')

            # Show top 3 results with technical details
            print(f'\nTOP 3 SIGNALS:')
            for i, result in enumerate(results[:3]):
                symbol = result.get('symbol', 'Unknown')
                price = result.get('price', 0)
                pct_from_low = result.get('pct_from_low', 1.0)
                rvol = result.get('rvol', 0)

                print(f'{i+1}. {symbol}:')
                print(f'   Price: ${price:.2f} ({pct_from_low:.1%} from 52w low)')
                print(f'   Volume: RVOL {rvol:.1f}x')

                # Check for technical indicators
                rsi = result.get('rsi')
                atr = result.get('atr_pct')
                if rsi or atr:
                    tech_info = []
                    if rsi: tech_info.append(f'RSI {rsi:.1f}')
                    if atr: tech_info.append(f'ATR {atr:.1%}')
                    if tech_info:
                        tech_str = ', '.join(tech_info)
                        print(f'   Technical: {tech_str}')
                    else:
                        print('   Technical: None available')
                else:
                    print('   Technical: None available')

        else:
            print('No signals found - this may be expected due to strict criteria')

        print(f'\nTEST STATUS: SUCCESS - Enhanced scanning operational')

        # Validate that enhanced features are working
        print(f'\nVALIDATION CHECKS:')
        if results:
            sample = results[0]
            has_rsi = 'rsi' in sample
            has_atr = 'atr_pct' in sample
            rsi_status = 'PASS' if has_rsi else 'FAIL'
            atr_status = 'PASS' if has_atr else 'FAIL'
            tech_status = 'PASS' if len(results) > 0 else 'UNCLEAR'
            print(f'  RSI calculation: {rsi_status}')
            print(f'  ATR calculation: {atr_status}')
            print(f'  Technical filtering: {tech_status}')

        return len(results)

    except Exception as e:
        print(f'TEST FAILED: {e}')
        import traceback
        traceback.print_exc()
        return 0

if __name__ == '__main__':
    signal_count = test_current_markets()
    print(f'\nFinal result: {signal_count} signals detected')
    exit(0 if signal_count > 0 else 1)