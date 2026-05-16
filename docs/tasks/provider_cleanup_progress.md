# Provider Cleanup Progress

## Task

- Short task name: Stabilize safety/provider cleanup before IDX/SET enablement
- Owner / agent: Claude (Opus 4.7)
- Date: 2026-05-16

## Status

- Current status: IDX/SET enablement Phases 0..5 DONE 2026-05-16; provider cleanup + yahooquery pin + monthly wrapper landed. Worktree is review-ready but uncommitted.
- Confidence: High on the verifications below.

## Files touched

This session's edits:

- `config/markets.py` — flipped `MARKETS['idx']` and `MARKETS['set']` from `True` back to `False`. The IDX/SET plan keeps them gated until yahooquery seeding and end-to-end smoke pass; the runtime toggle was out of sync with the plan.

Pre-existing dirty worktree (untouched this session, verified-as-correct):

- `.claude/settings.local.json` — local Claude permission cache. Keep out of project commits.
- `.pre-commit-config.yaml` — wires the new `import-safety` hook alongside `sql-guard`.
- `DEVELOPMENT.md` — documents both pre-commit guards under "SQL externalization (mandatory for destructive verbs)".
- `data/providers.py` — `OptimizedYFinanceProvider` rewritten to bulk `yf.download` + cached market cap; verified against the audit checklist below.
- `docs/master_development_plan.md` — updated provider description for the bulk path.
- `docs/tasks/idx_set_enablement_plan.md` — new; Phase 0..5 enablement plan, not yet executed.
- `scripts/hooks/import_safety.py` — new AST-based pre-commit guard.

Deletions (already in the index):

- `data/providers_optimized.py`, `data/rate_limit_solutions.py`, `docs/yfinance_rate_limiting_guide.md` — no remaining references in the codebase (grep clean).

## Commands run

```text
git log --oneline -20
git status --short
.\.venv\Scripts\python.exe scripts\hooks\import_safety.py       # exit 0
.\.venv\Scripts\python.exe scripts\hooks\sql_guard.py           # exit 0
git diff --check                                                # clean (only CRLF warnings)
.\.venv\Scripts\python.exe -c "import ast; ast.parse(open('data/providers.py', encoding='utf-8').read())"  # OK
.\.venv\Scripts\python.exe -c "from data.providers import OptimizedYFinanceProvider"  # OK
.\.venv\Scripts\python.exe -c "from config import MARKETS; print(MARKETS['idx'], MARKETS['set'])"  # False False
# Synthetic hook test inside repo: module-scope db.execute_file flagged, function/class/main-guard variants ignored. Hook exited 1 with one finding, as designed.
```

Pre-existing `SyntaxWarning: invalid escape sequence '\.'` in `scripts/etl/ibkr/migrate_to_ib_async.py:139` surfaces on every Python invocation. Not chased — does not affect exit codes.

## What changed

Verifications completed this session:

1. **`scripts/hooks/import_safety.py`** — AST walks the tree and flags any `db.execute_file` / `db.execute_values_file` / `db.truncate_table` call whose AST id is not inside a `FunctionDef` / `AsyncFunctionDef` / `ClassDef` body or under an `if __name__ == "__main__":` guard. Confirmed empirically with a synthetic test file in repo: the module-scope call is reported, the function/class/main-guard variants pass. Wired in `.pre-commit-config.yaml:18-28`; documented in `DEVELOPMENT.md:99-103, 120`.

2. **`OptimizedYFinanceProvider`** audit (`data/providers.py:17-165`):
   - Single bulk `yf.download(tickers=" ".join(viable), period='1y', group_by='ticker', ...)` at `:122`. No fallback per-ticker loop.
   - `_extract_per_ticker` slices the bulk multi-index frame per symbol; no `yf.Ticker(...).history()` in the class.
   - Market cap sourced from `FundamentalCacheManager.get_fundamentals(symbol)['market_cap_usd']` at `:62-63`. No `.info` access in this class.
   - `should_pass_screening(...)` return dict is appended to results (`:160-162`), not the raw `symbol_data`.
   - Failed-ticker cache still marks INACTIVE after 3 empty pulls (`:148-151`).
   - Other paths preserved: legacy `YFinanceProvider`, `IBKRProvider`, `IBKRScannerProvider` all untouched.

