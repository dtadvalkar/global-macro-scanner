# SQL Externalization Closeout + DB Recovery Plan

## Context

SQL externalization (the original Plan 3, two-track) shipped in commit `c624ffd refactor: externalize active ETL SQL` on 2026-04-30. The original plan is complete:

- **Track 1 (SQL externalization):** Phase A (`db.py` helpers + `sql/` tree) → Phase B (exemplar) → Phase C (5 ETL scripts) → Phase D (`storage/database.py` deletion + 4 callers migrated/retired).
- **Track 2 (runtime safety):** Phase S1 (`data/providers.py:492` IN-clause parameterized) → Phase S2 (`data/cache_manager.py` pruned to 4 read-only methods).

During verification of the migrated `scripts/utils/reset_db_schema.py`, I imported the module to check it loaded — and the script's top-level executable code (no `__main__` guard, a pre-existing footgun preserved by the migration) committed a `TRUNCATE TABLE tickers, stock_fundamentals RESTART IDENTITY CASCADE`. The success-line `print("✅ ...")` then failed with `UnicodeEncodeError` on Windows codepage 1252 — masking what had already happened. By the time I noticed, both tables were at 0.

Damage:
- `tickers`: 5824 → 0
- `stock_fundamentals`: 1844 → 0
- All other tables intact (`ibkr_fundamentals`, `ibkr_market_data`, `prices_daily`, `current_market_data`)

The script has been hardened (under `if __name__ == "__main__":`, typed `TRUNCATE tickers stock_fundamentals` confirmation phrase, ASCII-only output, no broad-except) and that fix is in the same commit. No backup snapshot existed.

User has deferred recovery. This plan captures the state and the exact recovery sequence so it can be picked up cleanly later.

**2026-05-02 decision update:** do not execute this recovery before the Spark plan. The Spark work can proceed with `tickers` and `stock_fundamentals` empty unless it explicitly depends on scanner/ETL smoke tests, `main.py --exchanges ...`, or logic that joins those two tables. Treat the empty tables as known local DB state, not as a blocker for Spark. Before anyone eventually runs this recovery, revise or re-check the `tickers` reseed path against current code because FinanceDatabase seeding is now the primary path for most exchanges.

---

## What shipped (commit `c624ffd`)

| Track | Phase | Result |
|---|---|---|
| 2 | S1 | `data/providers.py:_screen_stored_market_data` IN clause parameterized; empty-list early return |
| 1 | A | `sql/{etl,schema,analytics}/` tree; `db.py::load_sql/query_file/execute_file/execute_values_file` |
| 1 | B | `flatten_ibkr_market_data.py` exemplar — delta SELECT + upsert externalized |
| 1 | C.1 | `collect_daily_ibkr_market_data.py` migrated to `db.py`; ibkr_market_data upsert externalized |
| 1 | C.2 | `flatten_ibkr_final.py` migrated; CREATE_SQL + read SELECTs externalized; dynamic UPSERT kept in Python |
| 1 | C.3 | `collect_ibkr_fundamentals.py` resume-filter SELECT + upsert externalized |
| 1 | C.4 | `collect_daily_yfinance.py` migrated; prices_daily upsert externalized; `bulk_insert_prices(df)` signature |
| 1 | C.5 | `collect_historical_yfinance.py` migrated; matched signature change |
| 2 | S2 | `data/cache_manager.py` pruned: 18 broken methods deleted; 4 read-only members kept; `use_database=False` guards added |
| 1 | D | `storage/database.py` deleted; 3 utils migrated to `db.py`; `populate_nse_fundamentals.py` retired |

Audit fixes folded into the same commit:
- Trailing newline at EOF in `data/cache_manager.py` (flagged by `git diff --check`).
- `if not self.use_database: return` guards in `ensure_table_exists` and `get_fundamentals` (silent disabled-DB path).

