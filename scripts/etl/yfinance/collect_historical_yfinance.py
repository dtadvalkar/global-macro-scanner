"""
collect_historical_yfinance.py

One-time script to collect 10 years of historical OHLCV data for the
curated 398 tickers in stock_fundamentals, using a single bulk YFinance
download. Populates prices_daily. Safe to re-run — ON CONFLICT updates
existing rows and refreshes datetimestamp.

USAGE:
    python scripts/etl/yfinance/collect_historical_yfinance.py
    python scripts/etl/yfinance/collect_historical_yfinance.py --period 5y
"""

import argparse
import sys
import os
import io
import time
import psycopg2

sys.path.append(os.getcwd())
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.settings import DB_CONFIG
from scripts.etl.yfinance.collect_daily_yfinance import ingest_multi_ohlcv, bulk_insert_prices

DB_URL = (
    f"postgresql://{DB_CONFIG['db_user']}:{DB_CONFIG['db_pass']}"
    f"@{DB_CONFIG['db_host']}:{DB_CONFIG['db_port']}/{DB_CONFIG['db_name']}"
)

PERIOD = "10y"


def get_fundamentals_tickers(conn) -> list[str]:
    """Return all tickers from stock_fundamentals (curated NSE universe)."""
    with conn.cursor() as cur:
        cur.execute("SELECT ticker FROM stock_fundamentals ORDER BY ticker")
        return [r[0] for r in cur.fetchall()]


def main():
    parser = argparse.ArgumentParser(
        description="One-time historical OHLCV backfill for curated stock_fundamentals tickers."
    )
    parser.add_argument(
        "--period",
        default=PERIOD,
        help=f"yfinance period string (default: {PERIOD}). Examples: 5y, 10y, max.",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("HISTORICAL YFINANCE DATA COLLECTION")
    print("=" * 70)
    print(f"Source : stock_fundamentals (curated NSE universe)")
    print(f"Target : prices_daily")
    print(f"Period : {args.period}")
    print(f"Safe   : ON CONFLICT (ticker, price_date) DO UPDATE")
    print("=" * 70)

    try:
        conn = psycopg2.connect(DB_URL)
    except Exception as e:
        print(f"❌ DB connection failed: {e}")
        sys.exit(1)

    tickers = get_fundamentals_tickers(conn)
    total = len(tickers)
    print(f"\nFound {total} tickers in stock_fundamentals")
    print(f"Sample: {tickers[:5]}")

    if total == 0:
        print("❌ No tickers found — aborting.")
        conn.close()
        sys.exit(1)

    print(f"\nStarting bulk download ({args.period} × {total} tickers)...")
    t0 = time.time()

    try:
        df = ingest_multi_ohlcv(tickers, args.period)
    except Exception as e:
        print(f"❌ Download failed: {e}")
        conn.close()
        sys.exit(1)

    if df.empty:
        print("❌ No data returned from YFinance — nothing inserted.")
        conn.close()
        sys.exit(1)

    try:
        bulk_insert_prices(conn, df)
    except Exception as e:
        print(f"❌ Insert failed: {e}")
        conn.close()
        sys.exit(1)

    duration = time.time() - t0
    print(f"\nDuration : {duration:.1f}s")
    print("=" * 70)
    print("COLLECTION COMPLETE")
    print("=" * 70)
    print("Next: PYTHONPATH='.' python scripts/testing/check_progress.py")

    conn.close()


if __name__ == "__main__":
    main()
