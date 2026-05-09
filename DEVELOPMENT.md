# Development Guide

This document describes how to work in this codebase. The core principle: keep data logic in SQL/PostgreSQL and use Python as a thin orchestration layer.

## Tech stack

- **Language**: Python 3.12+
- **Database**: PostgreSQL
- **DB access**: `db.py` — single centralized module (pool, `query`/`execute`/`health_check` helpers)
- **Data providers**: Yahoo Finance (bulk OHLCV), Interactive Brokers (fundamentals + live market snapshots)
- **Screening**: `screener/` (universe + core logic, reads from `stock_fundamentals` + `prices_daily`)

## Repository layout

| Path | Role |
|------|------|
| `main.py` | Daily pipeline entrypoint; orchestrates collection → flatten → screen → alert |
| `config/settings.py` | DB config (env-backed), application settings |
| `config/criteria.py` | Screening thresholds |
| `config/markets.py` | Market definitions |
| `db.py` | **Sole** Python DB interface — add named methods here, not in ad-hoc scripts |
| `screener/` | Universe management (`universe.py`) and screening engine (`core.py`) |
| `data/` | Provider abstractions (`providers.py`), fundamentals cache (`cache_manager.py`) |
| `storage/` | DB helpers (`database.py`), CSV logging (`csvlogging.py`) |
| `alerts/` | Telegram integration |
| `scripts/etl/yfinance/` | YFinance OHLCV collection (`collect_daily_yfinance.py`, `collect_historical_yfinance.py`) |
| `scripts/etl/ibkr/` | IBKR fundamentals flattening and market data scripts |
| `scripts/testing/` | Smoke tests and audit scripts (offline, no external calls) |
| `scripts/utils/` | One-off utility scripts |
| `docs/` | Architecture, schema, and user documentation |

## Environment setup

```bash
# From repo root — activate the project venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy and fill in secrets
cp .env.example .env            # edit DB_NAME, DB_USER, DB_PASSWORD, IBKR_*, TELEGRAM_*
```

> **Never** install into a system environment. `.venv` at repo root is authoritative.

For shared multi-agent workflow and handoff rules, read `AGENTS.md`.

## Running the pipeline

```bash
# From repo root with venv activated:
PYTHONPATH='.' python main.py --exchanges NSE --mode test   # quick test (top 200 tickers)
PYTHONPATH='.' python main.py --exchanges NSE --mode live   # full scan

# DB health and diagnostics
python db.py health
python db.py validate
python db.py info --table stock_fundamentals
```

## ETL scripts (run order for a fresh setup)

```bash
# 1. Populate fundamentals (requires IBKR TWS running)
PYTHONPATH='.' python scripts/etl/ibkr/flatten_ibkr_final.py

# 2. Populate historical OHLCV (one-time; ~60s for 398 tickers × 10y)
PYTHONPATH='.' python scripts/etl/yfinance/collect_historical_yfinance.py

# 3. Flatten IBKR market snapshots into current_market_data (after market hours)
PYTHONPATH='.' python scripts/etl/ibkr/flatten_ibkr_market_data.py

# 4. Run offline screener smoke test
PYTHONPATH='.' python scripts/testing/test_offline_screener.py
```

## Database access guidelines

### Rule: one place for DB access

All Python-side DB interactions go through `db.py`. Do not create new standalone scripts that open their own `psycopg2.connect()` calls for simple queries.

```python
from db import get_db

db = get_db()
results = db.query("SELECT ticker, close FROM prices_daily WHERE price_date = %s", (today,))
```

### Adding new DB behavior

1. Add a named method to the `Database` class in `db.py` (or reuse `query`/`execute` inline for one-off ETL).
2. For multi-step data transformations or aggregations, prefer a SQL view or function over Python loops.
3. Never duplicate an existing query — check `db.py` first.
4. Tiny one-table helper queries stay inline. Multi-table joins, CTEs, window functions, ETL transformations, analytical queries, and schema DDL live under `sql/` (`sql/etl/`, `sql/schema/`, `sql/analytics/`, `sql/admin/`) and load via `db.query_file` / `db.execute_file` / `db.execute_values_file`.

### SQL externalization (mandatory for destructive verbs)

Destructive SQL — `TRUNCATE TABLE`, `DROP TABLE`, `DELETE FROM`, `ALTER TABLE`, `CREATE TABLE`, `CREATE INDEX`, `DROP INDEX` — must live in `sql/`, never embedded in `.py`. The only exception is `db.py`, the canonical DB interface. The pre-commit guard at `scripts/hooks/sql_guard.py` enforces this; install the hook with `pip install pre-commit && pre-commit install`.

