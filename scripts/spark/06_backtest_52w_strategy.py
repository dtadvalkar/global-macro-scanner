r"""Offline backtest for the 52-week-low scanner strategy (v1 + v2).

Reads OHLCV from prices_daily, joins market metadata from tickers and
USD market cap from stock_fundamentals, and replays the screener's
filters on a per-day basis. For each emitted signal it records the
forward close at +5 / +10 / +20 trading rows so downstream analysis can
compute hit rates and average returns.

`--filter-set core` (default) mirrors the IMPLEMENTED / CLIENT-SIDE
subset of `screening/screening_utils.should_pass_screening`:
52-week-low proximity, 52-week-high ceiling, days-since-low window,
volume / rvol-or-volume gate, 20-day average-volume floor, price range,
and per-market USD market-cap floor.

`--filter-set technical` adds rolling RSI(14), SMA50, SMA200 and
ATR(14) checks using thresholds from `config/criteria.py`. Pattern
recognition is out of scope.

`--dedupe-events` collapses contiguous per-ticker signal runs to the
first row of each event.

`--dedupe-nvdr` collapses Thai SET ordinary/NVDR collisions on the same
date using the same policy as `screener.core.dedupe_set_nvdr_results`.

`--transaction-bps N` deducts N basis points from every forward return
as a round-trip cost.

No live providers are used: the data path is Postgres only. Outputs
land in a gitignored data_files/spark/ subdirectory.

Usage examples (PowerShell):

    $env:PYTHONPATH='.'
    .\.venv\Scripts\python.exe scripts\spark\06_backtest_52w_strategy.py `
        --sample-tickers 50 --start-date 2024-01-01 --end-date 2026-04-30

    .\.venv\Scripts\python.exe scripts\spark\06_backtest_52w_strategy.py `
        --markets NSE,IDX,SET --start-date 2024-01-01 --end-date 2026-04-30 `
        --filter-set technical --dedupe-events --dedupe-nvdr --transaction-bps 20
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, date, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Repo root on sys.path so `from db import get_db` and `from config...` work
# even when this script is invoked from scripts/spark/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from db import get_db                                                       # noqa: E402
from config import CRITERIA                                                  # noqa: E402
from config.markets import get_min_market_cap                                # noqa: E402

DEFAULT_OUTPUT_DIR = Path("data_files/spark/backtest_52w")
DEFAULT_MARKETS = ["NSE", "IDX", "SET"]
DEFAULT_HORIZONS = [5, 10, 20]
LOOKBACK_TRADING_DAYS = 252  # ~1 year of trading days; matches CRITERIA['min_history_days']=250 with a small cushion
TECHNICAL_WARMUP = 200  # SMA200 window dominates technical-feature warmup

# Strategy thresholds sourced from config/criteria.py where practical, with
# explicit fallbacks so this script is self-documenting if criteria.py grows.
PRICE_52W_LOW_PCT = CRITERIA.get("price_52w_low_pct", 1.03)
PRICE_52W_HIGH_PCT = CRITERIA.get("price_52w_high_pct", 0.50)
MIN_DAYS_SINCE_LOW = CRITERIA.get("min_days_since_low", 1)
MAX_DAYS_SINCE_LOW = CRITERIA.get("max_days_since_low", 30)
MIN_VOLUME = CRITERIA.get("min_volume", 50_000)
MIN_RVOL = CRITERIA.get("min_rvol", 2.0)
MIN_AVG_VOLUME_20D = CRITERIA.get("min_avg_volume_20d", 50_000)
MIN_PRICE = CRITERIA.get("min_price", 1.0)
MAX_PRICE = CRITERIA.get("max_price", 1000.0)

# Technical thresholds (used only when --filter-set=technical).
RSI_MIN = CRITERIA.get("rsi_min", 20)
RSI_MAX = CRITERIA.get("rsi_max", 50)
PRICE_VS_SMA50_PCT = CRITERIA.get("price_vs_sma50_pct", 0.95)
SMA50_VS_SMA200_PCT = CRITERIA.get("sma50_vs_sma200_pct", 0.93)
ATR_MIN_PCT = CRITERIA.get("atr_min_pct", 0.015)
ATR_MAX_PCT = CRITERIA.get("atr_max_pct", 0.08)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_prices(markets, start_date, end_date, sample_tickers=None):
    """Load OHLCV rows for the requested markets and date window.

    Returns a (prices_df, ticker_market_map) pair. `ticker_market_map` is a
    dict {ticker: market} used downstream to resolve the per-market cap
    threshold without re-joining tickers in pandas.
    """
    db = get_db()
    rows = db.query_file(
        "analytics/prices_daily_by_markets.sql",
        (list(markets), start_date, end_date),
    )
    if not rows:
        return pd.DataFrame(), {}

    df = pd.DataFrame(
        rows,
        columns=["market", "ticker", "price_date", "open", "high", "low", "close", "volume"],
    )

    if sample_tickers is not None and sample_tickers > 0:
        # Deterministic sample: first N tickers per market alphabetical.
        keep = (
            df[["market", "ticker"]]
            .drop_duplicates()
            .sort_values(["market", "ticker"])
            .groupby("market", as_index=False)
            .head(sample_tickers)
        )
        df = df.merge(keep, on=["market", "ticker"], how="inner")

    df = df.sort_values(["ticker", "price_date"]).reset_index(drop=True)
    # Decimal -> float; bigint -> int64.
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype("int64")

    ticker_market = (
        df[["ticker", "market"]].drop_duplicates().set_index("ticker")["market"].to_dict()
    )
    return df, ticker_market


def load_mcap(tickers):
    """Return {ticker: mkt_cap_usd} for tickers with a positive cap."""
    if not tickers:
        return {}
    db = get_db()
    rows = db.query_file("analytics/stock_fundamentals_mcap.sql", (list(tickers),))
    return {t: float(m) for t, m in rows} if rows else {}


# ---------------------------------------------------------------------------
# Per-ticker signal generation (vectorised pandas)
# ---------------------------------------------------------------------------


def _trailing_argmin_offsets(arr: np.ndarray, window: int) -> np.ndarray:
    """Relative index of first minimum within each trailing `window` slice.

    Returns an array of length `len(arr) - window + 1` where element i is the
    argmin (first occurrence) of `arr[i:i+window]`. Mirrors pandas
    `Series.idxmin()` tie-break (first label).
    """
    from numpy.lib.stride_tricks import sliding_window_view

    windows = sliding_window_view(arr, window)
    return np.argmin(windows, axis=1)


def compute_technical_features(pdf: pd.DataFrame) -> pd.DataFrame:
    """Add rsi_14, sma_50, sma_200, price_vs_sma50_pct, sma50_vs_sma200_pct,
    and atr_pct columns to a single-ticker price frame.

    Pure function -- safe to call from tests without touching the DB.
    """
    close = pdf["close"]
    high = pdf["high"]
    low = pdf["low"]

    # Wilder-style RSI(14) computed with simple rolling means (matches the
    # screening_utils.calculate_rsi implementation, which the production
    # screener uses; sticking with the same formula keeps the backtest
    # comparable to the live screener).
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=14, min_periods=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=14, min_periods=14).mean()
    rs = gain / loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # When loss is 0 over the window, rs = inf and rsi resolves to 100 -- correct.
    # When both gain and loss are 0 (flat price), rs is NaN. Treat as 50 (neutral).
    rsi = rsi.where(~((gain == 0) & (loss == 0)), 50.0)

    sma50 = close.rolling(window=50, min_periods=50).mean()
    sma200 = close.rolling(window=200, min_periods=200).mean()

    with np.errstate(divide="ignore", invalid="ignore"):
        price_vs_sma50_pct = close / sma50
        sma50_vs_sma200_pct = sma50 / sma200

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr_14 = tr.rolling(window=14, min_periods=14).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        atr_pct = atr_14 / close

    out = pdf.copy()
    out["rsi_14"] = rsi.to_numpy()
    out["sma_50"] = sma50.to_numpy()
    out["sma_200"] = sma200.to_numpy()
    out["price_vs_sma50_pct"] = price_vs_sma50_pct.to_numpy()
    out["sma50_vs_sma200_pct"] = sma50_vs_sma200_pct.to_numpy()
    out["atr_pct"] = atr_pct.to_numpy()
    return out


def per_ticker_signals(pdf: pd.DataFrame, horizons, include_technical: bool = False) -> pd.DataFrame:
    """Compute signals + forward returns for one ticker's full history.

    When include_technical=True, also computes RSI/SMA50/SMA200/ATR
    features and applies the technical filter on top of the core mask.
    """
    pdf = pdf.sort_values("price_date").reset_index(drop=True)
    n = len(pdf)
    if n < LOOKBACK_TRADING_DAYS + 1:
        return pd.DataFrame()  # not enough history for any signal

    close = pdf["close"].to_numpy()
    low = pdf["low"].to_numpy()
    volume = pdf["volume"].to_numpy()

    # Rolling features. For a row to be a candidate signal, the full
    # LOOKBACK_TRADING_DAYS window must be available (no partial windows).
    low_52w_series = pdf["low"].rolling(LOOKBACK_TRADING_DAYS, min_periods=LOOKBACK_TRADING_DAYS).min()
    high_52w_series = pdf["high"].rolling(LOOKBACK_TRADING_DAYS, min_periods=LOOKBACK_TRADING_DAYS).max()
    avg_vol_20d_series = pdf["volume"].rolling(20, min_periods=20).mean()
    avg_vol_30d_series = pdf["volume"].rolling(30, min_periods=30).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rvol_series = np.where(avg_vol_30d_series > 0, volume / avg_vol_30d_series.to_numpy(), 0.0)

    # Days-since-low: for each row r with a full LOOKBACK window, find the
    # date of the first occurrence of the rolling min within rows
    # [r - LOOKBACK + 1, r].
    days_since_low = np.full(n, np.nan)
    if n >= LOOKBACK_TRADING_DAYS:
        argmin_offsets = _trailing_argmin_offsets(low, LOOKBACK_TRADING_DAYS)
        end_rows = np.arange(n - LOOKBACK_TRADING_DAYS + 1) + (LOOKBACK_TRADING_DAYS - 1)
        low_abs_rows = np.arange(n - LOOKBACK_TRADING_DAYS + 1) + argmin_offsets
        date_np = pd.to_datetime(pdf["price_date"]).to_numpy()
        diffs = (date_np[end_rows] - date_np[low_abs_rows]).astype("timedelta64[D]").astype(np.int32)
        days_since_low[end_rows] = diffs

    # Forward closes / returns. Shift(-h) puts the future close on the signal row.
    fwd_returns = {}
    for h in horizons:
        fwd_close = pd.Series(close).shift(-h)
        with np.errstate(divide="ignore", invalid="ignore"):
            fwd_returns[h] = (fwd_close.to_numpy() / close) - 1.0

    # Build a candidate frame on every row, then filter to signal rows. The
    # signal filter mirrors should_pass_screening's CLIENT-SIDE block.
    pct_from_low = close / low_52w_series.to_numpy()
    pct_from_high = close / high_52w_series.to_numpy()

    vol_ok = (volume >= MIN_VOLUME) | (rvol_series >= MIN_RVOL)
    cap_window = low_52w_series.notna().to_numpy()

    core_sig = (
        (close > 0)
        & cap_window
        & (pct_from_low <= PRICE_52W_LOW_PCT)
        & (pct_from_high <= PRICE_52W_HIGH_PCT)
        & (days_since_low >= MIN_DAYS_SINCE_LOW)
        & (days_since_low <= MAX_DAYS_SINCE_LOW)
        & vol_ok
        & (avg_vol_20d_series.notna().to_numpy())
        & (avg_vol_20d_series.to_numpy() >= MIN_AVG_VOLUME_20D)
        & (close >= MIN_PRICE)
        & (close <= MAX_PRICE)
    )

    # Technical features (always computed when include_technical so they
    # land in the output frame; the filter narrows core_sig further when
    # include_technical=True).
    rsi_vals = sma50_vals = sma200_vals = vs50_vals = vs200_vals = atr_vals = None
    if include_technical:
        feats = compute_technical_features(pdf)
        rsi_vals = feats["rsi_14"].to_numpy()
        sma50_vals = feats["sma_50"].to_numpy()
        sma200_vals = feats["sma_200"].to_numpy()
        vs50_vals = feats["price_vs_sma50_pct"].to_numpy()
        vs200_vals = feats["sma50_vs_sma200_pct"].to_numpy()
        atr_vals = feats["atr_pct"].to_numpy()

        tech_sig = (
            np.isfinite(rsi_vals)
            & (rsi_vals >= RSI_MIN)
            & (rsi_vals <= RSI_MAX)
            & np.isfinite(vs50_vals)
            & (vs50_vals >= PRICE_VS_SMA50_PCT)
            & np.isfinite(vs200_vals)
            & (vs200_vals >= SMA50_VS_SMA200_PCT)
            & np.isfinite(atr_vals)
            & (atr_vals >= ATR_MIN_PCT)
            & (atr_vals <= ATR_MAX_PCT)
        )
        core_sig = core_sig & tech_sig

    idx = np.flatnonzero(core_sig)
    if idx.size == 0:
        return pd.DataFrame()

    out = pd.DataFrame(
        {
            "ticker": pdf["ticker"].iloc[idx].to_numpy(),
            "market": pdf["market"].iloc[idx].to_numpy(),
            "signal_date": pdf["price_date"].iloc[idx].to_numpy(),
            "bar_index": idx.astype(np.int64),
            "entry_price": close[idx],
            "low_52w": low_52w_series.to_numpy()[idx],
            "high_52w": high_52w_series.to_numpy()[idx],
            "pct_from_low": pct_from_low[idx],
            "pct_from_high": pct_from_high[idx],
            "days_since_low": days_since_low[idx].astype(np.int32),
            "volume": volume[idx],
            "avg_volume_20d": avg_vol_20d_series.to_numpy()[idx],
            "rvol": rvol_series[idx],
        }
    )
    if include_technical:
        out["rsi_14"] = rsi_vals[idx]
        out["sma_50"] = sma50_vals[idx]
        out["sma_200"] = sma200_vals[idx]
        out["price_vs_sma50_pct"] = vs50_vals[idx]
        out["sma50_vs_sma200_pct"] = vs200_vals[idx]
        out["atr_pct"] = atr_vals[idx]
    for h in horizons:
        out[f"fwd_return_{h}d"] = fwd_returns[h][idx]
    return out


def generate_signals(prices_df, horizons, include_technical=False):
    """Run per-ticker signal generation across the loaded universe."""
    if prices_df.empty:
        return pd.DataFrame()

    parts = []
    for ticker, group in prices_df.groupby("ticker", sort=False):
        part = per_ticker_signals(group, horizons, include_technical=include_technical)
        if not part.empty:
            parts.append(part)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


# ---------------------------------------------------------------------------
# Post-filter pipeline
# ---------------------------------------------------------------------------


def apply_market_cap_filter(signals_df, mcap_by_ticker):
    """Annotate signals with mkt_cap_usd and drop rows below the per-market floor."""
    if signals_df.empty:
        signals_df = signals_df.copy()
        signals_df["mkt_cap_usd"] = pd.Series(dtype=float)
        return signals_df, {"with_mcap": 0, "missing_mcap": 0, "below_threshold": 0}

    out = signals_df.copy()
    out["mkt_cap_usd"] = out["ticker"].map(mcap_by_ticker).astype(float)
    out["min_mcap_threshold"] = out["market"].map(
        lambda m: float(get_min_market_cap(m))
    )

    missing_mask = out["mkt_cap_usd"].isna()
    below_mask = (~missing_mask) & (out["mkt_cap_usd"] < out["min_mcap_threshold"])
    keep = (~missing_mask) & (~below_mask)

    stats = {
        "with_mcap": int((~missing_mask).sum()),
        "missing_mcap": int(missing_mask.sum()),
        "below_threshold": int(below_mask.sum()),
    }
    return out.loc[keep].drop(columns=["min_mcap_threshold"]).reset_index(drop=True), stats


def dedupe_events(signals_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse contiguous per-ticker signal runs to the first row per event.

    `bar_index` is the per-ticker integer position in the sorted price
    history. Two signals on the same ticker with bar indices differing by
    exactly 1 are the same event.
    """
    if signals_df.empty:
        return signals_df

    df = signals_df.sort_values(["ticker", "bar_index"]).reset_index(drop=True)
    prev_idx = df.groupby("ticker")["bar_index"].shift(1)
    is_first = prev_idx.isna() | ((df["bar_index"] - prev_idx) > 1)
    return df.loc[is_first].reset_index(drop=True)