3. **IDX/SET toggle mismatch resolved** — `MARKETS['idx']` and `MARKETS['set']` set to `False` in `config/markets.py`. The plan in `docs/tasks/idx_set_enablement_plan.md` explicitly keeps these gated until Phase 4 smoke passes; the previous `True` values would have routed IDX/SET universe into the screener before market-cap fundamentals existed for those tickers.

## Blockers or failures

- None for this stabilization pass.
- Pre-existing `SyntaxWarning` in `scripts/etl/ibkr/migrate_to_ib_async.py:139` is noted but out of scope.

## Phase 1 closeout — 2026-05-16

**Files touched:**

- `screener/universe.py` — added `IDX` and `SET` to `CAP_FILTERED_EXCHANGES`; added `FD_COUNTRY_FILTER = {'IDX': 'Indonesia', 'SET': 'Thailand'}`; routed those db_keys through `equities.search(country=..., exchange=fd_key)` while leaving other exchanges on exchange-only search.
- `docs/tasks/idx_set_enablement_plan.md` — marked Phase 1 DONE with actual counts; rewrote the bottom "Next recommended step" to point at Phase 2.

**Commands run:**

```text
.\.venv\Scripts\python.exe -c "from screener.universe import get_universe; from config import MARKETS; m = {**MARKETS, 'idx': True, 'set': True}; universe = get_universe(m); print(f'total: {len(universe)}')"
# Output: 'Loaded 5251 stocks total' — IDX seeded 149, SET seeded 325.
.\.venv\Scripts\python.exe -c "from db import get_db; db = get_db(); print(db.query('SELECT market, COUNT(*) FROM tickers WHERE market IN (%s,%s) GROUP BY market ORDER BY market', ('IDX','SET'))); db.close()"
# Output: [('IDX', 149), ('SET', 325)]
.\.venv\Scripts\python.exe scripts\hooks\import_safety.py   # exit 0
.\.venv\Scripts\python.exe scripts\hooks\sql_guard.py       # exit 0
git diff --check                                            # clean (only CRLF warnings)
```

**Results:**

- IDX: 575 FD rows -> 149 after Large+Mid+Small filter. **Matches expected 149.**
- SET: 1,247 FD rows -> 325 after Large+Mid+Small filter. **Matches expected 325.**
- Combined IDX/SET universe: 474. `MARKETS['idx']` / `MARKETS['set']` remain `False` (verified post-edit).
- `-R.BK` (NVDR) ticker variants intentionally **not** filtered — filtering would drop SET to 194, breaking expected count and pre-empting an explicit downstream decision.

Side-effect note: the verification call also refreshed several other exchanges' universes (NSE, ASX, SGX, SEHK, LSE, JSE, TADAWUL) — pre-existing `is_market_fresh` staleness behavior, not caused by this change. Their seeded counts match prior records.

## Phase 2 closeout — 2026-05-16

**Files touched:**

