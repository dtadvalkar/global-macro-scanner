"""Focused unit tests for screening/screening_utils.py technical helpers.

These tests never call live providers or the DB. They cover the three
rolling-feature helpers (calculate_rsi, calculate_sma, calculate_atr) and
the atr_enabled branch in should_pass_screening that consumes them.

The calculate_atr test was specifically added to catch the missing
`import pandas as pd` in screening_utils -- the helper uses pd.concat
internally and py_compile cannot detect that.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from screening import screening_utils  # noqa: E402


def _linear_prices(n, start=100.0, step=1.0):
    return pd.Series([start + step * i for i in range(n)])


def test_calculate_rsi_strong_uptrend_is_high():
    prices = _linear_prices(30, start=100.0, step=1.0)
    rsi = screening_utils.calculate_rsi(prices, period=14)
    assert rsi == pytest.approx(100.0)


def test_calculate_rsi_strong_downtrend_is_low():
    prices = _linear_prices(30, start=200.0, step=-1.0)
    rsi = screening_utils.calculate_rsi(prices, period=14)
    assert rsi == pytest.approx(0.0)


def test_calculate_rsi_insufficient_data_returns_neutral():
    rsi = screening_utils.calculate_rsi(pd.Series([100.0, 101.0]), period=14)
    assert rsi == 50.0


def test_calculate_sma_matches_tail_mean():
    prices = _linear_prices(50, start=1.0, step=1.0)
    sma10 = screening_utils.calculate_sma(prices, period=10)
    # tail(10) is 41..50 inclusive, mean = 45.5
    assert sma10 == pytest.approx(45.5)


def test_calculate_sma_insufficient_data_returns_last_price():
    prices = pd.Series([10.0, 11.0, 12.0])
    sma10 = screening_utils.calculate_sma(prices, period=10)
    assert sma10 == 12.0


def test_calculate_atr_runs_without_pandas_import_error():
    """Regression test: calculate_atr uses pd.concat but the module never
    imported pandas. Before the fix this raised NameError: pd is not
    defined and the helper returned its default 0.05 via the except block.
    """
    rng = np.random.default_rng(seed=42)
    n = 60
    closes = pd.Series(100.0 + np.cumsum(rng.normal(0, 1.0, n)))
    highs = closes + np.abs(rng.normal(0, 0.5, n))
    lows = closes - np.abs(rng.normal(0, 0.5, n))

    atr_pct = screening_utils.calculate_atr(highs, lows, closes, period=14)

    # Non-default, non-zero, finite, and within a plausible range for synthetic
    # near-1-unit moves on a ~100 price: roughly 0.1%..10%.
    assert atr_pct != 0.05, "ATR returned default sentinel -- helper likely fell through to except"
    assert np.isfinite(atr_pct)
    assert 0.0 < atr_pct < 0.1


def test_calculate_atr_insufficient_data_returns_default():
    short = pd.Series([100.0, 101.0])
    atr_pct = screening_utils.calculate_atr(short, short, short, period=14)
    assert atr_pct == 0.05


def _base_passing_input():
    """Return a symbol_data dict that passes should_pass_screening with
    atr_enabled defaults. Individual tests mutate one field at a time."""
    return {
        'symbol': 'TEST.NS',  # NSE -> 150M floor
        'price': 100.0,
        'low_52w': 98.0,
        'usd_mcap': 1.0,  # 1B, well above NSE 150M floor
        'rvol': 3.0,
        'volume': 200_000,
        'high_52w': 250.0,
        'avg_volume_20d': 200_000,
        'days_since_low': 5,
        'rsi': 30,
        'price_vs_sma50_pct': 0.97,
        'sma50_vs_sma200_pct': 0.95,
        'atr_pct': 0.04,  # 4%, within default 1.5%..8%
    }


def test_should_pass_screening_atr_enabled_within_band():
    data = _base_passing_input()
    criteria = {'atr_enabled': True, 'atr_min_pct': 0.02, 'atr_max_pct': 0.08, 'min_history_days': 0}
    result = screening_utils.should_pass_screening(data, criteria)
    assert result is not None
    assert result['symbol'] == 'TEST.NS'


def test_should_pass_screening_atr_below_min_rejects():
    data = _base_passing_input()
    data['atr_pct'] = 0.005  # below 2% floor
    criteria = {'atr_enabled': True, 'atr_min_pct': 0.02, 'atr_max_pct': 0.08, 'min_history_days': 0}
    assert screening_utils.should_pass_screening(data, criteria) is None


def test_should_pass_screening_atr_above_max_rejects():
    data = _base_passing_input()
    data['atr_pct'] = 0.20  # above 8% ceiling
    criteria = {'atr_enabled': True, 'atr_min_pct': 0.02, 'atr_max_pct': 0.08, 'min_history_days': 0}
    assert screening_utils.should_pass_screening(data, criteria) is None
