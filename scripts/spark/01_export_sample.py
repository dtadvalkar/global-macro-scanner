"""
Phase 2 — Export bounded prices_daily sample to Parquet.

Pulls 50 NSE tickers (alphabetical, with full 1-year coverage) for the window
2025-04-17..2026-04-17 from Postgres and writes a single Parquet file.

Output: data_files/spark/prices_daily_sample.parquet
"""

import pandas as pd
from db import get_db
from pathlib import Path

AS_OF_DATE = "2026-04-17"
WINDOW_START = "2025-04-17"
TICKER_LIMIT = 50
MIN_TRADING_DAYS = 240

OUT_PATH = Path("data_files/spark/prices_daily_sample.parquet")


def main():
    db = get_db()

    eligible = db.query_file(
        'analytics/eligible_tickers_window.sql',
        ("%.NS", WINDOW_START, AS_OF_DATE, MIN_TRADING_DAYS, TICKER_LIMIT),
    )
    tickers = [r[0] for r in eligible]
    print(f"Selected {len(tickers)} NSE tickers (min {MIN_TRADING_DAYS} trading days in window)")

    rows = db.query_file(
        'analytics/prices_daily_window.sql',
        (tickers, WINDOW_START, AS_OF_DATE),
    )

    df = pd.DataFrame(
        rows, columns=["ticker", "price_date", "open", "high", "low", "close", "volume"]
    )
    print(f"Exported {len(df)} rows; per-ticker mean = {len(df)/len(tickers):.1f}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
