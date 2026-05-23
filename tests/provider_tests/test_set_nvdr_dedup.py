"""Tests for screener.core.dedupe_set_nvdr_results.

Covers the SET ordinary / NVDR collision policy and verifies that the
end-to-end DATA_SOURCE=auto path still routes both branches and emits
deduped combined results. No external services touched -- all providers
are stubbed identically to test_mixed_provider_routing.py.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from screener import core as screener_core  # noqa: E402


CRITERIA = {'min_history_days': 0}


# ---------------------------------------------------------------------------
# Pure helper tests
# ---------------------------------------------------------------------------


def _row(symbol, avg=None, volume=None, **extra):
    out = {'symbol': symbol}
    if avg is not None:
        out['avg_volume_20d'] = avg
    if volume is not None:
        out['volume'] = volume
    out.update(extra)
    return out


def test_nvdr_higher_avg_volume_wins():
    results = [
        _row('AOT.BK', avg=1_000_000, volume=900_000),
        _row('AOT-R.BK', avg=2_500_000, volume=2_000_000),
    ]
    out = screener_core.dedupe_set_nvdr_results(results)
    assert [r['symbol'] for r in out] == ['AOT-R.BK']


def test_ordinary_higher_volume_wins_when_avg_missing():
    """Ordinary has no avg_volume_20d, NVDR has none either, fall back
    to raw volume -- ordinary's larger volume wins."""
    results = [
        _row('AOT.BK', volume=5_000_000),
        _row('AOT-R.BK', volume=1_000_000),
    ]
    out = screener_core.dedupe_set_nvdr_results(results)
    assert [r['symbol'] for r in out] == ['AOT.BK']


def test_tied_liquidity_prefers_ordinary():
    """When everything ties (or is absent), the ordinary .BK wins as the
    deterministic tie-break."""
    results = [
        _row('AOT-R.BK'),
        _row('AOT.BK'),
    ]
    out = screener_core.dedupe_set_nvdr_results(results)
    assert [r['symbol'] for r in out] == ['AOT.BK']


def test_tied_liquidity_with_explicit_equal_values_prefers_ordinary():
    results = [
        _row('AOT-R.BK', avg=1_000_000, volume=500_000),
        _row('AOT.BK', avg=1_000_000, volume=500_000),
    ]
    out = screener_core.dedupe_set_nvdr_results(results)
    assert [r['symbol'] for r in out] == ['AOT.BK']


def test_unique_nvdr_is_preserved():
    """No ordinary present -> the NVDR keeps its slot (it's the only candidate)."""
    results = [
        _row('CHIC-R.BK', avg=400_000),  # no underlying CHIC.BK in our results
    ]
    out = screener_core.dedupe_set_nvdr_results(results)
    assert [r['symbol'] for r in out] == ['CHIC-R.BK']


def test_non_set_symbols_pass_through_unchanged():
    """NSE / IDX / SEHK results must be untouched by NVDR dedup."""
    results = [
        _row('RELIANCE.NS', volume=1_000_000),
        _row('AALI.JK', volume=500_000),
        _row('5.HK', volume=2_000_000),
        _row('AOT.BK', volume=3_000_000),
        _row('AOT-R.BK', avg=10_000_000),
    ]
    out = screener_core.dedupe_set_nvdr_results(results)
    symbols = [r['symbol'] for r in out]
    # Non-SET rows preserved in their original positions; SET pair collapses
    # to the NVDR (higher avg_volume_20d).
    assert symbols == ['RELIANCE.NS', 'AALI.JK', '5.HK', 'AOT-R.BK']


def test_stable_order_emits_first_position_of_kept_row():
    """When the NVDR appears before the ordinary in the input list and
    the ordinary wins, the kept ordinary row keeps its later slot."""
    results = [
        _row('AOT-R.BK', volume=100),
        _row('AOT.BK', volume=10_000),
    ]
    out = screener_core.dedupe_set_nvdr_results(results)
    assert [r['symbol'] for r in out] == ['AOT.BK']


def test_multiple_pairs_resolved_independently():
    results = [
        _row('AOT.BK', avg=500_000),
        _row('AOT-R.BK', avg=2_500_000),  # NVDR wins
        _row('BBL-R.BK', avg=100_000),
        _row('BBL.BK', avg=900_000),      # ordinary wins
        _row('CPN-R.BK', avg=300_000),    # unique NVDR
    ]
    out = screener_core.dedupe_set_nvdr_results(results)
    assert [r['symbol'] for r in out] == ['AOT-R.BK', 'BBL.BK', 'CPN-R.BK']