- `sql/etl/stock_fundamentals_yq_upsert.sql` (new) — sparse UPSERT into `stock_fundamentals`. Writes the underlying SQL column `mkt_cap_usd` (the plan text was using the `market_cap_usd` Python alias from `data/cache_manager.py:81`; corrected in this pass). Tuple contract: `ticker, company_name, mkt_cap_usd, price_currency, exchange_code, exchange_country`. `last_fundamental_update` is set to `CURRENT_TIMESTAMP` only on conflict — same pattern as `stock_fundamentals_fd_upsert.sql`; first insert leaves it NULL.
- `scripts/etl/yahooquery/seed_idx_set_fundamentals.py` (new) — bulk seeder. `if __name__ == "__main__":` guard, no side effects on import, ASCII-only output, sys.path bump matches `collect_daily_yfinance.py` convention. Single 474-symbol chunk via Yahoo plural `?symbols=` endpoint; FX rates memoised per currency via `functools.lru_cache` patched onto `data.currency.get_live_fx_rate` (so `usd_market_cap` keeps being the canonical conversion entry point and we avoid 438 redundant FX-API hits).
- `docs/tasks/idx_set_enablement_plan.md` — marked Phase 2 DONE; corrected `market_cap_usd` -> `mkt_cap_usd` in the Phase 2 / Phase 3 sections (SQL column vs Python alias); rewrote bottom Next-step to point at Phase 3 with a percentile probe template.

**Commands run:**

```text
.\.venv\Scripts\python.exe -c "import scripts.etl.yahooquery.seed_idx_set_fundamentals as s; print('import ok')"
# Output: import ok  (confirms zero side effects on import)
.\.venv\Scripts\python.exe scripts\etl\yahooquery\seed_idx_set_fundamentals.py
# Output:
#   Loaded 474 IDX+SET tickers from DB.
#   Chunk 1: 474 symbols in 1.31s
#   Built 438 rows (36 skipped) in 2.64s wall.
#   [ok] Upserted 438 rows into stock_fundamentals.
.\.venv\Scripts\python.exe -c "..."  # DB count probe
# Output: [('IDX', 145, 145), ('SET', 293, 293)]
.\.venv\Scripts\python.exe scripts\hooks\import_safety.py   # exit 0
.\.venv\Scripts\python.exe scripts\hooks\sql_guard.py       # exit 0
git diff --check                                            # clean (CRLF warnings only)
from config import MARKETS                                  # idx: False, set: False
```

**Results:**

| Exchange | with_mcap | total seeded (Phase 1) | coverage | threshold |
|---|---:|---:|---:|---|
| IDX | 145 | 149 | 97.3% | >= 120 of 149 |
| SET | 293 | 325 | 90.2% | >= 260 of 325 |

438 rows upserted; 36 skipped (currency mismatch, missing marketCap, or non-EQUITY). Wall time 2.64s vs 30s budget. All upserted rows have positive `mkt_cap_usd` (the `with_mcap` count equals the total for each exchange). `MARKETS['idx']` and `MARKETS['set']` confirmed `False` post-run.

Schema-column confirmation: the new SQL writes `mkt_cap_usd` (not `market_cap_usd`). Verified by the percentile probe returning data from a `mkt_cap_usd > 0` filter and by inspecting `sql/schema/stock_fundamentals.sql:14`.

**Blockers / failures:** none.

**Pre-existing noise:** `scripts/etl/ibkr/migrate_to_ib_async.py:139` SyntaxWarning still emitted on every Python invocation; explicitly out of scope per Darshan's note.

## Phase 3 closeout — 2026-05-16

**Files touched:**

- `config/markets.py` — bumped IDX and SET `threshold_usd` only:
  - IDX: `150_000_000` -> `600_000_000`
  - SET: `150_000_000` -> `450_000_000`
  - Provider stays `YFINANCE`; `type` stays `EMERGING`; all other exchange entries untouched.
- `docs/tasks/idx_set_enablement_plan.md` — marked Phase 3 DONE with the threshold table, the distribution that drove the choice, and the mapping confirmation; rewrote Next-step to point at Phase 4 with pre-conditions (OHLCV seed + scheduler entries).

**Commands run:**

```text
.\.venv\Scripts\python.exe -c "from config.markets import get_min_market_cap; print(get_min_market_cap('IDX')); print(get_min_market_cap('SET'))"
# Output: 600000000  450000000
.\.venv\Scripts\python.exe -c "..."  # retained-count probe
# Output:
#   IDX 600000000 (87, 145) retain=60.0%
#   SET 450000000 (176, 293) retain=60.1%
.\.venv\Scripts\python.exe -c "from config import MARKETS; print(MARKETS['idx'], MARKETS['set'])"
# Output: False False
.\.venv\Scripts\python.exe scripts\hooks\import_safety.py   # exit 0
.\.venv\Scripts\python.exe scripts\hooks\sql_guard.py       # exit 0
git diff --check                                            # clean (CRLF warnings only)
```

