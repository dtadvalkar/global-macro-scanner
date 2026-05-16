"""Bulk-seed stock_fundamentals.mkt_cap_usd for IDX/SET via yahooquery.

Reads actionable tickers from the `tickers` table for markets IDX and SET,
fetches Yahoo `quotes` payload in chunks of <= 500 (one HTTP call per chunk
via the plural `?symbols=...` endpoint), keeps only EQUITY rows with a
positive marketCap and a currency matching the suffix (IDR for .JK,
THB for .BK), normalises marketCap to USD via `data.currency.usd_market_cap`,
and UPSERTs into the sparse `stock_fundamentals` schema. Other ~70 columns
are intentionally left NULL — `stock_fundamentals` already tolerates this
shape for exchanges without IBKR XML coverage.

Schema note: this script writes the `mkt_cap_usd` column directly.
`data/cache_manager.py:81` aliases that column to the Python key
`market_cap_usd` for downstream consumers; the underlying column name is
`mkt_cap_usd` — verify against `sql/schema/stock_fundamentals.sql`.

Phase 2 of `docs/tasks/idx_set_enablement_plan.md`. Phase 0 + Phase 1
prerequisites must already have passed:
  - yahooquery installed in .venv (not yet pinned in requirements.txt).
  - `tickers` populated for IDX and SET via screener/universe.py.
"""
from __future__ import annotations

import functools
import os
import sys
import time
from typing import Iterable, List, Sequence, Tuple

# Match the existing convention in scripts/etl/yfinance/collect_daily_yfinance.py:
# allow direct invocation (python scripts/etl/yahooquery/seed_idx_set_fundamentals.py)
# by ensuring the project root is on sys.path before importing project modules.
sys.path.append(os.getcwd())

from yahooquery import Ticker  # noqa: E402

from data import currency as currency_mod  # noqa: E402
from data.currency import usd_market_cap  # noqa: E402
from db import get_db  # noqa: E402

CHUNK_SIZE = 500

# Per-suffix exchange metadata. Currency is the *expected* Yahoo `currency`
# field for that suffix; rows whose currency does not match are dropped
# (catches cross-listings, ADRs, and Yahoo data glitches).
EXCHANGE_META = {
    '.JK': {'code': 'IDX', 'country': 'Indonesia', 'currency': 'IDR'},
    '.BK': {'code': 'SET', 'country': 'Thailand',  'currency': 'THB'},
}


def chunked(seq: Sequence[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), size):
        yield list(seq[i:i + size])


def exchange_meta_for(ticker: str):
    for suffix, meta in EXCHANGE_META.items():
        if ticker.endswith(suffix):
            return meta
    return None


def fetch_quotes(chunk: List[str]) -> dict:
    """One HTTP call per chunk via Yahoo's plural ?symbols= endpoint."""
    return Ticker(chunk, asynchronous=False).quotes


def build_row(symbol: str, payload):
    """Return a tuple matching sql/etl/stock_fundamentals_yq_upsert.sql, or None to skip."""
    if not isinstance(payload, dict):
        return None
    if payload.get('quoteType') != 'EQUITY':
        return None
    mcap = payload.get('marketCap')
    if not mcap or mcap <= 0:
        return None
    currency = payload.get('currency')
    meta = exchange_meta_for(symbol)
    if meta is None or currency != meta['currency']:
        return None
    company_name = payload.get('longName') or payload.get('shortName') or symbol
    mkt_cap_usd = usd_market_cap(symbol, mcap)
    return (
        symbol,
        company_name,
        float(mkt_cap_usd),
        currency,
        meta['code'],
        meta['country'],
    )


def seed():
    db = get_db()
    tickers = db.get_actionable_tickers('IDX') + db.get_actionable_tickers('SET')
    print(f"Loaded {len(tickers)} IDX+SET tickers from DB.")
    if not tickers:
        print("Nothing to seed.")
        return

    # data.currency.get_live_fx_rate hits a public FX API per call. With ~474
    # tickers across 2 currencies, that would be 474 redundant HTTP requests
    # and dominate runtime. Memoise per-currency at module scope so
    # usd_market_cap() (which looks up get_live_fx_rate via module globals at
    # call time) gets the cached value transparently.
    currency_mod.get_live_fx_rate = functools.lru_cache(maxsize=8)(
        currency_mod.get_live_fx_rate
    )

    rows: List[Tuple] = []
    skipped = 0
    t0 = time.time()
    for chunk_no, chunk in enumerate(chunked(tickers, CHUNK_SIZE), start=1):
        c0 = time.time()
        try:
            quotes = fetch_quotes(chunk)
        except Exception as e:
            print(f"  Chunk {chunk_no}: fetch failed: {str(e)[:120]}")
            continue
        print(f"  Chunk {chunk_no}: {len(chunk)} symbols in {time.time() - c0:.2f}s")
        for symbol in chunk:
            payload = quotes.get(symbol)
            row = build_row(symbol, payload)
            if row is None:
                skipped += 1
            else:
                rows.append(row)

    print(f"Built {len(rows)} rows ({skipped} skipped) in {time.time() - t0:.2f}s wall.")
    if not rows:
        print("Nothing to upsert.")
        return

    affected = db.execute_values_file('etl/stock_fundamentals_yq_upsert.sql', rows)
    print(f"[ok] Upserted {affected} rows into stock_fundamentals.")


if __name__ == "__main__":
    seed()
