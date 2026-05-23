from data.providers import OptimizedYFinanceProvider, IBKRProvider, IBKRScannerProvider
from config import DATA_SOURCE, IBKR_CONFIG
from config.markets import MARKET_REGISTRY, exchange_from_yf_ticker
import time


# Scanner expansion hub: server-side IBKR scans.
# Format: (Instrument, LocationCode, ScanCode, MarketKey, IBKRExchange)
# IBKRExchange must match a MARKET_REGISTRY key in config/markets.py so that
# ibkr_to_yfinance() applies the correct per-exchange symbol transformation.
# Only IBKR-compatible markets belong here. YFINANCE-only markets (IDX, SET,
# BOVESPA, KSE, TWSE, BURSA) must not appear -- their universe is screened via
# OptimizedYFinanceProvider in the YFinance branch below.
ALL_SCANS = [
    ('STK',      'STK.HK.SEHK',    'MOST_ACTIVE', 'sehk',    'SEHK'),     # Hong Kong [IBKR free]
    ('STK',      'STK.EU.LSE',     'MOST_ACTIVE', 'lse',     'LSE'),      # UK LSE    [IBKR restricted]
    ('STK',      'STK.ME.TADAWUL', 'MOST_ACTIVE', 'tadawul', 'TADAWUL'),  # Saudi     [IBKR restricted]
    ('STOCK.NA', 'STK.NA',         'MOST_ACTIVE', 'tsx',     'TSE'),      # Canada    [IBKR paid]
]


def get_provider_for_ticker(ticker):
    """Return 'YFINANCE' or 'IBKR' for a yfinance-format ticker.

    IBKR_PAID is treated as IBKR-compatible for routing -- the routing tier
    cares about which API to call, not subscription state. Unknown suffixes
    and bare US-style tickers default to IBKR.
    """
    exchange = exchange_from_yf_ticker(ticker)
    if not exchange:
        return 'IBKR'
    provider = MARKET_REGISTRY.get(exchange, {}).get('provider', 'IBKR')
    if provider == 'YFINANCE':
        return 'YFINANCE'
    return 'IBKR'


def split_universe_by_provider(universe):
    """Return (ibkr_tickers, yfinance_tickers) preserving input order."""
    ibkr_tickers = []
    yfinance_tickers = []
    for ticker in universe:
        if get_provider_for_ticker(ticker) == 'YFINANCE':
            yfinance_tickers.append(ticker)
        else:
            ibkr_tickers.append(ticker)
    return ibkr_tickers, yfinance_tickers


def dedupe_results(results):
    """De-dupe screener results by symbol/ticker, preserving insertion order."""
    seen = set()
    deduped = []
    for row in results:
        if not isinstance(row, dict):
            deduped.append(row)
            continue
        key = row.get('symbol') or row.get('ticker')
        if key is None:
            deduped.append(row)
            continue
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _row_symbol(row):
    """Return the symbol/ticker for a result row, or None."""
    if not isinstance(row, dict):
        return None
    return row.get('symbol') or row.get('ticker')


def _set_group_key(symbol):
    """SET ordinary/NVDR grouping key.

    Returns the ordinary `.BK` form for any SET ordinary share or NVDR
    variant (`-R.BK`), and None for symbols that should not be grouped.
    Non-SET symbols (e.g. NSE, IDX) return None so they pass through
    untouched.
    """
    if not isinstance(symbol, str):
        return None
    if symbol.endswith('-R.BK'):
        return symbol[: -len('-R.BK')] + '.BK'
    if symbol.endswith('.BK'):
        return symbol
    return None


def _liquidity_sort_key(row):
    """Return a sort key (avg_volume_20d, volume) for liquidity comparison.

    Missing or non-numeric fields fall through to -1 so they always lose
    to a row with usable liquidity data. Returned as a tuple so the
    standard max(... key=...) ranking applies avg_volume_20d first.
    """
    def _num(v):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return -1.0
        if f != f:  # NaN
            return -1.0
        return f
    return (_num(row.get('avg_volume_20d')), _num(row.get('volume')))


