#!/usr/bin/env python3
"""
Quick setup check for YFinance historical data collection
"""

import sys
sys.path.append('.')

def check_imports():
    """Check if required packages are available"""
    try:
        import yfinance as yf
        print("OK yfinance: Available")
    except ImportError:
        print("ERROR yfinance: NOT INSTALLED")
        return False

    try:
        import psycopg2
        print("OK psycopg2: Available")
    except ImportError:
        print("ERROR psycopg2: NOT INSTALLED")
        return False

    try:
        from config import DB_CONFIG
        print("OK config: Available")
    except ImportError as e:
        print(f"ERROR config: Import failed - {e}")
        return False

    return True

def check_database():
    """Check database connectivity and stock_fundamentals table"""
    try:
        from config import DB_CONFIG
        import psycopg2

        conn = psycopg2.connect(dbname=DB_CONFIG['db_name'], user=DB_CONFIG['db_user'], password=DB_CONFIG['db_pass'], host=DB_CONFIG['db_host'], port=DB_CONFIG['db_port'])
        cur = conn.cursor()

        # Check stock_fundamentals table
        cur.execute("SELECT COUNT(*) FROM stock_fundamentals")
        fundamentals_count = cur.fetchone()[0]

        # Check prices_daily table (should exist but be empty for historical)
        cur.execute("SELECT COUNT(*) FROM prices_daily WHERE source = 'yf'")
        existing_yf_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        print(f"OK Database connection: OK")
        print(f"OK stock_fundamentals: {fundamentals_count} tickers")
        print(f"INFO Existing YFinance data: {existing_yf_count} rows")

        return fundamentals_count > 0

    except Exception as e:
        print(f"ERROR Database issue: {e}")
        return False

def check_script_imports():
    """Check if the collection script can import its dependencies"""
    try:
        from scripts.etl.yfinance.test_raw_ingestion import get_fundamentals_tickers, ingest_multi_ohlcv
        print("OK Script imports: OK")
        return True
    except ImportError as e:
        print(f"ERROR Script imports: Failed - {e}")
        return False

if __name__ == "__main__":
    print("SETUP CHECK FOR YFINANCE HISTORICAL DATA COLLECTION")
    print("=" * 60)

    checks_passed = 0
    total_checks = 3

    if check_imports():
        checks_passed += 1

    if check_database():
        checks_passed += 1

    if check_script_imports():
        checks_passed += 1

    print("=" * 60)
    if checks_passed == total_checks:
        print("ALL CHECKS PASSED - Ready to run collect_historical_yfinance.py")
        print("\nNext: python collect_historical_yfinance.py")
    else:
        print(f"WARNING {checks_passed}/{total_checks} checks passed - Fix issues before running")

    print("=" * 60)