def test_non_dict_rows_pass_through():
    """Defensive: tuple/string rows (legacy stored-data format) must not crash."""
    results = [
        ('AOT.BK', 50.0),
        _row('AOT-R.BK', avg=1_000_000),
    ]
    out = screener_core.dedupe_set_nvdr_results(results)
    # The tuple row has no symbol our helper can read, so it passes through;
    # the NVDR row is the only candidate in its group.
    assert ('AOT.BK', 50.0) in out
    assert any(isinstance(r, dict) and r.get('symbol') == 'AOT-R.BK' for r in out)


def test_set_group_key():
    """Targeted check on the key derivation: ordinary -> itself, NVDR ->
    underlying, others -> None."""
    assert screener_core._set_group_key('AOT.BK') == 'AOT.BK'
    assert screener_core._set_group_key('AOT-R.BK') == 'AOT.BK'
    assert screener_core._set_group_key('RELIANCE.NS') is None
    assert screener_core._set_group_key('AALI.JK') is None
    assert screener_core._set_group_key(None) is None


# ---------------------------------------------------------------------------
# End-to-end via screen_universe (DATA_SOURCE=auto)
# ---------------------------------------------------------------------------


class _FakeIBKRScannerProvider:
    instances = []
    hot_tickers = []

    def __init__(self, *_a, **_kw):
        self.calls = []
        _FakeIBKRScannerProvider.instances.append(self)

    def get_scanner_results(self, *_a, **_kw):
        return list(_FakeIBKRScannerProvider.hot_tickers)


class _FakeIBKRProvider:
    instances = []
    bulk_results = []

    def __init__(self, *_a, **_kw):
        self.batches = []
        _FakeIBKRProvider.instances.append(self)

    def get_market_data(self, tickers, criteria):
        self.batches.append(list(tickers))
        return list(_FakeIBKRProvider.bulk_results)


class _FakeYFinanceProvider:
    instances = []
    results = []

    def __init__(self, *_a, **_kw):
        self.batches = []
        _FakeYFinanceProvider.instances.append(self)

    def get_market_data(self, tickers, criteria):
        self.batches.append(list(tickers))
        return list(_FakeYFinanceProvider.results)


@pytest.fixture(autouse=True)
def _wire_fakes(monkeypatch):
    _FakeIBKRScannerProvider.instances = []
    _FakeIBKRScannerProvider.hot_tickers = []
    _FakeIBKRProvider.instances = []
    _FakeIBKRProvider.bulk_results = []
    _FakeYFinanceProvider.instances = []
    _FakeYFinanceProvider.results = []

    monkeypatch.setattr(screener_core, 'IBKRScannerProvider', _FakeIBKRScannerProvider)
    monkeypatch.setattr(screener_core, 'IBKRProvider', _FakeIBKRProvider)
    monkeypatch.setattr(screener_core, 'OptimizedYFinanceProvider', _FakeYFinanceProvider)
    monkeypatch.setattr(screener_core.time, 'sleep', lambda *_: None)


def test_screen_universe_auto_dedupes_set_nvdr_after_branch_combine(monkeypatch):
    """End-to-end: SET ordinary returned by one branch + NVDR by the other
    are collapsed in auto mode while non-SET tickers route + return normally."""
    monkeypatch.setattr(screener_core, 'DATA_SOURCE', 'auto')

    _FakeIBKRProvider.bulk_results = [
        {'ticker': 'RELIANCE.NS', 'volume': 1_000_000},
    ]
    _FakeYFinanceProvider.results = [
        {'symbol': 'AOT.BK', 'volume': 500_000},
        {'symbol': 'AOT-R.BK', 'avg_volume_20d': 3_000_000, 'volume': 250_000},
        {'symbol': 'CHIC-R.BK', 'avg_volume_20d': 400_000},  # unique NVDR
    ]

    universe = ['RELIANCE.NS', 'AOT.BK', 'AOT-R.BK', 'CHIC-R.BK']
    markets = {'nse': True, 'set': True}

    results = screener_core.screen_universe(universe, CRITERIA, markets)

    symbols = {(r.get('symbol') or r.get('ticker')) for r in results}
    assert symbols == {'RELIANCE.NS', 'AOT-R.BK', 'CHIC-R.BK'}, (
        "expected RELIANCE.NS (untouched), AOT-R.BK (won liquidity), "
        f"CHIC-R.BK (unique NVDR); got {symbols}"
    )