def dedupe_set_nvdr_results(results):
    """Collapse SET ordinary/NVDR collisions at signal time.

    For every group keyed by `_set_group_key`, keep the row with the
    higher avg_volume_20d (fallback: higher volume; final tie-break:
    ordinary `.BK` over NVDR `-R.BK`). Rows whose symbol returns a None
    group key (non-SET symbols) pass through untouched.

    Stable order: the kept row is emitted in the position of the first
    occurrence within its group. Non-grouped rows keep their position.
    """
    # Bucket rows by group key, tracking each row's original index for
    # stable emission order.
    groups = {}            # group_key -> list[(idx, row)]
    ordering = []          # list[(idx, group_key | None, row)]
    for idx, row in enumerate(results):
        symbol = _row_symbol(row)
        gk = _set_group_key(symbol) if symbol is not None else None
        ordering.append((idx, gk, row))
        if gk is not None:
            groups.setdefault(gk, []).append((idx, row))

    # Decide the winner for every group that has at least one ordinary +
    # NVDR collision. Groups with only one variant present pass through
    # unchanged.
    winners = {}  # group_key -> set of indices kept
    for gk, rows in groups.items():
        symbols = {_row_symbol(r) for _, r in rows}
        has_ordinary = gk in symbols
        has_nvdr = any(s and s.endswith('-R.BK') for s in symbols)
        if not (has_ordinary and has_nvdr):
            winners[gk] = {idx for idx, _ in rows}
            continue

        def _rank(item):
            idx, row = item
            sym = _row_symbol(row) or ''
            # Higher liquidity wins; final tie-break: ordinary .BK (False
            # < True; we want ordinary to win on equality, so invert).
            is_nvdr = sym.endswith('-R.BK')
            return _liquidity_sort_key(row) + (0 if not is_nvdr else -1,)

        best_idx, _best_row = max(rows, key=_rank)
        winners[gk] = {best_idx}

    out = []
    for idx, gk, row in ordering:
        if gk is None:
            out.append(row)
            continue
        if idx in winners.get(gk, set()):
            out.append(row)
    return out


def _run_scanner_then_deep_scan(ibkr_universe, markets, criteria):
    """Run IBKR scanner (Option B) for enabled IBKR-compatible markets, then deep-scan hits.

    Returns the list of confirmed scanner deep-scan results, possibly empty.
    Errors are swallowed and logged so the caller can continue with the bulk
    IBKR path / yfinance path.
    """
    scanner = IBKRScannerProvider(IBKR_CONFIG['host'], IBKR_CONFIG['port'], IBKR_CONFIG['client_id'])

    option_b_scans = [
        (inst, loc, scan, ibkr_exchange)
        for inst, loc, scan, m_key, ibkr_exchange in ALL_SCANS
        if markets.get(m_key, False)
    ]

    if not option_b_scans:
        print("Option B skipped: No enabled markets have server-side scanning configured.")
        return []

    print(f"Option B: Connecting to IBKR on {IBKR_CONFIG['host']}:{IBKR_CONFIG['port']}...")
    hot_tickers = []
    for inst, loc, scan, ibkr_exchange in option_b_scans:
        try:
            print(f"Requesting scan: {loc} | {scan}...")
            found = scanner.get_scanner_results(inst, loc, scan, ibkr_exchange)
            if found:
                print(f"  Found {len(found)} candidates from {loc} Scanner.")
                hot_tickers.extend(found)
            else:
                print(f"  No results from {loc} Scanner.")
            time.sleep(1)
        except Exception as e:
            print(f"  Warning: Scanner Option B failed for {loc}: {e}")
            time.sleep(2)

    if not hot_tickers:
        print("Option B (Scanner) found no tickers.")
        return []

    print(f"Running deep analysis on {len(hot_tickers)} server-side candidates...")
    ib_bulk = IBKRProvider(IBKR_CONFIG['host'], IBKR_CONFIG['port'], IBKR_CONFIG['client_id'])
    unique_hot = list(dict.fromkeys(hot_tickers))  # de-dupe, preserve order
    try:
        results = ib_bulk.get_market_data(unique_hot, criteria) or []
    except Exception as e:
        print(f"  Warning: Scanner deep-scan failed: {e}")
        results = []
    if results:
        print(f"Option B successful: {len(results)} confirmed catches.")
    return results


