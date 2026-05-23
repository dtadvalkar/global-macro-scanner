# IDX / SET Operations Hardening Progress

## Task

- Short task name: Operations hardening after IDX/SET enablement (B1..B5).
- Owner / agent: Claude (Opus 4.7)
- Date: 2026-05-16

## Status

- Current status: **DONE.** B1 (35 dead `.JK`/`.BK` tickers deactivated), B2 (NVDR analysis recorded with explicit "no mass-action" recommendation), B3 (monthly wrapper verified + Windows scheduler `.bat` helper added), B4 (daily yfinance collector now accepts `--exchange`/`--markets`/`--dry-run`), B5 (conservative `DATA_SOURCE=auto NSE,IDX` smoke green; DAILY PIPELINE COMPLETE).
- Confidence: High. All DB mutations behind strict rules with dry-run defaults; all DB writes verified pre + post.

## Files touched

- `scripts/maintenance/mark_inactive_idx_set_dead_tickers.py` (new) -- strict-rule deactivator; dry-run by default, `--apply` to mutate, `--force` overrides the 50-ticker safety cap.
- `sql/analytics/dead_idx_set_tickers.sql` (new) -- candidate query for B1.
- `scripts/etl/yfinance/collect_daily_yfinance.py` -- added `--exchange/--markets` and `--dry-run` (the historical collector already had `--exchange`; daily collector now matches that contract).
- `scheduler/run_idx_set_fundamentals_refresh.bat` (new) -- Windows Task Scheduler wrapper for the monthly yahooquery refresh.
- `docs/tasks/idx_set_operations_hardening_progress.md` (this file).

DB mutations:

- `tickers` table: 35 rows updated, `status` ACTIVE -> INACTIVE (3 IDX + 32 SET). All match the documented Phase 4 failed-backfill cohort from `docs/tasks/idx_set_enablement_plan.md`.

No changes to `MARKETS`, `MARKET_REGISTRY`, thresholds, screener routing, or scheduler/market_scheduler.

## B1 -- Dead IDX / SET ticker cleanup

### Strict rule

A ticker is a B1 candidate if **all** of:

- `tickers.market` IN ('IDX', 'SET')
- `tickers.ticker` LIKE '%.JK' OR LIKE '%.BK'
- `tickers.status` = 'ACTIVE' OR IS NULL
- ZERO rows in `prices_daily`
- No row in `stock_fundamentals` with `mkt_cap_usd > 0`

Encoded in `sql/analytics/dead_idx_set_tickers.sql`. Suffix patterns are bound parameters (not inlined as `'%.JK'`) so psycopg2's placeholder parser doesn't choke on literal `%` characters -- a small lesson learned during the first dry-run.

### Script behavior

- Default: **dry-run** (no DB write).
- `--apply` -- actually update.
- `--force` -- bypass the 50-candidate safety cap.
- `--cap N` -- override the safety cap.
- Per-ticker output records old status -> new status during apply.

### Results

```text
.\.venv\Scripts\python.exe scripts\maintenance\mark_inactive_idx_set_dead_tickers.py
# Candidates: 35 total (IDX 3, SET 32). [dry-run] No changes made.

.\.venv\Scripts\python.exe scripts\maintenance\mark_inactive_idx_set_dead_tickers.py --apply
# Applying status=INACTIVE to 35 tickers...
# [ok] Updated 35 rows.

.\.venv\Scripts\python.exe scripts\maintenance\mark_inactive_idx_set_dead_tickers.py
# No candidates match the strict dead-ticker rule. Nothing to do.   (idempotent)
```

DB state post-apply:

```text
[('IDX', 'ACTIVE', 146), ('IDX', 'INACTIVE', 3),
 ('SET', 'ACTIVE', 293), ('SET', 'INACTIVE', 32)]
```

Matches the published Phase 4 numbers exactly (149 IDX seeded -> 146 active; 325 SET seeded -> 293 active). The 35-name cohort is the same one reported by the Phase 4 yfinance smoke ("35 failed downloads") and the prior `current_market_data` collector logs.

The IDX/SET routing smoke (`NSE,IDX --skip-collection`) immediately reflected this: `Loaded 146 actionable IDX tickers from DB` (was 149 before). No catches, DAILY PIPELINE COMPLETE.

## B2 -- NVDR (`-R.BK`) analysis (read-only)

### Counts on active `-R.BK` (after B1 cleanup)

| Metric | Count |
|---|---:|
| `-R.BK` rows total in `tickers` | 131 |
| `-R.BK` INACTIVE (set by B1) | 13 |
| `-R.BK` ACTIVE | **118** |
| Active `-R.BK` with `prices_daily` rows | 118 (100%) |
| Active `-R.BK` with positive `mkt_cap_usd` | 118 (100%) |
| Active `-R.BK` above SET 450M threshold | 69 |
| `-R.BK` pairs where BOTH variants pass the threshold | **68** |
| Active `-R.BK` with no matching underlying `.BK` in our tickers table | 11 |
| Active `-R.BK` whose underlying `.BK` is INACTIVE | 0 |