**Results:** thresholds match plan exactly; retain rates 60.0% / 60.1% hit the ~60% target band. `screening/screening_utils.py:52` already maps `.JK -> IDX` and `.BK -> SET`, so `get_min_market_cap()` routes correctly without further changes. `MARKETS['idx']` and `MARKETS['set']` confirmed `False`.

**Blockers / failures:** none.

## Phase 4 closeout — 2026-05-16

**Files touched:**

- `config/markets.py` — flipped `MARKETS['idx']` and `MARKETS['set']` from `False` to `True` after both smokes passed. Inline comment updated to record the enablement date and counts.
- `docs/tasks/idx_set_enablement_plan.md` — marked Phase 4 DONE with backfill / smoke / scheduler results; bottom Next-step rewritten to point at Phase 5.

**Database state changed:**

- `prices_daily`: +208,781 rows across 146 `.JK` and 293 `.BK` distinct tickers (2y history). 35 tickers failed (delisted or NVDR variants not on Yahoo).
- No other tables modified this pass.

**Commands run:**

```text
# Preflight (no state change)
.\.venv\Scripts\python.exe -c "..."  # 4-table count probe
# Output: prices (0,0) current (0,0) tickers IDX=149 SET=325 fundamentals (145/145, 293/293)

# Backfill
.\.venv\Scripts\python.exe scripts\etl\yfinance\collect_historical_yfinance.py --exchange IDX,SET --period 2y
# Result: 208,781 rows in 39.4s, 35 failures (delisted/NVDR)

# Post-backfill verify
.\.venv\Scripts\python.exe -c "..."  # prices_daily count
# Output: (69797, 138984) ; distinct .JK=146, .BK=293

# Smokes (DATA_SOURCE=yfinance via $env:DATA_SOURCE)
.\.venv\Scripts\python.exe main.py --exchanges IDX --mode test --skip-collection --skip-flattening
# Exit 0, 149 tickers, 0 catches, DAILY PIPELINE COMPLETE, single bulk yf.download
.\.venv\Scripts\python.exe main.py --exchanges SET --mode test --skip-collection --skip-flattening
# Exit 0, 325 tickers, 0 catches, DAILY PIPELINE COMPLETE, single bulk yf.download

# Final checks
.\.venv\Scripts\python.exe -c "from config import MARKETS; print(MARKETS['idx'], MARKETS['set'])"
# Output: True True
.\.venv\Scripts\python.exe scripts\hooks\import_safety.py   # exit 0
.\.venv\Scripts\python.exe scripts\hooks\sql_guard.py       # exit 0
git diff --check                                            # clean (CRLF warnings only)
```

**Results:**

- **IDX smoke:** PASS. 149 tickers loaded; bulk yfinance download; 0 catches; pipeline complete; exit 0; 3 delisted-ticker warnings (RMBA / FREN / TURI) but no rate-limit symptoms.
- **SET smoke:** PASS. 325 tickers loaded; bulk yfinance download; 0 catches; pipeline complete; exit 0; 32 delisted/NVDR warnings (same set as backfill) but no rate-limit symptoms.
- **Toggles:** both flipped to `True`. Verified.
- **Scheduler:** already supports IDX/SET via `emerging_asia` region (Bangkok 10:30 - 16:30, `scheduler/market_scheduler.py:34-35,61-65`). No edit needed.
- **Step 3 freshness warning:** `current_market_data` is stale (171.7 h old). Expected and acceptable per the smoke criteria; the IDX/SET path uses bulk yfinance, not `current_market_data`. The daily IBKR collector for the other seven exchanges will refresh it.