def _run_ibkr_bulk(ibkr_universe, criteria):
    """Run the IBKR stored/bulk path on the IBKR-compatible slice of the universe."""
    if not ibkr_universe:
        return []
    print(f"Option A: IBKR bulk/stored-data scan on {len(ibkr_universe)} IBKR-compatible tickers...")
    ib_bulk = IBKRProvider(IBKR_CONFIG['host'], IBKR_CONFIG['port'], IBKR_CONFIG['client_id'])
    try:
        results = ib_bulk.get_market_data(ibkr_universe, criteria)
    except Exception as e:
        print(f"  Warning: IBKR bulk scan failed: {e}")
        return []
    return results or []


def _run_yfinance(yfinance_universe, criteria):
    """Run OptimizedYFinanceProvider on the YFINANCE-only slice of the universe."""
    if not yfinance_universe:
        return []
    print(f"YFinance path: bulk scan on {len(yfinance_universe)} YFINANCE-only tickers...")
    provider = OptimizedYFinanceProvider()
    try:
        results = provider.get_market_data(yfinance_universe, criteria)
    except Exception as e:
        print(f"  Warning: YFinance bulk scan failed: {e}")
        return []
    return results or []


def screen_universe(universe, criteria, markets=None):
    """Route the universe to IBKR / YFinance providers per DATA_SOURCE.

    DATA_SOURCE values:
      'yfinance' -> all tickers via OptimizedYFinanceProvider; IBKR untouched.
      'ibkr'     -> IBKR scanner+bulk only; YFINANCE-only tickers are skipped
                    with a warning (DATA_SOURCE=ibkr disables the yfinance path).
      'auto'     -> universe is split: IBKR scanner+bulk for IBKR-compatible
                    tickers, OptimizedYFinanceProvider for YFINANCE-only tickers.
                    Results are combined and de-duped. A zero-result or error
                    from one branch does not block the other.
    """
    if markets is None:
        from config import MARKETS
        markets = MARKETS

    ibkr_tickers, yfinance_tickers = split_universe_by_provider(universe)
    print(f"Provider split: IBKR={len(ibkr_tickers)}, YFINANCE={len(yfinance_tickers)} "
          f"(DATA_SOURCE={DATA_SOURCE})")

    if DATA_SOURCE == 'yfinance':
        return dedupe_set_nvdr_results(dedupe_results(_run_yfinance(universe, criteria)))

    if DATA_SOURCE == 'ibkr':
        if yfinance_tickers:
            print(f"  Warning: skipping {len(yfinance_tickers)} YFINANCE-only tickers "
                  f"because DATA_SOURCE=ibkr (sample: {yfinance_tickers[:5]}).")
        scanner_results = _run_scanner_then_deep_scan(ibkr_tickers, markets, criteria)
        bulk_results = _run_ibkr_bulk(ibkr_tickers, criteria)
        return dedupe_set_nvdr_results(dedupe_results(scanner_results + bulk_results))

    # DATA_SOURCE == 'auto' (default): run both branches, combine, dedupe.
    scanner_results = _run_scanner_then_deep_scan(ibkr_tickers, markets, criteria)
    bulk_results = _run_ibkr_bulk(ibkr_tickers, criteria)
    yf_results = _run_yfinance(yfinance_tickers, criteria)

    deduped = dedupe_results(scanner_results + bulk_results + yf_results)
    combined = dedupe_set_nvdr_results(deduped)
    nvdr_dropped = len(deduped) - len(combined)
    print(f"Combined results: scanner={len(scanner_results)}, ibkr_bulk={len(bulk_results)}, "
          f"yfinance={len(yf_results)}, total_after_dedupe={len(deduped)}"
          + (f", set_nvdr_dropped={nvdr_dropped}" if nvdr_dropped else "")
          + f", total_after_nvdr_dedupe={len(combined)}")
    return combined