Commit shape: 30 files, +589 / -1491. `.claude/settings.local.json` correctly excluded as harness state.

Handoff note: `docs/tasks/sql_externalization_progress.md` (with closeout update appended).

---

## Current DB state (Step 1 complete 2026-05-09)

| Table | Rows | Status |
|---|---|---|
| `tickers` | 0 | **EMPTY** (was 5824) — Step 2 still deferred |
| `stock_fundamentals` | **1,844** | **RESTORED 2026-05-09** via `flatten_ibkr_final` from intact `ibkr_fundamentals`. Per-exchange counts match Task 11 baseline exactly. |
| `ibkr_fundamentals` | 2108 (1907 with `xml_snapshot`) | intact (source for the Step 1 restore) |
| `ibkr_market_data` | 1461 | intact |
| `prices_daily` | 5,598,705 | intact (5.6M baseline) |
| `current_market_data` | 923 | intact, last_updated 2026-04-27 (stale — refresh after Step 2) |

The Step 1 restore wrote 1,844 upserts with 63 XML-parse errors (data quality on the IBKR raw side, not a regression introduced by the C.2 refactor). Per-exchange acceptance: NSE 408 / SEHK 597 / ASX 327 / LSE 241 / SGX 124 / TADAWUL 96 / JSE 51 = 1,844 — zero drift from the baseline.

---

## Recovery sequence (deferred; not required before Spark)

Run this sequence only when scanner/ETL validation needs `tickers` and `stock_fundamentals` restored, or when the user explicitly asks to recover the local DB. This is intentionally not part of the Spark-plan critical path.

### Step 1 — Restore `stock_fundamentals` (DONE 2026-05-09; deterministic, ≤1 min)

```bash
PYTHONPATH='.' .venv/Scripts/python -m scripts.etl.ibkr.flatten_ibkr_final
```

Re-flattens the 1907 XML rows from intact `ibkr_fundamentals` via the refactored `flatten_ibkr_final.py`. The DDL comes from `sql/schema/stock_fundamentals.sql`; the read SELECTs from `sql/etl/ibkr_fundamentals_all.sql`; the dynamic UPSERT stays Python-resident over `SCHEMA_COLUMNS`.

**Expected output:** 1844 rows total, distributed per Task 11 baseline:
- NSE 408, SEHK 597, ASX 327, LSE 241, SGX 124, TADAWUL 96, JSE 51

**Verify:**
```bash
python db.py health    # issues: []
PYTHONPATH='.' .venv/Scripts/python -c "
from db import get_db
db = get_db()
print('total:', db.query('SELECT COUNT(*) FROM stock_fundamentals', fetch='one')[0])
# Per-exchange:
for r in db.query('''SELECT
  CASE
    WHEN ticker LIKE %s THEN %s WHEN ticker LIKE %s THEN %s
    WHEN ticker LIKE %s THEN %s WHEN ticker LIKE %s THEN %s
    WHEN ticker LIKE %s THEN %s WHEN ticker LIKE %s THEN %s
    WHEN ticker LIKE %s THEN %s ELSE %s END AS exch, COUNT(*)
FROM stock_fundamentals GROUP BY 1 ORDER BY 1''',
  ('%.NS','NSE','%.HK','SEHK','%.AX','ASX','%.L','LSE','%.SI','SGX','%.SR','TADAWUL','%.JO','JSE','OTHER')):
    print(r)
"
```

**Stop condition:** if total != 1844 or per-exchange counts diverge from baseline, halt and investigate before Step 2. The likely failure mode would be an XML parse regression introduced by the C.2 refactor (which only changed the DB layer + read SELECT boundary; XML parse logic is unchanged).

### Step 2 — Reseed `tickers` (DONE 2026-05-09)

Executed via the FinanceDatabase-backed `screener.universe.get_universe(markets)` path with all seven IBKR-free exchanges enabled. The `is_market_fresh` gate returned False for every market (table was empty), so the FD seed branch fired for each, and `db.save_tickers` committed the results. Final per-market counts match the Task 11 universe baselines exactly:

