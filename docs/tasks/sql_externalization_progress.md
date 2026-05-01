# SQL Externalization Progress

## Task

- Short task name: SQL externalization and DB access cleanup
- Owner / agent: Claude with Codex review
- Date: 2026-04-30

## Status

- Current status: Code refactor completed and committed for review; data recovery remains pending.
- Confidence: Medium-high for code shape; end-to-end runtime verification is blocked until `tickers` and `stock_fundamentals` are restored.

## Files touched

- `db.py`
- `DEVELOPMENT.md`
- `data/cache_manager.py`
- `data/providers.py`
- `scripts/etl/ibkr/collect_daily_ibkr_market_data.py`
- `scripts/etl/ibkr/collect_ibkr_fundamentals.py`
- `scripts/etl/ibkr/flatten_ibkr_final.py`
- `scripts/etl/ibkr/flatten_ibkr_market_data.py`
- `scripts/etl/yfinance/collect_daily_yfinance.py`
- `scripts/etl/yfinance/collect_historical_yfinance.py`
- `scripts/utils/debug_mcap.py`
- `scripts/utils/inspect_db.py`
- `scripts/utils/reset_db_schema.py`
- `tests/provider_tests/test_fundamental_cache.py`
- `scripts/populate_nse_fundamentals.py` deleted
- `storage/database.py` deleted
- `sql/` added
- `docs/tasks/sql_externalization_review_brief.md` added

## Commands run

```text
git diff --check
python -m py_compile on changed Python files
python db.py health
load_sql checks for new sql/ files
execute_values_file([]) guard check
isolated imports for in-scope ETL modules
reset_db_schema.py import safety check
tests/provider_tests/test_fundamental_cache.py
```

## What changed

- Added `db.py` SQL-file helpers: `load_sql`, `query_file`, `execute_file`, and `execute_values_file`.
- Moved reusable active ETL SQL into `sql/etl/` and schema DDL into `sql/schema/`.
- Migrated the in-scope active ETL scripts away from direct `psycopg2.connect()` and toward `db.py`.
- Parameterized the live screening `IN` clause in `data/providers.py`.
- Pruned broken `data/cache_manager.py` write/cache APIs that no longer matched the curated IBKR `stock_fundamentals` schema.
- Migrated utility scripts away from the deleted `storage/database.py`.
- Rewrote `scripts/utils/reset_db_schema.py` so importing it has no database side effects and running it requires typed confirmation.

## Blockers or failures

- During earlier verification, importing the old `scripts/utils/reset_db_schema.py` truncated `tickers` and `stock_fundamentals`.
- There is no backup. Current known state after the incident: `tickers = 0`, `stock_fundamentals = 0`; source tables such as `ibkr_fundamentals`, `ibkr_market_data`, `prices_daily`, and `current_market_data` were reported intact.
- Full scanner smoke tests and row-count baselines are deferred until data is restored.
- `.claude/settings.local.json` was modified by harness state and should not be treated as project work.

## Next recommended step

- Restore `stock_fundamentals` from intact `ibkr_fundamentals` by running `PYTHONPATH='.' .venv/Scripts/python -m scripts.etl.ibkr.flatten_ibkr_final`, then verify the expected Task 11 baseline of 1,844 rows.
- Reseed `tickers` separately using the chosen canonical exchange-universe process.
- After data recovery, run `python db.py health` and `PYTHONPATH='.' python main.py --exchanges NSE --mode test`.

## Notes for the next agent

- Do not run destructive reset/truncate scripts during verification.
- Keep `.claude/settings.local.json` out of commits unless the user explicitly asks to commit harness state.
- Treat the cache-manager pruning and `storage/database.py` deletion as intentional but review-worthy structural decisions.

## Closeout update — 2026-04-30

- Status correction: the work is **staged**, not yet committed. Awaiting human review and explicit go-ahead before `git commit`.
- Late audit fixes folded into the same staged change set:
  - `data/cache_manager.py`: removed a trailing blank line at EOF (flagged by `git diff --check`).
  - `data/cache_manager.py`: added `if not self.use_database: return` / `return None` guards in `ensure_table_exists` and `get_fundamentals`. Behavior change: with `use_database=False`, both methods are now silent rather than printing an `AttributeError` to stdout per call. No code paths in the runtime use `use_database=False`, but the prior empirical noise is gone.
- Staged-commit shape (from `git diff --cached --stat`): 30 files, +578 / -1491. Both progress and review-brief notes are included.
- `.claude/settings.local.json` is **unstaged only** (` M`) and not part of the staged commit — confirmed by `git status --short`.
- `git diff --cached --check` is clean (exit 0).
- Verification still deferred until `stock_fundamentals` is restored from `ibkr_fundamentals` and `tickers` is reseeded: per-exchange counts vs. Task 11 baseline (1,844), end-to-end `main.py --exchanges NSE --mode test`, and any ETL round-trip that touches the empty tables.
