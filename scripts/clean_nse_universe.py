#!/usr/bin/env python3
"""
Clean NSE Universe - Remove delisted and invalid stocks
This will solve the "error 200" issues by ensuring we only process valid stocks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
from datetime import datetime
from db import get_db

def validate_stock(symbol, quick_check=True):
    """
    Validate if a stock is active and has data available

    Returns: (is_valid: bool, reason: str)
    """
    try:
        ticker = yf.Ticker(symbol)

        if quick_check:
            # Quick check with minimal data
            hist = ticker.history(period='5d')
            if hist.empty or len(hist) < 3:
                return False, "No recent trading data"

            # Check if ticker info exists
            info = ticker.info
            if not info or info.get('regularMarketPrice') is None:
                return False, "No market data available"
        else:
            # Full check with 1 year of data
            hist = ticker.history(period='1y')
            if hist.empty or len(hist) < 200:  # ~1 year of trading days
                return False, "Insufficient historical data"

        return True, "Valid stock"

    except Exception as e:
        error_str = str(e).lower()
        if 'delisted' in error_str or 'not found' in error_str or '404' in str(e):
            return False, f"Delisted or not found: {str(e)[:50]}"
        else:
            return False, f"Error: {str(e)[:50]}"

def clean_nse_universe(batch_size=100, max_stocks=None):
    """
    Clean the NSE universe by validating stocks and updating database
    """
    print("CLEANING NSE UNIVERSE")
    print("=" * 60)
    print("This will validate all NSE stocks and remove invalid/delisted ones")
    print("This may take several minutes...")

    # Get current NSE universe
    db = get_db()
    try:
        result = db.query(
            "SELECT ticker FROM tickers WHERE exchange = %s ORDER BY ticker",
            ('NSE',),
        )
        all_stocks = [row[0] for row in result]
    except Exception as e:
        print(f"Error loading NSE universe: {e}")
        return

    if max_stocks:
        all_stocks = all_stocks[:max_stocks]

    print(f"Found {len(all_stocks)} NSE stocks to validate")

    valid_stocks = []
    invalid_stocks = []
    total_processed = 0

    # Process in batches
    for i in range(0, len(all_stocks), batch_size):
        batch = all_stocks[i:i+batch_size]
        print(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} stocks)...")

        batch_valid = []
        batch_invalid = []

        for j, symbol in enumerate(batch):
            if (j+1) % 20 == 0:
                print(f"  Progress: {j+1}/{len(batch)} in current batch")

            is_valid, reason = validate_stock(symbol, quick_check=True)

            if is_valid:
                batch_valid.append(symbol)
            else:
                batch_invalid.append((symbol, reason))
                print(f"    ❌ {symbol}: {reason}")

        valid_stocks.extend(batch_valid)
        invalid_stocks.extend(batch_invalid)
        total_processed += len(batch)

        print(f"  Batch complete: {len(batch_valid)} valid, {len(batch_invalid)} invalid")

        # Small delay between batches to be respectful to YFinance
        import time
        time.sleep(2)

    # Update database
    print(f"\nUPDATING DATABASE...")
    print(f"  Total processed: {total_processed}")
    print(f"  Valid stocks: {len(valid_stocks)}")
    print(f"  Invalid stocks: {len(invalid_stocks)}")

    try:
        # Mark invalid stocks as inactive (commented-out DELETE option intentionally
        # not migrated; if the destructive option is ever wanted, externalize it
        # to sql/etl/ first per DEVELOPMENT.md).
        if invalid_stocks:
            invalid_tickers = [stock for stock, reason in invalid_stocks]
            placeholders = ','.join(['%s'] * len(invalid_tickers))
            db.execute(
                f"UPDATE tickers SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP "
                f"WHERE ticker IN ({placeholders}) AND exchange = 'NSE'",
                invalid_tickers,
            )
            print(f"  Marked {len(invalid_tickers)} invalid stocks as inactive")

        if valid_stocks:
            placeholders = ','.join(['%s'] * len(valid_stocks))
            db.execute(
                f"UPDATE tickers SET is_active = TRUE, updated_at = CURRENT_TIMESTAMP "
                f"WHERE ticker IN ({placeholders}) AND exchange = 'NSE'",
                valid_stocks,
            )
            print(f"  Ensured {len(valid_stocks)} valid stocks are marked active")

        db.execute_file('schema/universe_cleanup_log.sql')
        db.execute_file(
            'etl/universe_cleanup_log_insert.sql',
            (
                'NSE',
                total_processed,
                len(valid_stocks),
                len(invalid_stocks),
                f'Cleaned NSE universe. Invalid stocks: {len(invalid_stocks[:5])}...',
            ),
        )

        print("✅ Database updated successfully")

    except Exception as e:
        print(f"❌ Database update error: {e}")

    # Summary
    print(f"\n🎯 CLEANUP SUMMARY")
    print(f"=" * 40)
    print(f"Total NSE stocks processed: {total_processed}")
    print(f"Valid/active stocks: {len(valid_stocks)} ({len(valid_stocks)/total_processed*100:.1f}%)")
    print(f"Invalid/delisted stocks: {len(invalid_stocks)} ({len(invalid_stocks)/total_processed*100:.1f}%)")

    if invalid_stocks:
        print(f"\nSample invalid stocks removed:")
        for stock, reason in invalid_stocks[:5]:
            print(f"  {stock}: {reason}")

    print(f"\n✅ NSE universe cleanup complete!")
    print(f"Future scans will only process valid stocks, eliminating 'error 200' issues.")

def test_cleaned_universe():
    """Test that cleaned universe only contains valid stocks"""
    print(f"\n🧪 TESTING CLEANED UNIVERSE")
    print(f"=" * 40)

    try:
        db = get_db()
        # Get active NSE stocks
        result = db.query(
            "SELECT ticker FROM tickers WHERE exchange = %s AND is_active = TRUE ORDER BY ticker",
            ('NSE',),
        )
        active_stocks = [row[0] for row in result]

        print(f"Active NSE stocks in database: {len(active_stocks)}")

        if active_stocks:
            # Test first 10 active stocks
            test_stocks = active_stocks[:10]
            print(f"Testing first {len(test_stocks)} active stocks...")

            valid_count = 0
            for symbol in test_stocks:
                is_valid, reason = validate_stock(symbol, quick_check=True)
                if is_valid:
                    valid_count += 1
                else:
                    print(f"  ❌ {symbol}: Still invalid after cleanup - {reason}")

            success_rate = valid_count / len(test_stocks) * 100
            print(f"Validation success rate: {success_rate:.1f}%")

            if success_rate >= 90:
                print("✅ Cleanup successful - universe is clean!")
            else:
                print("⚠️  Some stocks still invalid - may need manual review")

    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Clean NSE universe by removing delisted stocks')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for processing')
    parser.add_argument('--max-stocks', type=int, default=None, help='Maximum stocks to process (for testing)')
    parser.add_argument('--test-only', action='store_true', help='Only test current universe without cleaning')

    args = parser.parse_args()

    if args.test_only:
        test_cleaned_universe()
    else:
        clean_nse_universe(batch_size=args.batch_size, max_stocks=args.max_stocks)
        test_cleaned_universe()