| Market | Count | Notes |
|---|---:|---|
| NSE | 1,933 | Full FD list (NSE intentionally excluded from `CAP_FILTERED_EXCHANGES`) |
| LSE | 1,326 | Cap-filtered (Large+Mid+Small) |
| SEHK | 664 | Cap-filtered |
| ASX | 498 | Cap-filtered |
| SGX | 172 | Cap-filtered |
| TADAWUL | 103 | Cap-filtered |
| JSE | 81 | Cap-filtered |
| **Total** | **4,777** | |

**Masking-bug surfaced and fixed during the run.** Each market logged a misleading `Warning: <market> FD load failed: 'charmap' codec can't encode character '✅'` because the success-line print at `screener/universe.py:79` used a `✅` emoji that fails on Windows codepage 1252; the broad `except Exception` at line 83 then caught the UnicodeEncodeError and labeled it as an FD failure. The save itself had already committed. Same class of bug as the `reset_db_schema.py` incident this whole plan exists to recover from. Fixed in commit 9ea60c7 by switching the two non-ASCII print literals in `get_universe` to `[ok]`/`[info]` prefixes, matching the ASCII-only convention added to DEVELOPMENT.md in fcd249f.

**Verification:**
- `.venv/Scripts/python.exe db.py health` → `issues: []`, `tickers.row_count = 4777`.
- `SELECT market, COUNT(*) FROM tickers GROUP BY market` → matches the table above.
- No call to `seed_exchange_tickers.py` was needed; static-list fallback remains available if a future FD coverage gap appears.

### Step 3 — End-to-end verification

After both restore steps:

```bash
# DB health
.venv/Scripts/python db.py health
.venv/Scripts/python db.py validate

# Universe pre-flight: counts match expected baselines
# (Task 10 final: 264 tickers SEHK/LSE/JSE/TADAWUL; Task 11: 1844 fundamentals)

# Pipeline smoke (no live collection — exercises the refactored path)
PYTHONPATH='.' .venv/Scripts/python main.py --exchanges NSE --mode test --skip-collection --skip-flattening
# Expected: data freshness check warns on stale current_market_data (>24h since 2026-04-27).
# In TEST mode the pipeline continues; screening returns 0 catches against post-restore data.

# Optional full path (live IBKR required)
PYTHONPATH='.' .venv/Scripts/python main.py --exchanges NSE --mode test
```

---

## Step 4 — Optional follow-ups (not gated on recovery)

Identified during the work but excluded from the first pass. Take only if the user wants them.

1. **Polish.** Externalize the `_screen_stored_market_data` SELECT body to `sql/analytics/screen_stored_market_data.sql`. Pure refactor, decoupled from S1's safety fix. Was deliberately deferred per the two-track plan.
2. **Verify the new `reset_db_schema.py` confirmation flow.** Run interactively in a sacrificial environment, type the wrong phrase, confirm "Aborting; no changes made"; then type the right phrase against an empty DB to confirm the truncate succeeds and exits cleanly.
3. **Retire `scripts/etl/ibkr/collect_ibkr_market_data.py`** — legacy variant excluded from the first pass; has a pre-existing undefined-`conn`/`cur` bug. Either fix or delete.
4. **Audit `scripts/etl/finance_db/flatten_fd_nse.py`** — still in use via `collect_ibkr_fundamentals.py --source fd_capfilter` and `orchestrate_ibkr_pipeline.py`. Decide if retirement is on the roadmap; if so, schedule the migration now that `db.py` is the standard.
5. **`/security-review` or `/ultrareview` on commit `c624ffd`** to lock in the SQL injection fix (Phase S1) and cache_manager pruning. Independent verification on the diff.
6. **Add `pre-commit` or CI guard against the import-side-effect class of bug** — anything destructive must be under `if __name__ == "__main__":`. The reset_db_schema incident is the canonical example.