**Blockers / failures:** none.

**Yahoo delisted-ticker hygiene:** 35 `.JK`/`.BK` tickers in the `tickers` table return Yahoo 404 / "possibly delisted". They are currently still marked `ACTIVE` (or NULL status) and will be retried on every daily collector run, adding ~10s of noise to logs each day. Side-cleanup candidate for the same Phase 5 pass.

## Phase 5 closeout — 2026-05-16

**Files touched:**

- `requirements.txt` — added `yahooquery==2.4.1` under the "Financial Data APIs" section. Other pins untouched.
- `scripts/etl/yahooquery/schedule_monthly_idx_set_fundamentals.py` (new) — monthly refresh wrapper. ASCII-only; `if __name__ == "__main__":` guard; no DB / subprocess side effects on import; supports `--run` (force), `--dry-run` (print only), and default due-rule mode. Last-update read goes through `db.py/get_db()`, not raw `psycopg2`. Seeder is invoked via `sys.executable` with `cwd=REPO_ROOT`. Exit codes match the brief (0 not-due, 0 success, nonzero on seeder failure).
- `docs/tasks/idx_set_enablement_plan.md` — marked Phase 5 DONE; rewrote bottom Next-step to point at commit/review or optional side-cleanup.
- `alerts/telegram.py` — **not modified**. Pre-existing `_EXCHANGE_INFO` (line 22-23) already maps `.JK -> 'Rp '` and `.BK -> '฿'`. Verified before considering an edit.
- `scheduler/market_scheduler.py` — **not modified**. The brief instructs against scheduler refactor unless a runtime gap exists; the monthly wrapper lives under `scripts/etl/yahooquery/` and is meant to be triggered externally (Windows Task Scheduler / cron / upstream orchestrator).

**Commands run:**

```text
.\.venv\Scripts\python.exe -c "import scripts.etl.yahooquery.schedule_monthly_idx_set_fundamentals as s; print('import ok')"
# Output: import ok

.\.venv\Scripts\python.exe scripts\etl\yahooquery\schedule_monthly_idx_set_fundamentals.py --dry-run
# Output: Should run: True / Reason: No previous IDX/SET fundamental update found (NULL)
#         [dry-run] Would execute: <python> <seeder>   /  cwd: C:\Dev\Global Market Scanner

.\.venv\Scripts\python.exe scripts\etl\yahooquery\schedule_monthly_idx_set_fundamentals.py --run
# Seeder output: Loaded 474 IDX+SET tickers; Chunk 1 = 474 symbols in 1.01s; Built 438 rows (36 skipped); Upserted 438 rows.
# Wrapper output: [ok] Seeder completed successfully.

# Default mode after forced run, confirming due-rule path resolves to skip
.\.venv\Scripts\python.exe scripts\etl\yahooquery\schedule_monthly_idx_set_fundamentals.py
# Output: Last IDX/SET update: 2026-05-16 16:16:22 / Should run: False / [skip] Not due. Use --run to force.

# Post-run counts probe (executed via temporary scratch file so PowerShell didn't choke on inline % wildcards)
('IDX', 145, 145, 2026-05-16 16:16:22)
('SET', 293, 293, 2026-05-16 16:16:22)

# Final checks
.\.venv\Scripts\python.exe -c "from config import MARKETS; print(MARKETS['idx'], MARKETS['set'])"   # True True
.\.venv\Scripts\python.exe scripts\hooks\import_safety.py   # exit 0
.\.venv\Scripts\python.exe scripts\hooks\sql_guard.py       # exit 0
git diff --check                                            # clean (CRLF warnings only)
```

**Results:**

