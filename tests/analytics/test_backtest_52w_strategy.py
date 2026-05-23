"""Unit tests for scripts/spark/06_backtest_52w_strategy.py post-processing.

Synthetic pandas frames -- no DB, no live providers. Loads the backtest
module by file path because `scripts/spark/` is not an importable
package (no __init__.py and the file name starts with a digit).
"""

import importlib.util
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load_backtest_module():
    spec = importlib.util.spec_from_file_location(
        "backtest_52w_under_test",
        os.path.join(ROOT, "scripts", "spark", "06_backtest_52w_strategy.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


backtest = _load_backtest_module()


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------


def _synthetic_prices(ticker="X.BK", market="SET", n_days=350, seed=0,
                      base=100.0, drift=-0.05):
    """Return a single-ticker OHLCV frame long enough to clear the 252-day
    warmup with deterministic, generally-down-trending closes.
    """
    rng = np.random.default_rng(seed=seed)
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B").date
    noise = rng.normal(0, 0.5, n_days)
    closes = np.maximum(1.0, base + drift * np.arange(n_days) + noise.cumsum())
    highs = closes + np.abs(rng.normal(0, 0.4, n_days))
    lows = closes - np.abs(rng.normal(0, 0.4, n_days))
    opens = closes + rng.normal(0, 0.2, n_days)
    volumes = rng.integers(100_000, 1_000_000, n_days)
    return pd.DataFrame({
        "market": market,
        "ticker": ticker,
        "price_date": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })


# ---------------------------------------------------------------------------
# Required test cases
# ---------------------------------------------------------------------------


def test_technical_features_populated_after_warmup():
    """After the SMA200 warmup, all technical feature columns must hold
    finite values. Before warmup they should be NaN."""
    pdf = _synthetic_prices(n_days=300, seed=1)
    feats = backtest.compute_technical_features(pdf)

    # Rows below 199 (zero-indexed) cannot have SMA200; row 199 and onward must.
    early = feats.iloc[150]
    late = feats.iloc[250]

    assert pd.isna(early["sma_200"]) or not np.isfinite(early["sma_200"])
    assert np.isfinite(late["sma_50"])
    assert np.isfinite(late["sma_200"])
    assert np.isfinite(late["rsi_14"])
    assert np.isfinite(late["atr_pct"])
    assert np.isfinite(late["price_vs_sma50_pct"])
    assert np.isfinite(late["sma50_vs_sma200_pct"])


def test_technical_filter_narrows_or_equals_core_count():
    """On the same synthetic frame, technical-filtered signals must be a
    subset of core signals (count <= core count)."""
    pdf = _synthetic_prices(n_days=320, seed=7, base=100.0, drift=-0.1)
    core = backtest.per_ticker_signals(pdf, horizons=[5, 10], include_technical=False)
    tech = backtest.per_ticker_signals(pdf, horizons=[5, 10], include_technical=True)

    assert len(tech) <= len(core)
    if not core.empty and not tech.empty:
        # Technical signals must coincide with rows that were also core signals
        # (technical filter ANDs onto core mask).
        core_keys = set(zip(core["ticker"], core["signal_date"]))
        tech_keys = set(zip(tech["ticker"], tech["signal_date"]))
        assert tech_keys.issubset(core_keys)


def test_event_dedup_collapses_consecutive_signals_to_first():
    """Contiguous bar_index runs per ticker collapse to the first row."""
    df = pd.DataFrame({
        "ticker": ["X.BK"] * 4 + ["Y.NS"] * 3,
        "market": ["SET"] * 4 + ["NSE"] * 3,
        "signal_date": [
            pd.Timestamp("2025-01-02").date(),
            pd.Timestamp("2025-01-03").date(),
            pd.Timestamp("2025-01-06").date(),  # gap: new event
            pd.Timestamp("2025-01-07").date(),
            pd.Timestamp("2025-02-10").date(),
            pd.Timestamp("2025-02-11").date(),
            pd.Timestamp("2025-02-12").date(),
        ],
        "bar_index": [10, 11, 14, 15, 22, 23, 24],
        "entry_price": [50.0, 50.5, 51.0, 51.5, 200.0, 201.0, 202.0],
        "volume": [1_000_000] * 7,
        "avg_volume_20d": [950_000] * 7,
        "fwd_return_5d": [0.01, 0.02, 0.03, 0.04, -0.01, -0.02, -0.03],
    })
    out = backtest.dedupe_events(df)
    # X.BK: bar_indices 10 and 14 are the first row of each contiguous run.
    # Y.NS: only the bar_index 22 row survives.
    assert sorted(out[["ticker", "bar_index"]].itertuples(index=False, name=None)) == [
        ("X.BK", 10),
        ("X.BK", 14),
        ("Y.NS", 22),
    ]


def test_nvdr_dedup_keeps_higher_avg_volume_and_ties_to_ordinary():
    df = pd.DataFrame({
        "ticker": ["AOT.BK", "AOT-R.BK", "BBL-R.BK", "BBL.BK",
                   "CPN-R.BK",  # unique NVDR
                   "RELIANCE.NS"],
        "market": ["SET", "SET", "SET", "SET", "SET", "NSE"],
        "signal_date": [pd.Timestamp("2025-07-02").date()] * 6,
        "bar_index": [100, 101, 102, 103, 104, 200],
        "entry_price": [60.0, 60.1, 150.0, 150.5, 35.0, 2400.0],
        "avg_volume_20d": [1_000_000, 2_500_000, 100_000, 900_000, 250_000, 5_000_000],
        "volume": [800_000, 2_000_000, 50_000, 700_000, 200_000, 5_500_000],
        "fwd_return_5d": [0.01, 0.02, -0.01, -0.005, 0.03, 0.0],
    })
    out = backtest.dedupe_nvdr(df)
    tickers = sorted(out["ticker"].tolist())
    assert tickers == sorted(["AOT-R.BK", "BBL.BK", "CPN-R.BK", "RELIANCE.NS"])


def test_nvdr_dedup_tie_breaks_to_ordinary():
    df = pd.DataFrame({
        "ticker": ["AOT-R.BK", "AOT.BK"],
        "market": ["SET", "SET"],
        "signal_date": [pd.Timestamp("2025-07-02").date()] * 2,
        "bar_index": [101, 100],
        "avg_volume_20d": [1_000_000, 1_000_000],
        "volume": [500_000, 500_000],
        "fwd_return_5d": [0.02, 0.01],
    })
    out = backtest.dedupe_nvdr(df)
    assert out["ticker"].tolist() == ["AOT.BK"]


def test_transaction_bps_subtracts_exact_amount():
    df = pd.DataFrame({
        "ticker": ["A", "B", "C"],
        "fwd_return_5d": [0.10, -0.05, np.nan],
        "fwd_return_10d": [0.20, 0.0, 0.03],
    })
    out = backtest.apply_transaction_costs(df, horizons=[5, 10], bps=25)
    cost = 25 / 10_000.0  # 0.0025

    assert out.loc[0, "fwd_return_5d"] == pytest.approx(0.10 - cost)
    assert out.loc[1, "fwd_return_5d"] == pytest.approx(-0.05 - cost)
    assert pd.isna(out.loc[2, "fwd_return_5d"])
    assert out.loc[0, "fwd_return_10d"] == pytest.approx(0.20 - cost)
    assert out.loc[2, "fwd_return_10d"] == pytest.approx(0.03 - cost)


def test_transaction_bps_zero_is_noop():
    df = pd.DataFrame({"ticker": ["A"], "fwd_return_5d": [0.10]})
    out = backtest.apply_transaction_costs(df, horizons=[5], bps=0)
    # The path returns the original frame unchanged.
    assert out.loc[0, "fwd_return_5d"] == 0.10


def test_no_duplicate_ticker_signal_date_after_dedup_chain():
    """Combined event + NVDR dedup must not leave duplicate (ticker, signal_date)
    pairs in the output."""
    dates = pd.date_range("2025-01-02", periods=5, freq="B").date
    df = pd.DataFrame({
        "ticker": ["X.BK"] * 5 + ["X-R.BK"] * 5 + ["Y.NS"] * 5,
        "market": ["SET"] * 10 + ["NSE"] * 5,
        "signal_date": list(dates) * 3,
        "bar_index": [100, 101, 102, 103, 104,
                       200, 201, 202, 203, 204,
                       300, 301, 302, 303, 304],
        "entry_price": [50.0] * 15,
        "avg_volume_20d": [1_000_000] * 5 + [2_000_000] * 5 + [3_000_000] * 5,
        "volume": [500_000] * 15,
        "fwd_return_5d": [0.01] * 15,
    })
    after_events = backtest.dedupe_events(df)
    after_nvdr = backtest.dedupe_nvdr(after_events)
    n_total = len(after_nvdr)
    n_distinct = after_nvdr.drop_duplicates(subset=["ticker", "signal_date"]).shape[0]
    assert n_total == n_distinct
    # Event dedup keeps only the bar_index 100/200/300 rows; NVDR dedup
    # then collapses the X.BK / X-R.BK pair on that date to the higher
    # avg_volume_20d row (X-R.BK).
    assert set(after_nvdr["ticker"].tolist()) == {"X-R.BK", "Y.NS"}


def test_set_group_key_matches_screener_helper():
    """The backtest's _set_group_key must agree with screener.core's
    helper so dedup behaviour stays in lockstep."""
    from screener import core as screener_core
    for sym in ["AOT.BK", "AOT-R.BK", "RELIANCE.NS", "AALI.JK", "5.HK"]:
        assert backtest._set_group_key(sym) == screener_core._set_group_key(sym)
