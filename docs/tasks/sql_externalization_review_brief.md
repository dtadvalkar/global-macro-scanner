# SQL Externalization / DB Boundary Review Brief

## Context

We are considering a scoped Plan 3 cleanup for Global Market Scanner: externalize meaningful ETL SQL into `.sql` files and route new/active DB access through `db.py`, while leaving tiny one-table helper queries inline.

The preference is:

- Keep simple one-line counts, simple one-table lookups, and simple one-table inserts/upserts inline when clearer.
- Externalize multi-table joins, CTEs, window functions, ETL transformations, analytical queries, schema DDL, future views/functions/procedures, and reusable SQL.
- New code should not call `psycopg2.connect()` directly outside `db.py`.
- Avoid a repo-wide cleanup. Focus only on active ETL and near-term analytics/Spark pilot work.

Plan 1 is assumed: add SQL-file conventions and DB helper support. Plan 4 is rejected as too broad. The current question is whether scoped Plan 3 is the right next move and exactly how to execute it safely.

## Current Observations To Validate

A read-only scan found:

- 110 Python files scanned.
- 47 files import `psycopg2`.
- 44 files call `psycopg2.connect()` directly.
- 51 files execute SQL through either cursors or `db.py`.
- 176 SQL execution call sites found.

But much of this is in `scripts/analysis`, `scripts/testing`, and `scripts/utils`.

Likely active ETL targets:

- `scripts/etl/yfinance/collect_daily_yfinance.py`
- `scripts/etl/yfinance/collect_historical_yfinance.py`
- `scripts/etl/finance_db/flatten_fd_nse.py`
- `scripts/etl/ibkr/collect_daily_ibkr_market_data.py`
- `scripts/etl/ibkr/collect_ibkr_fundamentals.py`
- `scripts/etl/ibkr/collect_ibkr_market_data.py`
- `scripts/etl/ibkr/flatten_ibkr_final.py`
- `scripts/etl/ibkr/flatten_ibkr_market_data.py`

Possible core drift hotspots:

- `data/cache_manager.py`
- `storage/database.py`

## Questions For Claude

1. Which of the listed ETL scripts are genuinely active and should be included in a first SQL externalization pass?

2. Which scripts are legacy, diagnostic, or research-only and should be explicitly excluded from the first pass?

3. Is `storage/database.py` still used by production/runtime paths, or has it effectively been superseded by root `db.py`?

4. Is `data/cache_manager.py` currently active in the scanner path? If yes, what behavior must be preserved before removing direct `psycopg2.connect()` calls?

5. Does `data/cache_manager.py` have a real bug around `self.db_config` not being initialized, or is there context elsewhere that makes it work?

6. Which SQL blocks in active ETL should be externalized first?
   Suggested categories:
   - schema DDL
   - `INSERT ... ON CONFLICT` upserts
   - multi-table joins
   - JSON extraction queries
   - audit/reporting queries

7. Which SQL should deliberately stay inline because moving it would add unnecessary ceremony?

8. Should `flatten_ibkr_final.py` keep its generated upsert SQL in Python because it depends on `SCHEMA_COLUMNS`, or should any part of that be moved to `.sql`?

9. What minimal helper methods should be added to `db.py` to support this cleanup?
   Possible helpers:
   - `load_sql(name_or_path)`
   - `query_file(path, params=None, fetch="all")`
   - `execute_file(path, params=None)`
   - `execute_values(sql_or_file, rows, page_size=1000)`
   - transaction/cursor context helper

10. What should the initial `sql/` directory layout be?
    Proposed:
    - `sql/analytics/`
    - `sql/etl/`
    - `sql/schema/`

11. What verification commands should be run after each phase, given this project's DB/IBKR/YFinance constraints?

12. What is the safest order of implementation to minimize behavior risk?

## Desired Output From Claude

Please answer with:

1. A short classification table:
   - file
   - active/legacy/unknown
   - direct DB usage type
   - recommended action

2. A recommended first-pass scope.

3. A step-by-step implementation plan.

4. A test/verification plan.

5. Any blockers or warnings.

Do not modify files yet. This is a planning/review pass only.
