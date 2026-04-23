"""
collect_historical_yfinance.py

Bulk-download historical OHLCV from yfinance into prices_daily.

Default mode (no --exchange): uses the curated 398-ticker NSE universe
from stock_fundamentals.

With --exchange: reads tickers from the tickers table for the given
exchange (seeded by scripts/etl/ibkr/seed_exchange_tickers.py) and
bulk-downloads history.

USAGE:
    python scripts/etl/yfinance/collect_historical_yfinance.py
    python scripts/etl/yfinance/collect_historical_yfinance.py --period 5y
    python scripts/etl/yfinance/collect_historical_yfinance.py --exchange SEHK
    python scripts/etl/yfinance/collect_historical_yfinance.py --exchange LSE --period 5y
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


def get_exchange_tickers(conn, exchange: str) -> list[str]:
    """Return active tickers from the tickers table for a given exchange."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT ticker FROM tickers WHERE market = %s AND (status = 'ACTIVE' OR status IS NULL) ORDER BY ticker",
            (exchange.upper(),),
        )
        return [r[0] for r in cur.fetchall()]


def main():
    parser = argparse.ArgumentParser(
        description="Bulk-download historical OHLCV from yfinance into prices_daily."
    )
    parser.add_argument(
        "--period",
        default=PERIOD,
        help=f"yfinance period string (default: {PERIOD}). Examples: 5y, 10y, max.",
    )
    parser.add_argument(
        "--exchange",
        default=None,
        help=(
            "Exchange code(s) to collect; comma-separated for multi-exchange "
            "(e.g. SEHK or SEHK,LSE,JSE,TADAWUL). Reads tickers from the "
            "tickers table, unions across exchanges, and issues ONE bulk "
            "yf.download call — safer than parallel processes against yfinance's "
            "rate limits. If omitted, uses stock_fundamentals (NSE curated universe)."
        ),
    )
    args = parser.parse_args()

    exchanges = (
        [e.strip().upper() for e in args.exchange.split(",") if e.strip()]
        if args.exchange else []
    )

    print("=" * 70)
    print("HISTORICAL YFINANCE DATA COLLECTION")
    print("=" * 70)
    if exchanges:
        print(f"Source : tickers table (markets = {', '.join(exchanges)})")
    else:
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

    if exchanges:
        tickers = []
        seen = set()
        for ex in exchanges:
            ex_tickers = get_exchange_tickers(conn, ex)
            print(f"  {ex}: {len(ex_tickers)} active tickers")
            for t in ex_tickers:
                if t not in seen:
                    seen.add(t)
                    tickers.append(t)
        print(f"\nFound {len(tickers)} unique tickers across {len(exchanges)} exchange(s)")
    else:
        tickers = get_fundamentals_tickers(conn)
        print(f"\nFound {len(tickers)} tickers in stock_fundamentals")

    total = len(tickers)
    if total > 0:
        print(f"Sample: {tickers[:5]}")

    if total == 0:
        if exchanges:
            source = f"tickers table (markets={','.join(exchanges)})"
        else:
            source = "stock_fundamentals"
        print(f"❌ No tickers found in {source} — aborting.")
        if exchanges:
            print(f"   Run: PYTHONPATH='.' python scripts/etl/ibkr/seed_exchange_tickers.py --exchanges {','.join(exchanges)}")
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

    conn.close()


if __name__ == "__main__":
    main()