### Examples of both-pass pairs

```text
AEONTS-R.BK ($0.70B)  /  AEONTS.BK ($0.70B)
AMATA-R.BK  ($0.75B)  /  AMATA.BK  ($0.75B)
AOT-R.BK    ($23.17B) /  AOT.BK    ($23.17B)
AYUD-R.BK   ($0.46B)  /  AYUD.BK   ($0.46B)
BAY-R.BK    ($6.47B)  /  BAY.BK    ($6.47B)
BBL-R.BK    ($9.64B)  /  BBL.BK    ($9.64B)
```

The `mkt_cap_usd` is identical between the NVDR and the underlying because yahooquery's `marketCap` is the company-level cap (one number), not a per-listing cap. This means the **per-market mcap floor cannot distinguish the two** -- both pass.

The Part A v1 backtest already observed this in the wild: AOT.BK and AOT-R.BK both generated independent signals on the same dates (e.g. 2025-07-02..2025-07-09). The NVDR returned +20-36% over the +10/+20-day horizons while the underlying returned -10 to -19% on some signal dates -- not identical price action despite identical company.

### Recommendation (not implemented)

**No mass deactivation.** The strict B1 rule does not apply to any of the 118 active `-R.BK` tickers; deactivating them en masse would violate the "do not broadly deactivate NVDRs unless the same strict dead-ticker rule from B1 applies" guardrail.

Proposed v2 follow-up (separate task): **dedupe at signal time**, not at seed time. Specifically:

1. After the screener emits results, group by `REPLACE(ticker, '-R.BK', '.BK')`.
2. Within each group of {ordinary, NVDR}, keep the variant with higher 20-day average volume on the signal date (or higher current-day volume if avg-20 is unavailable).
3. Preserve the 11 NVDRs that have no underlying in our universe (no group collisions -- nothing to dedupe).

This avoids:
- Re-seeding (which would lose the 11 unique-NVDR rows).
- Bumping the SET threshold (which would also drop legitimate non-NVDR mid-caps).
- Hard-coding a per-suffix preference (which way to prefer ordinary vs NVDR is a strategy choice, not a data-correctness one).

Open Question #1 in `docs/tasks/idx_set_enablement_plan.md` (filter-at-seed vs dedupe-at-screening) is now decidable from data; the recommendation is **dedupe-at-screening** for the reasons above.

## B3 -- Monthly fundamentals refresh operationalization

### Verification

```text
.\.venv\Scripts\python.exe -c "import scripts.etl.yahooquery.schedule_monthly_idx_set_fundamentals as s; print('import ok')"
# Output: import ok

.\.venv\Scripts\python.exe scripts\etl\yahooquery\schedule_monthly_idx_set_fundamentals.py --dry-run
# Today: 2026-05-16; Last IDX/SET update: 2026-05-16 16:16:22.630909
# Should run: False; Reason: 0 days since last IDX/SET refresh (<= 25)
# [dry-run] Would execute: ...python.exe ...seed_idx_set_fundamentals.py
```

The wrapper has no DB or subprocess side effects on import (verified again here). Dry-run path is interactive-friendly and prints the resolved command.

### New helper: `scheduler/run_idx_set_fundamentals_refresh.bat`

Activates the canonical `.venv` and invokes `schedule_monthly_idx_set_fundamentals.py` with no flags so the script's own due rule decides whether the seeder runs. Designed to be parked under Windows Task Scheduler; exit code is propagated.

### Task Scheduler manual setup (one-time)

The `.bat` is not registered automatically. Recommended setup:

