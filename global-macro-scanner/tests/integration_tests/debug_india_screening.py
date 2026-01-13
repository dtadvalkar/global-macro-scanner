#!/usr/bin/env python3
"""
Debug why India stocks are not passing screening
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config
import yfinance as yf
from screening.screening_utils import should_pass_screening

def debug_india_stock(symbol):
    """Debug why a specific India stock is not passing screening"""
    print(f"DEBUGGING {symbol}")
    print("=" * 50)

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='1y')
        info = ticker.info

        print(f"Data availability:")
        print(f"  History: {len(hist)} days")
        print(f"  Market cap: {info.get('marketCap', 'N/A')}")

        if hist.empty or len(hist) < 250:
            print("❌ FAIL: Insufficient history")
            return

        # Extract key metrics
        low_52w = hist['Low'].min()
        current = hist['Close'].iloc[-1]
        current_vol = hist['Volume'].iloc[-1]
        avg_vol_30d = hist['Volume'].tail(30).mean()
        rvol = current_vol / avg_vol_30d if avg_vol_30d > 0 else 0

        print("\nKey metrics:")
        print(f"  Current price: ${current:.2f}")
        print(f"  52w low: ${low_52w:.2f}")
        print(f"  % from low: {current/low_52w:.3f}")
        print(f"  Volume: {current_vol:,}")
        print(f"  RVOL: {rvol:.2f}")
        print(f"  Market cap: ${info.get('marketCap', 0)/1e9:.1f}B")

        # Test criteria
        print("\nCriteria checks:")
        pct_from_low_ok = current/low_52w <= config.CRITERIA['price_52w_low_pct']
        rvol_ok = rvol >= config.CRITERIA['min_rvol']
        vol_ok = current_vol >= config.CRITERIA['min_volume']
        volume_pass = vol_ok or rvol_ok

        print(f"  Price ≤ {config.CRITERIA['price_52w_low_pct']}: {pct_from_low_ok}")
        print(f"  RVOL ≥ {config.CRITERIA['min_rvol']}: {rvol_ok}")
        print(f"  Volume ≥ {config.CRITERIA['min_volume']:,}: {vol_ok}")
        print(f"  Volume condition (OR): {volume_pass}")

        # Prepare data for screening
        symbol_data = {
            'symbol': symbol,
            'price': current,
            'low_52w': low_52w,
            'usd_mcap': info.get('marketCap', 0) / 1e9,
            'rvol': rvol,
            'volume': current_vol,
            'time': None
        }

        # Test screening
        result = should_pass_screening(symbol_data, config.CRITERIA)
        print(f"\n🎯 FINAL RESULT: {'PASS' if result else 'FAIL'}")

        if result:
            print("✅ Stock passed screening!")
        else:
            print("❌ Stock failed screening")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("DEBUGGING INDIA STOCK SCREENING")
    print("=" * 60)

    # Test well-known stocks
    test_stocks = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']

    for stock in test_stocks:
        debug_india_stock(stock)
        print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    main()