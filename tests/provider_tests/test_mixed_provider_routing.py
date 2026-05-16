"""Tests for screener.core mixed-provider routing.

These tests verify that DATA_SOURCE=auto correctly splits the universe
between IBKR-compatible and YFINANCE-only tickers, and that the two
non-auto modes route as expected. All external dependencies (IBKR,
yfinance, DB) are monkeypatched -- the tests never touch real services.
"""

import os
import sys

import pytest

# Make project root importable when pytest is invoked from anywhere.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from screener import core as screener_core  # noqa: E402


CRITERIA = {'min_history_days': 0}


class _FakeIBKRScannerProvider:
    """Stand-in for IBKRScannerProvider.

    Yields a configurable list of hot tickers regardless of location/exchange.
    Records every call for assertion.
    """

    instances = []

    def __init__(self, *_args, **_kwargs):
        self.calls = []
        _FakeIBKRScannerProvider.instances.append(self)

    # Class-level toggle the tests set before invoking screen_universe.
    hot_tickers = []

    def get_scanner_results(self, instrument, location, scan_code, exchange=''):
        self.calls.append((instrument, location, scan_code, exchange))
        return list(_FakeIBKRScannerProvider.hot_tickers)


class _FakeIBKRProvider:
    """Stand-in for IBKRProvider that records every batch of tickers it sees."""

    instances = []
    deep_scan_results = []  # returned for the deep-scan invocation (first hot ticker batch)
    bulk_results = []       # returned for subsequent bulk invocations

    def __init__(self, *_args, **_kwargs):
        self.batches = []
        _FakeIBKRProvider.instances.append(self)

    def get_market_data(self, tickers, criteria):
        batch = list(tickers)
        self.batches.append(batch)
        # First instance invoked = deep-scan if scanner had hits; otherwise bulk.
        # Use class-level results lists so tests can pre-stage what each path returns.
        if _FakeIBKRProvider.deep_scan_results and len(_FakeIBKRProvider.instances) == 1 and \
                set(batch).issubset(set(_FakeIBKRScannerProvider.hot_tickers)):
            return list(_FakeIBKRProvider.deep_scan_results)
        return list(_FakeIBKRProvider.bulk_results)


class _FakeYFinanceProvider:
    """Stand-in for OptimizedYFinanceProvider."""

    instances = []
    results = []

    def __init__(self, *_args, **_kwargs):
        self.batches = []
        _FakeYFinanceProvider.instances.append(self)

    def get_market_data(self, tickers, criteria):
        batch = list(tickers)
        self.batches.append(batch)
        return list(_FakeYFinanceProvider.results)


@pytest.fixture(autouse=True)
def _reset_fakes(monkeypatch):
    """Clear fake class state and wire fakes into screener.core for every test."""
    _FakeIBKRScannerProvider.instances = []
    _FakeIBKRScannerProvider.hot_tickers = []
    _FakeIBKRProvider.instances = []
    _FakeIBKRProvider.deep_scan_results = []
    _FakeIBKRProvider.bulk_results = []
    _FakeYFinanceProvider.instances = []
    _FakeYFinanceProvider.results = []

    monkeypatch.setattr(screener_core, 'IBKRScannerProvider', _FakeIBKRScannerProvider)
    monkeypatch.setattr(screener_core, 'IBKRProvider', _FakeIBKRProvider)
    monkeypatch.setattr(screener_core, 'OptimizedYFinanceProvider', _FakeYFinanceProvider)
    # Prevent the 1-2 second sleeps the scanner branch uses between scans.
    monkeypatch.setattr(screener_core.time, 'sleep', lambda *_: None)


def test_auto_mode_splits_universe_by_provider(monkeypatch):
    monkeypatch.setattr(screener_core, 'DATA_SOURCE', 'auto')
    _FakeIBKRProvider.bulk_results = [{'ticker': 'RELIANCE.NS'}]
    _FakeYFinanceProvider.results = [{'symbol': 'AALI.JK'}, {'symbol': 'AOT.BK'}]

    universe = ['RELIANCE.NS', 'AALI.JK', 'AOT.BK']
    markets = {'nse': True, 'idx': True, 'set': True}

    results = screener_core.screen_universe(universe, CRITERIA, markets)

    assert len(_FakeIBKRProvider.instances) == 1, "IBKR provider should be invoked exactly once (bulk path)"
    assert _FakeIBKRProvider.instances[0].batches == [['RELIANCE.NS']], \
        "IBKR bulk should see only the IBKR-compatible ticker."

    assert len(_FakeYFinanceProvider.instances) == 1
    assert _FakeYFinanceProvider.instances[0].batches == [['AALI.JK', 'AOT.BK']], \
        "YFinance should see only the YFINANCE-only tickers."

    assert len(results) == 3
    symbols = {row.get('symbol') or row.get('ticker') for row in results}
    assert symbols == {'RELIANCE.NS', 'AALI.JK', 'AOT.BK'}