def _set_group_key(ticker: str):
    """Match screener.core._set_group_key for backtest-side NVDR dedup."""
    if not isinstance(ticker, str):
        return None
    if ticker.endswith("-R.BK"):
        return ticker[: -len("-R.BK")] + ".BK"
    if ticker.endswith(".BK"):
        return ticker
    return None


def dedupe_nvdr(signals_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse SET ordinary/NVDR collisions on the same signal_date.

    Within each (signal_date, group_key) bucket where both an ordinary
    `.BK` and an NVDR `-R.BK` row exist, keep the row with the higher
    avg_volume_20d (fallback: higher volume; final tie-break: ordinary
    .BK). Rows whose ticker has no SET group key pass through.
    """
    if signals_df.empty:
        return signals_df

    df = signals_df.copy()
    df["_group_key"] = df["ticker"].map(_set_group_key)
    df["_is_nvdr"] = df["ticker"].fillna("").str.endswith("-R.BK")

    keep_mask = pd.Series(True, index=df.index)

    # Only consider rows that have a SET group key for dedup.
    set_rows = df[df["_group_key"].notna()]
    if not set_rows.empty:
        grouped = set_rows.groupby(["signal_date", "_group_key"], sort=False)
        for (_sig_date, _gk), group in grouped:
            if len(group) <= 1:
                continue
            has_ordinary = (~group["_is_nvdr"]).any()
            has_nvdr = group["_is_nvdr"].any()
            if not (has_ordinary and has_nvdr):
                continue

            # Rank: avg_volume_20d desc, volume desc, ordinary first.
            avg = group["avg_volume_20d"].fillna(-1.0).astype(float).to_numpy()
            vol = group["volume"].fillna(-1.0).astype(float).to_numpy()
            is_nvdr = group["_is_nvdr"].astype(bool).to_numpy()
            # Tuple max picks largest avg, then largest vol, then non-NVDR
            # (False < True so we want is_nvdr=False to win; invert via
            # ranking 0 for ordinary and -1 for NVDR).
            ranks = [
                (avg[i], vol[i], 0 if not is_nvdr[i] else -1, i)
                for i in range(len(group))
            ]
            best = max(ranks)
            best_local = best[3]
            best_idx = group.index.to_numpy()[best_local]

            for i in group.index:
                if i != best_idx:
                    keep_mask.loc[i] = False

    return df.loc[keep_mask].drop(columns=["_group_key", "_is_nvdr"]).reset_index(drop=True)


def apply_transaction_costs(signals_df: pd.DataFrame, horizons, bps: int) -> pd.DataFrame:
    """Deduct `bps / 10000` from every non-NaN fwd_return_*d column."""
    if bps == 0 or signals_df.empty:
        return signals_df
    cost = bps / 10_000.0
    out = signals_df.copy()
    for h in horizons:
        col = f"fwd_return_{h}d"
        if col in out.columns:
            out[col] = out[col] - cost
    return out


# ---------------------------------------------------------------------------
# Summary + sanity
# ---------------------------------------------------------------------------


def summarise(
    signals_df,
    horizons,
    start_date,
    end_date,
    *,
    filter_set,
    transaction_bps,
    stage_counts,
    mcap_filter_applied,
    mcap_stats,
    market_coverage,
    thresholds_used,
):
    summary = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requested_range": {"start": str(start_date), "end": str(end_date)},
        "filter_set": filter_set,
        "transaction_bps": transaction_bps,
        "market_cap_filter_applied": mcap_filter_applied,
        "stage_counts": stage_counts,
        "mcap_stats_before_filter": mcap_stats,
        "market_coverage": market_coverage,
        "totals": {
            "signals": int(len(signals_df)),
            "distinct_tickers": int(signals_df["ticker"].nunique()) if not signals_df.empty else 0,
            "min_signal_date": str(signals_df["signal_date"].min()) if not signals_df.empty else None,
            "max_signal_date": str(signals_df["signal_date"].max()) if not signals_df.empty else None,
        },
        "horizons": {},
        "per_market": {},
        "per_year": {},
        "thresholds_used": thresholds_used,
    }

    if signals_df.empty:
        return summary

    for h in horizons:
        col = f"fwd_return_{h}d"
        series = signals_df[col].dropna()
        summary["horizons"][f"{h}d"] = {
            "with_data": int(len(series)),
            "missing_future": int(signals_df[col].isna().sum()),
            "mean_return": float(series.mean()) if not series.empty else None,
            "median_return": float(series.median()) if not series.empty else None,
            "win_rate": float((series > 0).mean()) if not series.empty else None,
        }

    for market, group in signals_df.groupby("market"):
        row = {
            "signals": int(len(group)),
            "distinct_tickers": int(group["ticker"].nunique()),
            "horizons": {},
        }
        for h in horizons:
            series = group[f"fwd_return_{h}d"].dropna()
            row["horizons"][f"{h}d"] = {
                "with_data": int(len(series)),
                "mean_return": float(series.mean()) if not series.empty else None,
                "win_rate": float((series > 0).mean()) if not series.empty else None,
            }
        summary["per_market"][market] = row

    years = pd.to_datetime(signals_df["signal_date"]).dt.year
    for year, group in signals_df.groupby(years):
        row = {
            "signals": int(len(group)),
            "distinct_tickers": int(group["ticker"].nunique()),
            "horizons": {},
        }
        for h in horizons:
            series = group[f"fwd_return_{h}d"].dropna()
            row["horizons"][f"{h}d"] = {
                "with_data": int(len(series)),
                "mean_return": float(series.mean()) if not series.empty else None,
                "win_rate": float((series > 0).mean()) if not series.empty else None,
            }
        summary["per_year"][str(int(year))] = row

    return summary


def print_summary(summary, horizons):
    print("\n=== Backtest summary ===")
    totals = summary["totals"]
    print(f"Filter set      : {summary['filter_set']}")
    print(f"Transaction bps : {summary['transaction_bps']}")
    print(f"Requested range : {summary['requested_range']['start']} -> {summary['requested_range']['end']}")
    print(f"Signals         : {totals['signals']}")
    print(f"Distinct tickers: {totals['distinct_tickers']}")
    print(f"Signal range    : {totals['min_signal_date']} -> {totals['max_signal_date']}")
    print(f"mcap filter     : {'on' if summary['market_cap_filter_applied'] else 'off (diagnostic)'}")
    sc = summary["stage_counts"]
    print(
        "Stage counts    : "
        f"core={sc.get('core', '-')}  technical={sc.get('technical', '-')}  "
        f"mcap={sc.get('mcap', '-')}  event_dedup={sc.get('event_dedup', '-')}  "
        f"nvdr_dedup={sc.get('nvdr_dedup', '-')}"
    )

    if totals["signals"] == 0:
        return

    print("\nPer-horizon forward returns (after all enabled stages):")
    for h in horizons:
        row = summary["horizons"][f"{h}d"]
        mr = "n/a" if row["mean_return"] is None else f"{row['mean_return']*100:+.2f}%"
        md = "n/a" if row["median_return"] is None else f"{row['median_return']*100:+.2f}%"
        wr = "n/a" if row["win_rate"] is None else f"{row['win_rate']*100:.1f}%"
        print(
            f"  {h:>2}d: n={row['with_data']:>4}  mean={mr}  median={md}  win_rate={wr}"
            f"  (missing_future={row['missing_future']})"
        )

    print("\nPer-market breakdown:")
    for market, row in summary["per_market"].items():
        bits = []
        for h in horizons:
            hr = row["horizons"][f"{h}d"]
            mean_str = "n/a" if hr["mean_return"] is None else f"{hr['mean_return']*100:+.2f}%"
            win_str = "n/a" if hr["win_rate"] is None else f"{hr['win_rate']*100:.0f}%"
            bits.append(f"{h}d mean={mean_str} win={win_str}")
        print(
            f"  {market:<8} signals={row['signals']:>4} tickers={row['distinct_tickers']:>3}  "
            + "  ".join(bits)
        )


def run_sanity_checks(signals_df, start_date, end_date):
    issues = []
    if signals_df.empty:
        return issues
    n_total = len(signals_df)
    n_distinct = signals_df.drop_duplicates(subset=["ticker", "signal_date"]).shape[0]
    if n_distinct != n_total:
        issues.append(f"duplicate ticker/signal_date pairs: {n_total - n_distinct} extras")

    bad_dates = signals_df[
        (signals_df["signal_date"] < pd.to_datetime(start_date).date())
        | (signals_df["signal_date"] > pd.to_datetime(end_date).date())
    ]
    if len(bad_dates) > 0:
        issues.append(f"{len(bad_dates)} signals fall outside requested range")
    return issues


def thresholds_snapshot(include_technical: bool, transaction_bps: int) -> dict:
    base = {
        "lookback_trading_days": LOOKBACK_TRADING_DAYS,
        "price_52w_low_pct": PRICE_52W_LOW_PCT,
        "price_52w_high_pct": PRICE_52W_HIGH_PCT,
        "min_days_since_low": MIN_DAYS_SINCE_LOW,
        "max_days_since_low": MAX_DAYS_SINCE_LOW,
        "min_volume": MIN_VOLUME,
        "min_rvol": MIN_RVOL,
        "min_avg_volume_20d": MIN_AVG_VOLUME_20D,
        "min_price": MIN_PRICE,
        "max_price": MAX_PRICE,
        "transaction_bps": transaction_bps,
    }
    if include_technical:
        base.update({
            "rsi_min": RSI_MIN,
            "rsi_max": RSI_MAX,
            "price_vs_sma50_pct": PRICE_VS_SMA50_PCT,
            "sma50_vs_sma200_pct": SMA50_VS_SMA200_PCT,
            "atr_min_pct": ATR_MIN_PCT,
            "atr_max_pct": ATR_MAX_PCT,
        })
    return base


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(
        description="Offline 52-week-low strategy backtest (v1 + v2)."
    )
    parser.add_argument("--start-date", type=str, default="2024-01-01")
    parser.add_argument("--end-date", type=str, default=str(date.today()))
    parser.add_argument(
        "--markets",
        type=str,
        default=",".join(DEFAULT_MARKETS),
        help="Comma-separated markets (e.g. NSE,IDX,SET).",
    )
    parser.add_argument(
        "--sample-tickers",
        type=int,
        default=None,
        help="If set, restrict to first N tickers per market alphabetical (quick validation).",
    )
    parser.add_argument(
        "--horizons",
        type=str,
        default=",".join(str(h) for h in DEFAULT_HORIZONS),
        help="Comma-separated forward-return horizons in trading rows.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to write parquet + json summary.",
    )
    parser.add_argument(
        "--no-market-cap-filter",
        action="store_true",
        help="Skip the per-market mkt_cap_usd floor (diagnostic only).",
    )
    parser.add_argument(
        "--filter-set",
        choices=["core", "technical"],
        default="core",
        help="core (v1) or technical (v2: core + RSI/MA/ATR).",
    )
    parser.add_argument(
        "--dedupe-events",
        action="store_true",
        help="Collapse consecutive per-ticker signals to the first event.",
    )
    parser.add_argument(
        "--dedupe-nvdr",
        action="store_true",
        help="Collapse SET ordinary/NVDR (-R.BK) collisions on the same date.",
    )
    parser.add_argument(
        "--transaction-bps",
        type=int,
        default=0,
        help="Round-trip cost in basis points to subtract from every forward return.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    markets = [m.strip().upper() for m in args.markets.split(",") if m.strip()]
    horizons = [int(h) for h in args.horizons.split(",") if h.strip()]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    include_technical = (args.filter_set == "technical")

    if not os.environ.get("PYTHONPATH"):
        print("[hint] PYTHONPATH not set; using sys.path bump (see _REPO_ROOT).")

    print(
        f"Loading prices for markets={markets} window=[{args.start_date}, {args.end_date}]"
        + (f" sample_tickers={args.sample_tickers}" if args.sample_tickers else "")
    )
    t0 = time.time()
    prices_df, _ticker_market = load_prices(
        markets, args.start_date, args.end_date, args.sample_tickers
    )
    if prices_df.empty:
        print("WARNING: no price rows for the requested scope; aborting.")
        return 1
    print(
        f"  loaded {len(prices_df):,} rows / {prices_df['ticker'].nunique()} tickers in {time.time()-t0:.1f}s"
    )

    market_coverage = {}
    for market in markets:
        sub = prices_df[prices_df["market"] == market]
        if sub.empty:
            print(f"  WARNING: market {market} has no rows in scope")
            market_coverage[market] = {"tickers": 0, "rows": 0, "min_date": None, "max_date": None}
        else:
            market_coverage[market] = {
                "tickers": int(sub["ticker"].nunique()),
                "rows": int(len(sub)),
                "min_date": str(sub["price_date"].min()),
                "max_date": str(sub["price_date"].max()),
            }

    stage_counts = {}

    # Always run core signals so we can report the pre-technical count.
    print("Generating core signals (per-ticker, vectorised pandas)...")
    t0 = time.time()
    core_signals = generate_signals(prices_df, horizons, include_technical=False)
    stage_counts["core"] = int(len(core_signals))
    print(f"  core signals: {stage_counts['core']:,} (in {time.time()-t0:.1f}s)")

    if include_technical:
        print("Generating technical-filtered signals...")
        t0 = time.time()
        signals_df = generate_signals(prices_df, horizons, include_technical=True)
        stage_counts["technical"] = int(len(signals_df))
        print(
            f"  technical signals: {stage_counts['technical']:,} "
            f"(narrowed from {stage_counts['core']:,} in {time.time()-t0:.1f}s)"
        )
    else:
        signals_df = core_signals
        stage_counts["technical"] = None

    mcap_by_ticker = load_mcap(prices_df["ticker"].unique().tolist())
    if not args.no_market_cap_filter:
        coverage_pct = (
            100.0 * len(mcap_by_ticker) / max(1, prices_df["ticker"].nunique())
        )
        print(
            f"  mcap coverage: {len(mcap_by_ticker)}/{prices_df['ticker'].nunique()} "
            f"tickers have positive mkt_cap_usd ({coverage_pct:.1f}%)"
        )
        if coverage_pct < 80.0:
            print("  WARNING: market-cap coverage below 80%. Many tickers will be dropped.")
        signals_df, mcap_stats = apply_market_cap_filter(signals_df, mcap_by_ticker)
        stage_counts["mcap"] = int(len(signals_df))
        print(
            f"  post-mcap signals: {stage_counts['mcap']:,} "
            f"(dropped missing={mcap_stats['missing_mcap']} below_threshold={mcap_stats['below_threshold']})"
        )
        mcap_filter_applied = True
    else:
        print("  --no-market-cap-filter: skipping mkt_cap_usd floor (diagnostic only).")
        signals_df = signals_df.copy()
        if not signals_df.empty:
            signals_df["mkt_cap_usd"] = signals_df["ticker"].map(mcap_by_ticker).astype(float)
        mcap_stats = {"with_mcap": len(mcap_by_ticker), "missing_mcap": 0, "below_threshold": 0}
        stage_counts["mcap"] = int(len(signals_df))
        mcap_filter_applied = False

    if args.dedupe_events:
        before = len(signals_df)
        signals_df = dedupe_events(signals_df)
        stage_counts["event_dedup"] = int(len(signals_df))
        print(f"  event dedup: {before:,} -> {stage_counts['event_dedup']:,}")
    else:
        stage_counts["event_dedup"] = None

    if args.dedupe_nvdr:
        before = len(signals_df)
        signals_df = dedupe_nvdr(signals_df)
        stage_counts["nvdr_dedup"] = int(len(signals_df))
        print(f"  NVDR dedup : {before:,} -> {stage_counts['nvdr_dedup']:,}")
    else:
        stage_counts["nvdr_dedup"] = None

    if args.transaction_bps:
        signals_df = apply_transaction_costs(signals_df, horizons, args.transaction_bps)
        print(f"  transaction costs: subtracting {args.transaction_bps} bps from forward returns")

    issues = run_sanity_checks(signals_df, args.start_date, args.end_date)
    if issues:
        print("\nSanity check issues:")
        for line in issues:
            print(f"  - {line}")
    else:
        print("Sanity checks: ok.")

    if not signals_df.empty:
        for h in horizons:
            missing = int(signals_df[f"fwd_return_{h}d"].isna().sum())
            if missing > 0:
                print(
                    f"  note: {missing} signals lack +{h}d future close (end-of-window edge effect)."
                )

    signals_path = output_dir / "backtest_52w_signals.parquet"
    summary_path = output_dir / "backtest_52w_summary.json"
    signals_df.to_parquet(signals_path, index=False)
    print(f"\nWrote {signals_path} ({len(signals_df):,} rows)")

    summary = summarise(
        signals_df, horizons, args.start_date, args.end_date,
        filter_set=args.filter_set,
        transaction_bps=args.transaction_bps,
        stage_counts=stage_counts,
        mcap_filter_applied=mcap_filter_applied,
        mcap_stats=mcap_stats,
        market_coverage=market_coverage,
        thresholds_used=thresholds_snapshot(include_technical, args.transaction_bps),
    )
    summary["sanity_issues"] = issues
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Wrote {summary_path}")

    print_summary(summary, horizons)
    return 0


if __name__ == "__main__":
    sys.exit(main())
