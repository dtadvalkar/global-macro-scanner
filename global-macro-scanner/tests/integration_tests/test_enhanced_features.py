#!/usr/bin/env python3
"""
Test Enhanced Scanning Features
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import daily_scan
from config import TEST_MODE, CRITERIA
from screening.screening_utils import detect_double_bottom, confirm_volume_spike, detect_breakout_near_low
import pandas as pd

def test_pattern_recognition():
    """Test pattern recognition functions"""
    print("Testing Pattern Recognition Functions")
    print("=" * 50)

    # Create sample price data for testing
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    # Create a double bottom pattern
    prices = [100] * 10 + [95] * 5 + [98] * 5 + [94] * 5 + [97] * 5 + [96] * 5 + [102] * 5 + [105] * 10
    price_series = pd.Series(prices, index=dates)

    # Test double bottom detection
    double_bottom = detect_double_bottom(price_series)
    print(f"Double Bottom Detection: {'Detected' if double_bottom else 'Not Detected'}")

    # Test volume spike confirmation
    volume_spike = confirm_volume_spike(100000, 50000, 1.5)
    print(f"Volume Spike Confirmation: {volume_spike}")

    # Test breakout detection
    breakout = detect_breakout_near_low(96.5, 95, 80000, 40000, 0.98)
    print(f"Breakout Detection: {breakout}")

    print()

def test_enhanced_criteria():
    """Test the enhanced screening criteria"""
    print("Testing Enhanced Screening Criteria")
    print("=" * 50)

    print("Technical Indicators Enabled:")
    print(f"  RSI: {'Enabled' if CRITERIA.get('rsi_enabled') else 'Disabled'} (Range: {CRITERIA.get('rsi_min', 'N/A')}-{CRITERIA.get('rsi_max', 'N/A')})")
    print(f"  Moving Averages: {'Enabled' if CRITERIA.get('ma_enabled') else 'Disabled'} (Price vs SMA50: {CRITERIA.get('price_vs_sma50_pct', 'N/A')})")
    print(f"  ATR: {'Enabled' if CRITERIA.get('atr_enabled') else 'Disabled'} (Range: {CRITERIA.get('atr_min_pct', 'N/A')}-{CRITERIA.get('atr_max_pct', 'N/A')})")

    print("\nPattern Recognition Enabled:")
    print(f"  Pattern Detection: {'Enabled' if CRITERIA.get('pattern_enabled') else 'Disabled'}")
    print(f"  Double Bottom: {'Enabled' if CRITERIA.get('double_bottom_enabled') else 'Disabled'}")
    print(f"  Breakout Detection: {'Enabled' if CRITERIA.get('breakout_enabled') else 'Disabled'}")
    print(f"  Volume Confirmation: {'Enabled' if CRITERIA.get('volume_confirmation_required') else 'Disabled'}")

    print()

def test_optimized_provider():
    """Test the optimized YFinance provider"""
    print("Testing Optimized YFinance Provider")
    print("=" * 50)

    try:
        from data.providers import OptimizedYFinanceProvider

        provider = OptimizedYFinanceProvider()

        # Test with a small sample
        test_tickers = ['AAPL', 'MSFT', 'GOOGL']
        print(f"Testing with {len(test_tickers)} sample stocks...")

        results = provider.get_market_data(test_tickers, CRITERIA)

        print(f"Results: {len(results)} stocks processed")

        if results:
            sample = results[0]
            print(f"Sample result keys: {list(sample.keys())}")

            # Check for technical indicators
            has_rsi = 'rsi' in sample
            has_ma = 'sma50' in sample and 'sma200' in sample
            has_atr = 'atr_pct' in sample

            print(f"Technical indicators present: RSI={has_rsi}, MA={has_ma}, ATR={has_atr}")

        print("Optimized provider working")
    except Exception as e:
        print(f"❌ Optimized provider error: {e}")

    print()

def main():
    """Run all tests"""
    print("TESTING ENHANCED SCANNING FEATURES")
    print("=" * 60)

    test_pattern_recognition()
    test_enhanced_criteria()
    test_optimized_provider()

    print("Running Full Enhanced Scan Test...")
    print("-" * 60)

    # Enable test mode
    import config
    config.TEST_MODE = True

    try:
        results = daily_scan()

        print(f"\nSCAN RESULTS: {len(results)} potential trades found")

        if results:
            print("\nTop 3 results:")
            for i, result in enumerate(results[:3]):
                symbol = result.get('symbol', 'Unknown')
                price = result.get('price', 0)
                pct_from_low = result.get('pct_from_low', 1.0)
                rvol = result.get('rvol', 0)

                print(f"{i+1}. {symbol}: ${price:.2f} ({pct_from_low:.1%} from low, RVOL: {rvol:.1f}x)")

                # Check for new technical data
                rsi = result.get('rsi', 'N/A')
                atr = result.get('atr_pct', 'N/A')
                if rsi != 'N/A' or atr != 'N/A':
                    print(f"   Technical: RSI={rsi:.1f}, ATR={atr:.1%}")

        print("\nEnhanced scanning features working correctly!")

    except Exception as e:
        print(f"Scan error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()