---

## Risks when recovery eventually runs

1. **Step 1 depends on the C.2 refactor being correct.** The migration was verified offline (XML parse logic untouched; only DB layer + read-SELECT boundary changed) and the SQL files round-tripped against the existing schema, but no end-to-end `flatten_ibkr_final` run has happened post-refactor. If it explodes, the data is still recoverable — the source XML in `ibkr_fundamentals` is intact.
2. **`tickers` reseed must follow current code, not stale memory.** As of 2026-05-02, `screener/universe.py` is the primary FinanceDatabase-backed seed path for most markets; `seed_exchange_tickers.py` is mainly the static-list fallback for SEHK/LSE/JSE/TADAWUL.
3. **Empty `tickers` cascades.** Many in-scope ETL scripts (`fetch_active_tickers`, `get_exchange_tickers`, `load_seed_tickers`) gracefully bail with "No active tickers — exiting." That is the correct empty-DB behavior, not a regression. Don't chase it.
4. **The `c624ffd` commit is local-only.** Not pushed to `origin/main`. Pushing is a separate explicit decision.
5. **Spark work should not be blocked by this plan.** Only pause Spark for DB recovery if the Spark task needs scanner validation or directly depends on restored `tickers` / `stock_fundamentals` contents.

---

## Critical files (for recovery)

- `C:\Dev\Global Market Scanner\scripts\etl\ibkr\flatten_ibkr_final.py` — Step 1 entrypoint
- `C:\Dev\Global Market Scanner\sql\schema\stock_fundamentals.sql` — Step 1 DDL (loaded by flatten_final)
- `C:\Dev\Global Market Scanner\sql\etl\ibkr_fundamentals_all.sql` — Step 1 read SELECT
- `C:\Dev\Global Market Scanner\screener\universe.py` — Step 2 primary FD-driven seeding path
- `C:\Dev\Global Market Scanner\scripts\etl\ibkr\seed_exchange_tickers.py` — Step 2 static fallback for SEHK/LSE/JSE/TADAWUL
- `C:\Dev\Global Market Scanner\db.py` — health/validate baseline + helpers
- `C:\Dev\Global Market Scanner\docs\tasks\sql_externalization_progress.md` — full handoff note

---

## Recommended sequence summary

| When | Action | Risk |
|---|---|---|
| Now | Confirm deferred runbook; do not execute before Spark. | None |
| Spark plan | Proceed unless Spark explicitly needs scanner/ETL validation or restored `tickers` / `stock_fundamentals`. | Low — empty tables are known local DB state |
| 2026-05-09 | **Step 1 complete:** `stock_fundamentals` restored to 1,844 rows via `flatten_ibkr_final`. Per-exchange counts match baseline exactly. | Risk realized: low — clean restore. |
| 2026-05-09 | Pre-Step-2 audit completed: confirmed `db.save_tickers` is the sole writer, called by `screener/universe.py` (FD primary) and `seed_exchange_tickers.py` (static fallback for SEHK/LSE/JSE/TADAWUL only). | None (read-only) |
| 2026-05-09 | **Step 2 complete:** `tickers` reseeded to 4,777 rows via `get_universe(markets)` for all 7 active exchanges. Counts match Task 11 baselines exactly. Masking bug at `screener/universe.py:79` (`✅` emoji + Windows cp1252) surfaced and fixed in commit 9ea60c7. | Risk realized: low — bug was cosmetic; data path was correct. |
| Later, gated | Step 2: reseed `tickers` through FD-backed universe path first; use static fallback only where appropriate. | Medium — depends on FD availability and current market mappings |
| Later | Step 3: end-to-end NSE `--mode test --skip-collection` smoke. | Low — refactor verified offline |
| Later | Step 4 follow-ups (optional, à la carte). | Low |