| Item | Expected | Actual |
|---|---|---|
| `yahooquery` pinned | `yahooquery==2.4.1` | yes, added under Financial Data APIs |
| Monthly wrapper import | no side effects | confirmed; `import scripts.etl.yahooquery.schedule_monthly_idx_set_fundamentals` returns clean |
| `--dry-run` exit | 0, no subprocess | confirmed |
| `--run` exit | 0; seeder succeeds | confirmed; 438 rows upserted in ~2.4s |
| Post-run IDX `with_mcap` | ~145 | 145 (= total) |
| Post-run SET `with_mcap` | ~293 | 293 (= total) |
| Post-run `last_fundamental_update` | populated | 2026-05-16 16:16:22 for both exchanges |
| Default mode (after run) | skip with exit 0 | confirmed |
| Telegram `.JK`/`.BK` currency | `Rp` / `฿` | pre-existing in `alerts/telegram.py:22-23`; no edit needed |
| `MARKETS['idx']`/`['set']` | True / True | confirmed |
| Hooks + `git diff --check` | clean | confirmed (only CRLF warnings) |

**Blockers / failures:** none.

**Notes:**

- The wrapper's default-mode path now reports "0 days since last IDX/SET refresh" because the forced run populated `last_fundamental_update` via the upsert's `ON CONFLICT DO UPDATE` branch. Future calls will return non-zero exits only if the seeder itself fails; otherwise the scheduler exits 0 either by skipping or by completing.
- Inline PowerShell `-c "..."` with `%` wildcards inside a SQL string triggered PowerShell's globbing; the post-run count probe was routed through a one-line `_probe_counts.py` scratch file (deleted after use). Recording here so the next agent skips that detour.
- Pre-existing `SyntaxWarning` in `scripts/etl/ibkr/migrate_to_ib_async.py:139` is still emitted; explicitly out of scope per the prior closeouts.

## Next recommended step

The full IDX/SET enablement change set (Phase 0 -> Phase 5) is now review-ready. Recommended next move: **commit / review the change set**. Suggested commits, following the no-Claude-attribution policy:

- `refactor(providers): bulk yf.download path in OptimizedYFinanceProvider; retire stale rate-limit modules`
- `feat(hooks): import_safety guard for module-scope db.py SQL-runner calls`
- `feat(idx-set): enable Indonesia + Thailand markets (universe seeding, yahooquery cap-seed, thresholds, toggles, monthly refresh wrapper)`
- `docs(tasks): IDX/SET enablement plan + provider cleanup progress`

Optional side-cleanup (independent of the commit set):

- Mark the 35 delisted `.JK`/`.BK` tickers `INACTIVE` in the `tickers` table so the daily collector stops retrying them.
- Decide NVDR `-R.BK` filtering (Open Question #1). At the $450M SET threshold most NVDRs already fall below cap; defer or fold into the inactive-ticker pass.
- External Task Scheduler / cron entry that invokes `scripts/etl/yahooquery/schedule_monthly_idx_set_fundamentals.py` once a day. The wrapper's internal due rule keeps it cheap on non-due days while guaranteeing it fires on the 1st of each month or after a 25-day staleness.

## Notes for the next agent

- The worktree contains the full provider-cleanup change set plus a new `import_safety` hook. Nothing has been committed. Suggested commit shape (per Darshan's commit-message policy — no Claude attribution):
  - `refactor(providers): bulk yf.download path in OptimizedYFinanceProvider; retire stale rate-limit modules`
  - `feat(hooks): import_safety guard for module-scope db.py SQL-runner calls`
  - `chore(markets): re-gate IDX/SET to False until enablement plan passes`
  - `docs(tasks): add idx_set_enablement_plan.md`
- Keep `.claude/settings.local.json` out of any project commits unless explicitly requested.
- The pre-existing `SyntaxWarning` in `migrate_to_ib_async.py` is noise on every Python invocation — if you commit, you'll see it in CI output too. Trivial fix (raw-string the regex) but explicitly out of scope here.
- IDX/SET universe will still be skipped by the screener even with these toggles flipped back to `True` later, until `stock_fundamentals.market_cap_usd` is populated for `.JK` / `.BK` rows. The Phase 2 yahooquery script in the plan is the canonical fix.