1. Open **Task Scheduler** -> **Create Task...** (Actions pane).
2. **General**: name `IDX/SET monthly fundamentals refresh`; description references this doc. Check **Run whether user is logged on or not** if you want headless behavior (will prompt for credentials).
3. **Triggers**: New trigger; **Daily**, recurrence every 1 day, start at e.g. 04:30 local time. (The script's internal due rule keeps it cheap on non-due days; daily firing just ensures the 1st-of-month and the 25-day staleness windows are caught.)
4. **Actions**: New action; **Start a program**.
   - Program/script: `C:\Dev\Global Market Scanner\scheduler\run_idx_set_fundamentals_refresh.bat`
   - Start in (optional): `C:\Dev\Global Market Scanner`
5. **Conditions**: leave "Start the task only if the computer is on AC power" if the workstation usually runs on mains; otherwise uncheck so a battery-only machine still fires.
6. **Settings**: enable "If the task fails, restart every 1 hour" with up to 3 attempts.
7. Optional: redirect output to a log file by editing the `.bat` to append `>> "%REPO_ROOT%\logs\idx_set_fundamentals.log" 2>&1` on the python invocation line. The `logs/` directory already exists in the repo root.

Calendar-based vs daily-firing: a strict monthly trigger on the 1st risks missing the run if the machine is off that day. The daily trigger pattern plus the wrapper's internal due rule is more robust.

## B4 -- Daily yfinance collector exchange scoping

### Before

`scripts/etl/yfinance/collect_daily_yfinance.py` had no `--exchange` flag. The only way to run an IDX/SET-only daily refresh was to either flip the global `MARKETS` toggles (changes scope of *every* downstream) or filter the universe by hand. The historical collector (`collect_historical_yfinance.py`) already had `--exchange` -- the two collectors were out of sync.

### Change

Added to `collect_daily_yfinance.py`:

- `--exchange` / `--markets` (alias) -- comma-separated market codes (e.g. `IDX` or `IDX,SET`). When provided, `fetch_active_tickers(markets)` scopes the SQL to `WHERE market = ANY(%s)`. Behavior matches the historical collector's flag of the same name.
- `--dry-run` -- prints the resolved count and first 8 tickers, then exits 0. Safe verification without touching yfinance or `prices_daily`.

Default behavior (no flag) is unchanged: scan all active tickers across every market. No DB schema change, no breaking change to existing callers.

### Verification

```text
PYTHONUTF8=1 .\.venv\Scripts\python.exe scripts\etl\yfinance\collect_daily_yfinance.py --exchange IDX,SET --dry-run
# Found 439 active tickers (markets=['IDX', 'SET']).      <- 146 IDX + 293 SET
# [dry-run] 439 tickers to collect (period=1d): AALI.JK, AAV-R.BK, AAV.BK, ...

PYTHONUTF8=1 .\.venv\Scripts\python.exe scripts\etl\yfinance\collect_daily_yfinance.py --dry-run
# Found 5216 active tickers (all markets).                <- 5251 total - 35 B1 deactivated
# [dry-run] 5216 tickers to collect ...
```

No live yfinance collection was performed in this session; the script behavior is verified end-to-end via dry-runs (the path through `fetch_active_tickers` is the same in both modes; only the `ingest_multi_ohlcv` / `bulk_insert_prices` calls differ post-resolve).

## B5 -- Mixed-provider routing smoke

TWS port 7496 was reachable at smoke time. Per the safety guidance, ran the conservative variant (skip live collection + skip flattening) so the smoke completes in seconds and exercises the screener routing on the post-B1 ticker state:

```text
$env:DATA_SOURCE='auto'
.\.venv\Scripts\python.exe main.py --exchanges NSE,IDX --mode test --skip-collection --skip-flattening
# Loaded 1933 actionable NSE tickers from DB.
# Loaded 146 actionable IDX tickers from DB.   <- was 149 pre-B1; B1 deactivation reflected
# Provider split: IBKR=1933, YFINANCE=146 (DATA_SOURCE=auto)
# Option A: IBKR bulk/stored-data scan on 1933 IBKR-compatible tickers...
# YFinance path: bulk scan on 146 YFINANCE-only tickers...
#   Optimized YFinance: 0 catches from 146 tickers
# Combined results: scanner=0, ibkr_bulk=0, yfinance=0, total_after_dedupe=0
# DAILY PIPELINE COMPLETE
```

Both branches run. IDX count reflects the B1 cleanup. No regression in routing.

A full live-collection smoke (no `--skip-collection`) was *not* attempted -- it would take 10-20 minutes on the IBKR side, and the B1 change does not affect NSE collection at all. The prior session's commit `9579796` already exercised the routing end-to-end.

## Final verification

```text
.\.venv\Scripts\python.exe -m py_compile scripts\spark\06_backtest_52w_strategy.py `
    scripts\maintenance\mark_inactive_idx_set_dead_tickers.py `
    scripts\etl\yfinance\collect_daily_yfinance.py                # OK
.\.venv\Scripts\python.exe scripts\hooks\import_safety.py         # exit 0
.\.venv\Scripts\python.exe scripts\hooks\sql_guard.py             # exit 0
git diff --check                                                  # clean (CRLF only)
```

## Blockers or failures

- None.
- One incidental fix during B1: psycopg2 misparses literal `%` in SQL comments and string literals when ANY params are passed. Resolved by parameterizing the suffix patterns instead of inlining them (`%s` placeholders bound to `'%.JK'` / `'%.BK'`). Documented in the SQL header.

## Follow-up session (2026-05-23) — NVDR dedup landed

Signal-time NVDR dedup is now implemented in production. Open Q #1 in `docs/tasks/idx_set_enablement_plan.md` is fully resolved.

### What landed

- `screener/core.py` gained `dedupe_set_nvdr_results(results)` and the `_set_group_key` / `_liquidity_sort_key` helpers. It runs **after** the existing `dedupe_results` symbol/ticker dedup, on every `DATA_SOURCE` path (`yfinance` / `ibkr` / `auto`).
- Policy: for each SET ordinary/NVDR collision (group key = `REPLACE(symbol, '-R.BK', '.BK')`), keep the row with higher `avg_volume_20d`; fallback to higher `volume`; final tie-break is the ordinary `.BK`. Non-SET symbols pass through untouched. Unique NVDRs with no ordinary counterpart pass through untouched.
- `screening/screening_utils.py` `should_pass_screening` now carries `avg_volume_20d` into its result dict when present, so the screener-side dedup has the liquidity field available.
- Combine-path logging extended: prints `set_nvdr_dropped=N` and a separate `total_after_nvdr_dedupe=N` when the dedup actually fired.
- Tests at `tests/provider_tests/test_set_nvdr_dedup.py` cover all six required cases (NVDR-wins, ordinary-wins, tied-liquidity-to-ordinary, unique-NVDR-preserved, non-SET-untouched, end-to-end `DATA_SOURCE=auto`).

### Also in the same session

- `screening/screening_utils.py` was missing `import pandas as pd` -- `calculate_atr` uses `pd.concat` and silently fell through its `except` returning the default 0.05. py_compile cannot catch that. Fix is one line; new unit tests at `tests/unit_tests/test_screening_technicals.py` cover RSI / SMA / ATR helpers and the `atr_enabled` branch in `should_pass_screening`. The ATR test was specifically designed to fail before the import fix.

### Tests

```text
.\.venv\Scripts\python.exe -m pytest tests\unit_tests\test_screening_technicals.py -q   # 10/10
.\.venv\Scripts\python.exe -m pytest tests\provider_tests -q                            # 33/33
.\.venv\Scripts\python.exe -m pytest tests\analytics\test_backtest_52w_strategy.py -q   # 9/9
```

### Backtest-side mirror

The same NVDR policy is also wired into `scripts/spark/06_backtest_52w_strategy.py` as `--dedupe-nvdr`, plus an explicit `_set_group_key` matched 1:1 with the screener helper (tested via cross-reference in `tests/analytics/test_backtest_52w_strategy.py::test_set_group_key_matches_screener_helper`). The diagnostic run on the 2024-01-01..2026-04-30 NSE+IDX+SET cohort showed event-dedup taking 123 -> 78 and NVDR-dedup then a no-op (no same-date X.BK/X-R.BK collisions survived event dedup). See `docs/tasks/backtest_52w_strategy_progress.md` "V2 session" for the four-run table.

## Next recommended step

1. **NVDR dedup (DONE 2026-05-23):** see "Follow-up session" above. `screener.core.dedupe_set_nvdr_results` plus tests.
2. **Schedule the `.bat`** under Windows Task Scheduler per the steps above (operator action, one-time).
3. **Re-run the v1 backtest after NVDR dedup** to compare signal count and forward-return distribution; AOT.BK vs AOT-R.BK divergence in the v1 results suggests this will change the per-horizon means meaningfully.
4. Optional: extend `mark_inactive_idx_set_dead_tickers.py` (or fork it) to handle other markets that accumulate dead tickers (LSE `0XXX.L` historical IDs are the next obvious candidate -- noted in `docs/master_development_plan.md` Task 12 caveat).
5. Optional: an INFO log of the B1 deactivation event in some operational journal -- the repo currently has no central operations log; this would be a new artifact rather than an extension of existing infrastructure.

## Notes for the next agent

- `tickers` row counts decreased by 35 ACTIVE rows (NOT total -- the rows are still present, just status=INACTIVE). Anything that filters on `status = 'ACTIVE' OR status IS NULL` will see the smaller universe; anything counting `SELECT COUNT(*)` will not.
- The dead-ticker script is **idempotent**. Re-running with `--apply` after a clean state reports "No candidates match the strict dead-ticker rule" and makes zero writes.
- The 35-row UPDATE is small enough that no transaction batching or `execute_values` was warranted; the existing `db.update_ticker_status` helper handles per-row updates fine at this cap. If a future cleanup pass needs to touch thousands of tickers, a single bulk UPDATE with a derived table would be the better path -- not because the per-row loop is unsafe, but because it cuts to one transaction.
- The B4 `--exchange` flag is *exchange-scoped to the `tickers.market` column*, not to the yfinance ticker suffix. Pass market codes (`IDX`, `SET`, `NSE`), not suffixes (`.JK`, `.BK`).
- `scheduler/run_idx_set_fundamentals_refresh.bat` returns the wrapper script's exit code, which is 0 when the seeder either runs successfully *or* skips for not-due. Task Scheduler will treat both as success -- which is correct, since the wrapper's design is "fire daily, decide internally."