def test_yfinance_mode_skips_ibkr(monkeypatch):
    monkeypatch.setattr(screener_core, 'DATA_SOURCE', 'yfinance')
    _FakeYFinanceProvider.results = [
        {'symbol': 'RELIANCE.NS'},
        {'symbol': 'AALI.JK'},
        {'symbol': 'AOT.BK'},
    ]

    universe = ['RELIANCE.NS', 'AALI.JK', 'AOT.BK']
    results = screener_core.screen_universe(universe, CRITERIA, {'nse': True, 'idx': True, 'set': True})

    assert _FakeIBKRProvider.instances == []
    assert _FakeIBKRScannerProvider.instances == []
    assert len(_FakeYFinanceProvider.instances) == 1
    assert _FakeYFinanceProvider.instances[0].batches == [['RELIANCE.NS', 'AALI.JK', 'AOT.BK']]
    assert len(results) == 3


def test_ibkr_mode_skips_yfinance_only_tickers(monkeypatch):
    monkeypatch.setattr(screener_core, 'DATA_SOURCE', 'ibkr')
    _FakeIBKRProvider.bulk_results = [{'ticker': 'RELIANCE.NS'}]

    universe = ['RELIANCE.NS', 'AALI.JK', 'AOT.BK']
    # No IBKR scanner market enabled here -- scanner branch should no-op.
    results = screener_core.screen_universe(universe, CRITERIA, {'nse': True, 'idx': True, 'set': True})

    assert _FakeYFinanceProvider.instances == [], \
        "DATA_SOURCE=ibkr must not invoke OptimizedYFinanceProvider."
    assert len(_FakeIBKRProvider.instances) == 1
    assert _FakeIBKRProvider.instances[0].batches == [['RELIANCE.NS']], \
        "IBKR bulk should be limited to IBKR-compatible tickers; .JK/.BK are skipped."
    assert [row.get('ticker') for row in results] == ['RELIANCE.NS']


def test_auto_mode_runs_yfinance_even_when_scanner_finds_hot_ibkr_ticker(monkeypatch):
    """Regression: the old core.py returned early after a successful scanner deep-scan,
    starving YFINANCE-only tickers. Both branches must always run in auto mode."""
    monkeypatch.setattr(screener_core, 'DATA_SOURCE', 'auto')
    _FakeIBKRScannerProvider.hot_tickers = ['5.HK']
    _FakeIBKRProvider.deep_scan_results = [{'ticker': '5.HK'}]
    _FakeYFinanceProvider.results = [{'symbol': 'AALI.JK'}]

    universe = ['AALI.JK']  # IBKR slice is empty; scanner provides its own hot ticker.
    markets = {'sehk': True, 'idx': True}

    results = screener_core.screen_universe(universe, CRITERIA, markets)

    # Scanner deep-scan path was invoked.
    assert len(_FakeIBKRProvider.instances) == 1
    assert _FakeIBKRProvider.instances[0].batches == [['5.HK']]

    # YFinance was still invoked despite the scanner producing a result.
    assert len(_FakeYFinanceProvider.instances) == 1
    assert _FakeYFinanceProvider.instances[0].batches == [['AALI.JK']]

    symbols = {row.get('symbol') or row.get('ticker') for row in results}
    assert symbols == {'5.HK', 'AALI.JK'}


def _load_main_automated(monkeypatch):
    """Load main/main_automated.py by file path.

    `main.py` at repo root shadows the `main/` directory in Python's import
    resolution, and `main/` has no `__init__.py`, so the regular `from main
    import main_automated` path does not work. Additionally, the module's
    top-level `from scheduler.market_scheduler import create_optimal_schedule`
    pulls in the optional `schedule` package which is not in requirements.txt,
    so we stub that import here.
    """
    import importlib.util
    import types

    fake_scheduler_pkg = types.ModuleType('scheduler')
    fake_market_scheduler = types.ModuleType('scheduler.market_scheduler')
    fake_market_scheduler.create_optimal_schedule = lambda _func: None
    monkeypatch.setitem(sys.modules, 'scheduler', fake_scheduler_pkg)
    monkeypatch.setitem(sys.modules, 'scheduler.market_scheduler', fake_market_scheduler)

    spec = importlib.util.spec_from_file_location(
        'main_automated_under_test',
        os.path.join(ROOT, 'main', 'main_automated.py'),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scan_markets_passes_markets_to_screen_universe(monkeypatch):
    """main.main_automated.scan_markets must propagate its markets_config down to
    screen_universe, so scheduled region scans keep their market scope through routing."""
    main_automated = _load_main_automated(monkeypatch)

    captured = {}

    def fake_get_universe(markets):
        captured['universe_markets'] = markets
        return ['AALI.JK']

    def fake_screen_universe(universe, criteria, markets=None):
        captured['markets'] = markets
        captured['universe'] = list(universe)
        return []

    monkeypatch.setattr(main_automated, 'get_universe', fake_get_universe)
    monkeypatch.setattr(main_automated, 'screen_universe', fake_screen_universe)
    monkeypatch.setattr(main_automated, 'log_catches', lambda c: None)
    monkeypatch.setattr(main_automated, 'TEST_MODE', True)

    main_automated.scan_markets({'idx': True})

    assert captured['markets'] == {'idx': True}
    assert captured['universe_markets'] == {'idx': True}
    assert captured['universe'] == ['AALI.JK']
