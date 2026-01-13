#!/usr/bin/env python3
"""
Simple test of fundamental data availability from YFinance
"""

import yfinance as yf

def test_stocks():
    """Test key stocks from different markets"""
    test_stocks = ['AAPL', 'MSFT', 'RELIANCE.NS', 'RY.TO']

    print("YFINDANCE FUNDAMENTAL DATA TEST")
    print("=" * 50)

    for symbol in test_stocks:
        print(f"\n{symbol}:")
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            fields = ['marketCap', 'sector', 'industry', 'currency', 'country', 'exchange']
            for field in fields:
                value = info.get(field, 'MISSING')
                status = "OK" if value != 'MISSING' else "MISSING"
                print(f"  {field}: {status}")

        except Exception as e:
            print(f"  ERROR: {e}")

if __name__ == '__main__':
    test_stocks()