Why: a TRUNCATE embedded at module level wiped two production tables on a routine `import` last cycle (`scripts/utils/reset_db_schema.py`, since hardened). Externalizing destructive verbs out of importable Python eliminates that class of footgun.

`sql/` subdirectory roles:

| Path | Use |
|---|---|
| `sql/schema/` | DDL (`CREATE TABLE IF NOT EXISTS`) — idempotent, the source of truth for structure |
| `sql/etl/` | DML for active ETL writers — INSERTs, UPDATEs, DELETEs, UPSERTs |
| `sql/analytics/` | Read-only screening / export / window-function SELECTs |
| `sql/admin/` | Destructive recovery operations (TRUNCATE, manual DROPs); always gated by typed-confirmation in the caller |

Caveat: psycopg2 treats unmatched `%` in SQL as format tokens when parameters are passed. Strip `%` from comments (use prose like "ending in .NS") or escape as `%%`.

### Conventions for new long-lived scripts

- **No raw `psycopg2.connect()`** outside `db.py`. Always `from db import get_db`.
- **No embedded destructive SQL** (see above). Read-only SELECTs that are short and inline are tolerated; multi-line or complex SELECTs go to `sql/analytics/`.
- **No side effects on import.** All execution must be guarded by `if __name__ == "__main__":`. Importing a script must never touch the database.
- **Destructive operations** must require typed confirmation (see `scripts/utils/reset_db_schema.py` for the pattern: a `CONFIRMATION_PHRASE` constant, an `input()` check, and ASCII-only output to avoid Windows codepage failures masking errors).
- **Single-responsibility functions** for new long-lived ETL/analytics scripts: split DB-touching, transform, and I/O into separate functions so each can be unit-tested with a mock `db`. (Short-lived pilots and one-off scripts may stay flat.)

### Retired or vestigial scripts

Some scripts predate the SQL-externalization discipline and remain in the tree as historical artifacts. They will trip the pre-commit guard if anyone edits them — the right response is to either externalize the SQL (and migrate to `db.py`) or delete the script. Do not bypass the guard. Currently in this state:

- `scripts/utils/create_market_data_table.py` — one-shot migration, already executed.
- `scripts/etl/ibkr/test_raw_ingestion.py` — experimental; schemas drift from production.

### Preferred pattern for new data operations

```python
# In db.py — add a named method
def get_recent_prices(self, ticker: str, days: int = 30):
    return self.query(
        """
        SELECT price_date, close, volume
        FROM prices_daily
        WHERE ticker = %s AND price_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY price_date
        """,
        (ticker, days),
    )
```

## Coding conventions

- Match the style of neighboring code (imports, logging, error handling).
- **Minimal diffs**: only touch what the task requires.
- **No new ad-hoc scripts** for one-off DB checks — use `db.py health/validate` or extend an existing script under `scripts/testing/`.
- **YFinance**: use the bulk `yf.download(tickers=space_joined_string, ...)` pattern — never per-ticker loops.
- **IBKR**: NSE-only scope; do not reintroduce fundamentals calls into market-data-only paths.
- Scripts that must be run standalone should set `PYTHONPATH='.'` as documented above.

## Testing

| Scenario | Location | How to run |
|----------|----------|-----------|
| Offline screener (no external calls) | `scripts/testing/test_offline_screener.py` | `PYTHONPATH='.' python scripts/testing/test_offline_screener.py` |
| DB health | `db.py` | `python db.py health` |
| Data integrity | `db.py` | `python db.py validate` |
| IBKR connectivity (requires TWS) | `tests/` | `PYTHONPATH='.' pytest tests/` |

## Data model quick reference

| Table | Source | Key columns | Update cadence |
|-------|--------|-------------|----------------|
| `tickers` | Manual / FinanceDatabase | `ticker`, `status` | As needed |
| `stock_fundamentals` | IBKR XML | 81+ financial metrics | Quarterly |
| `raw_ibkr_nse` | IBKR | `xml_snapshot`, `mkt_data` (JSONB) | Daily |
| `current_market_data` | IBKR (flattened) | `last_price`, `volume` | Daily |
| `prices_daily` | YFinance | `ticker`, `price_date`, OHLCV | Daily (incremental) / one-time bulk |

See `docs/developer_guide/database_schema.md` for full column definitions.
