#!/usr/bin/env python
# --------------------------------------------------------------
# collect_daily_yfinance.py
# --------------------------------------------------------------
# Purpose:
#   * Pull the active ticker list from the DB.
#   * Download OHLCV data from yfinance for a configurable period.
#   * Insert the rows into the already-existing `prices_daily` table.
#   * The table contains a `datetimestamp` column that is filled
#     automatically by PostgreSQL's DEFAULT NOW().
# --------------------------------------------------------------

import argparse
import sys
import pandas as pd
import yfinance as yf
from datetime import datetime
from pathlib import Path

# Add project root to path
import os
sys.path.append(os.getcwd())

from db import get_db


# ------------------------------------------------------------------
# Helper: fetch the list of active tickers from the DB
# ------------------------------------------------------------------
def fetch_active_tickers(markets: list[str] | None = None) -> list[str]:
    """Return a list of ticker symbols that are marked as active.

    If `markets` is provided (list of market codes like ['IDX', 'SET']),
    the query is scoped to those markets. Otherwise all active tickers
    across the universe are returned.
    """
    if markets:
        rows = get_db().query(
            "SELECT ticker FROM tickers "
            "WHERE market = ANY(%s) "
            "AND (status = 'ACTIVE' OR status IS NULL) "
            "ORDER BY ticker",
            (markets,),
        )
    else:
        rows = get_db().query(
            "SELECT ticker FROM tickers WHERE status = 'ACTIVE' OR status IS NULL"
        )
    return [r[0] for r in (rows or [])]


# ------------------------------------------------------------------
# Helper: reshape yfinance multi-ticker download into the flat schema
# ------------------------------------------------------------------
def flatten_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the multi-index DataFrame returned by yf.download into a
    flat table matching `prices_daily` columns:

        ticker, price_date, open, high, low, close, volume
    """
    # yfinance returns a DataFrame with columns like ('Open', 'High', ...) for each ticker.
    # We first stack the ticker level, then rename columns.
    if isinstance(df.columns, pd.MultiIndex):
        df = df.stack(level=0).reset_index()
        # After stack(level=0): date index retains name "Date";
        # stacked ticker level is named "Ticker" in yfinance >= 1.x.
        df = df.rename(
            columns={
                "Date": "price_date",
                "Ticker": "ticker",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
    else:
        # Single-ticker download - we still want the same column names.
        df = df.reset_index().rename(
            columns={
                "Date": "price_date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        # Add a dummy ticker column (the ticker string will be passed separately if single, 
        # but ingest_multi_ohlcv usually handles multiple)
        # If single ticker, 'ticker' might not be in columns if simplified.
        if "ticker" not in df.columns:
            # We don't easily know the ticker here if it's single.
            # But yf.download(..., group_by='ticker') usually forces multiindex or we handle it.
            pass

    # Ensure correct dtypes (PostgreSQL will coerce as needed)
    df["price_date"] = pd.to_datetime(df["price_date"]).dt.date
    numeric_cols = ["open", "high", "low", "close"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype("int64")
    
    # Filter for required columns
    return df[["ticker", "price_date", "open", "high", "low", "close", "volume"]]


# ------------------------------------------------------------------
# Core ETL function
# ------------------------------------------------------------------
def ingest_multi_ohlcv(tickers: list[str], period: str) -> pd.DataFrame:
    """
    Download OHLCV data for the supplied tickers and period,
    then flatten it to the final DataFrame.
    """
    if not tickers:
        raise ValueError("No active tickers found in the database.")

    # yfinance can handle a list of tickers (comma-separated string)
    ticker_str = " ".join(tickers)

    print(f"📥 Downloading data for {len(tickers)} tickers (period={period})...")
    
    # The `period` argument follows yfinance conventions:
    #   '1d', '5d', '7d', '1mo', '3mo', etc.
    raw = yf.download(
        tickers=ticker_str,
        period=period,
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=True,
    )
    
    if raw.empty:
        print("⚠️  yfinance returned empty data.")
        return pd.DataFrame()
        
    return flatten_ohlcv(raw)


# ------------------------------------------------------------------
# Bulk-insert helper - uses execute_values via sql/etl/prices_daily_upsert.sql
# ------------------------------------------------------------------
def bulk_insert_prices(df: pd.DataFrame):
    """Insert rows into `prices_daily`. `datetimestamp` is set by NOW() on upsert."""
    if df.empty:
        print("⚠️  No rows to insert - nothing to do.")
        return

    records = list(df.itertuples(index=False, name=None))
    get_db().execute_values_file('etl/prices_daily_upsert.sql', records)
    print(f"✅ Inserted/updated {len(records)} rows into prices_daily.")


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Collect daily YFinance OHLCV data and store it in prices_daily."
    )
    parser.add_argument(
        "--period",
        default="1d",
        help="yfinance period (e.g. 1d, 5d, 7d, 1mo). Default = 1d (daily run).",
    )
    parser.add_argument(
        "--exchange",
        "--markets",
        dest="exchange",
        default=None,
        help=(
            "Exchange code(s) to scope the collection to; comma-separated "
            "(e.g. IDX or IDX,SET). If omitted, all active tickers across "
            "every market are collected. Matches the historical collector's "
            "--exchange convention."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved ticker count and exit; do not download or write.",
    )
    args = parser.parse_args()

    markets = (
        [m.strip().upper() for m in args.exchange.split(",") if m.strip()]
        if args.exchange else None
    )

    # ------------------------------------------------------------------
    # 1. Pull active tickers
    # ------------------------------------------------------------------
    try:
        tickers = fetch_active_tickers(markets)
        scope = f"markets={markets}" if markets else "all markets"
        print(f"🔎 Found {len(tickers)} active tickers ({scope}).")
    except Exception as e:
        print(f"❌ Error fetching tickers: {e}")
        sys.exit(1)

    if not tickers:
        print("⚠️  No active tickers found. Exiting.")
        return

    if args.dry_run:
        sample = ", ".join(tickers[:8]) + (" ..." if len(tickers) > 8 else "")
        print(f"[dry-run] {len(tickers)} tickers to collect (period={args.period}): {sample}")
        return

    # ------------------------------------------------------------------
    # 2. Download & flatten data
    # ------------------------------------------------------------------
    try:
        df = ingest_multi_ohlcv(tickers, args.period)
    except Exception as exc:
        print(f"❌ yfinance download failed: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Bulk insert into the pre-created table
    # ------------------------------------------------------------------
    try:
        bulk_insert_prices(df)
    except Exception as e:
        print(f"❌ Database insert failed: {e}")


if __name__ == "__main__":
    main()
