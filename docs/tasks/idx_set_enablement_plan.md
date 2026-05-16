# IDX / SET Enablement Plan

## Task

- Short task name: Enable Indonesia (IDX, `.JK`) and Thailand (SET, `.BK`) markets
- Owner / agent: TBD
- Date: 2026-05-09
- Status: Phase 0 / 1 / 2 / 3 / 4 / 5 DONE 2026-05-16. `MARKETS['idx']` and `MARKETS['set']` flipped to True; `yahooquery==2.4.1` pinned; monthly refresh wrapper landed; Telegram currency confirmed.

## Context

IDX and SET are the two `False` entries in `config/markets.py` that have no IBKR feed at all (per the master plan's data-source table) — they are yfinance-only by design. Until 2026-05-09 they were also blocked by `OptimizedYFinanceProvider`'s per-ticker `yf.Ticker(...)` loops, which would rate-limit on a ~700-ticker universe.

That blocker was removed in this session: `OptimizedYFinanceProvider.get_market_data` now issues a single `yf.download(...)` for OHLCV (see `data/providers.py` post-rewrite). The remaining blocker is `marketCap`. `yf.download` returns OHLCV only; `screening/screening_utils.py:60` hard-rejects on the USD market-cap floor; therefore IDX/SET tickers fail the screener even though their price data flows.

This plan resolves the marketCap gap so IDX and SET can be flipped to `True` in `MARKETS`.

## Decision summary (investigation 2026-05-09)

Three candidates were evaluated for bulk marketCap on IDX/SET:

| Source | Bulk marketCap? | IDX/SET coverage | Free? | Verdict |
|---|---|---|---|---|
| **FinanceDatabase** | N/A — categorical only (Large/Mid/…/Nano) | 575 IDX rows on JKT, 1,247 SET rows on SET, all in yfinance `.JK`/`.BK` format | Yes | Use for **universe seeding** only |
| **yahooquery** | Yes — `Ticker([…]).quotes` issues one HTTP call to Yahoo's `v7/finance/quote?symbols=…` returning marketCap | Same Yahoo backend as yfinance; covers `.JK` and `.BK` | Yes | Use for **bulk marketCap fetch** |
| **Polygon.io free tier** | No bulk reference endpoint at this tier; 5 calls/min cap | US-only on free tier; international is paid-only | 5/min | Not viable |

yahooquery's source (`yahooquery/base.py`) confirms two request paths: endpoints whose Yahoo URL takes plural `?symbols=A,B,C` issue one HTTP call; endpoints with singular `?symbol=X` loop. The `quotes` accessor uses the plural endpoint. quoteSummary modules (`summary_detail`, `asset_profile`) loop because the Yahoo endpoint itself only takes one symbol — that is a Yahoo limit, not a yahooquery one. For our use case (marketCap) the plural endpoint is sufficient.

## Goals

1. Bring IDX and SET to NSE-grade screening: cap-filtered universe, marketCap populated, full criteria pipeline functional.
2. No regression on the seven currently-active exchanges.
3. Honour the bulk-only YF policy from `DEVELOPMENT.md:149` — every Yahoo call must be bulk-shaped.

## Non-goals

- Don't rewrite `should_pass_screening` to accept categorical FD buckets unless Phase 0 / Phase 2 prove yahooquery insufficient.
- Don't migrate the residual per-ticker `yf.Ticker(...)` calls in `IBKRProvider` (`data/providers.py` ~357 / ~619). They are per-symbol fallbacks within a per-symbol IBKR path, not universe loops. Out of scope.
- Don't introduce a new fundamentals schema. Reuse `stock_fundamentals`; populate the columns yahooquery returns and leave the rest sparse (the table already tolerates this for exchanges without IBKR XML coverage).

## Phases

### Phase 0 — yahooquery viability check (read-only, ~30 min) — DONE 2026-05-16

**Result:** All three acceptance criteria passed on the 10-ticker probe.

| Criterion | Threshold | Actual |
|---|---|---|
| Wall time | <= 5 s | 0.91 s |
| marketCap populated | >= 8 / 10 | 10 / 10 |
| Currency | IDR for `.JK`, THB for `.BK` | Confirmed |

All 10 returned `quoteType=EQUITY`. The plural `?symbols=…` endpoint is observably one HTTP call. `yahooquery 2.4.1` installed locally into `.venv`; **not** pinned in `requirements.txt` (defer to Phase 4 pass per plan).

Raw output for the record:

```
wall: 0.91s  rows: 10
AALI.JK   14627632054272  IDR  EQUITY
ABBA.JK     161371602944  IDR  EQUITY
ADRO.JK   72577246560256  IDR  EQUITY
BBCA.JK  749545076031488  IDR  EQUITY
TLKM.JK  293197687291904  IDR  EQUITY
A.BK         4605999616  THB  EQUITY
AAV.BK      13492499456  THB  EQUITY
AOT.BK     757142126592  THB  EQUITY
CPALL.BK   412138405888  THB  EQUITY
PTT.BK    1026757165056  THB  EQUITY
```

Phase 1 (FD-driven `tickers` seeding in `screener/universe.py`) is unblocked.

---

#### Original Phase 0 procedure (kept for reproducibility)

```powershell
.\.venv\Scripts\python.exe -m pip install yahooquery
.\.venv\Scripts\python.exe -c "
from yahooquery import Ticker
import time
sample = ['AALI.JK', 'ABBA.JK', 'ADRO.JK', 'BBCA.JK', 'TLKM.JK',
          'A.BK', 'AAV.BK', 'AOT.BK', 'CPALL.BK', 'PTT.BK']
t0 = time.time()
q = Ticker(sample, asynchronous=False).quotes
print(f'wall: {time.time()-t0:.2f}s  rows: {len(q)}')
for sym, row in q.items():
    print(sym, row.get('marketCap'), row.get('currency'), row.get('quoteType'))
"
```

Acceptance:

- Wall time ≤ 5 s for 10 tickers (one HTTP call).
- `marketCap` populated for ≥ 8 of 10.
- `currency` is `IDR` for `.JK` rows, `THB` for `.BK` rows.

If marketCap is missing for too many or the call still loops, halt and escalate before Phase 1. Do not pin yahooquery in `requirements.txt` yet — local-only install until Phase 4 passes (mirrors the Spark plan's "promote after correctness" rule).

### Phase 1 — Seed `tickers` from FinanceDatabase — DONE 2026-05-16

**Result:** Counts match the plan exactly.

| Exchange | FD raw | After Large+Mid+Small filter | Expected |
|---|---:|---:|---:|
| IDX | 575 | **149** | 149 |
| SET | 1,247 | **325** | 325 |

Combined IDX/SET seed: 474 tickers. DB verification:

```
[('IDX', 149), ('SET', 325)]
```

Implementation (`screener/universe.py`):

- Added `IDX` and `SET` to `CAP_FILTERED_EXCHANGES`.
- Added `FD_COUNTRY_FILTER = {'IDX': 'Indonesia', 'SET': 'Thailand'}`. When `db_key` appears here, FD search uses `equities.search(country=..., exchange=fd_key)` — required because `country='Indonesia'` alone matches Indonesian cross-listings on FRA / STU. Other exchanges keep exchange-only search unchanged.
- `MARKETS['idx']` and `MARKETS['set']` deliberately left `False`. The acceptance check used a temporary in-process override (`{**MARKETS, 'idx': True, 'set': True}`); the runtime config was never modified.

**NVDR (`-R.BK`) handling:** intentionally not filtered in Phase 1. Filtering at seed time would cut SET from 325 to 194, breaking the expected count and pre-empting the explicit decision in Open Question #1. Deferred to a future explicit decision after Phase 2 marketCap data shows whether NVDR rows duplicate their underlyings in `stock_fundamentals`.

#### Acceptance commands (for reproducibility)

In `screener/universe.py`:

1. Add `'idx'` and `'set'` to the FD-backed exchange table the same way SEHK/LSE/etc. were added in Task 12.
2. Add IDX / SET to `CAP_FILTERED_EXCHANGES` so the Large+Mid+Small filter applies (see Universe Criterion memory).
3. FD lookup: `country='Indonesia' AND exchange='JKT'` and `country='Thailand' AND exchange='SET'`. The `country` field alone matches European cross-listings (FRA/STU) — must AND with `exchange`.

Run after edit:

```powershell
.\.venv\Scripts\python.exe -c "
from screener.universe import get_universe
from config import MARKETS
m = {**MARKETS, 'idx': True, 'set': True}
universe = get_universe(m)
print(f'total: {len(universe)}')
"
```

Expected per-exchange counts (from FD as of 2026-05-09):

| Exchange | Cap-filtered (Large+Mid+Small) |
|---|---:|
| IDX | 149 |
| SET | 325 |

Optional filter: SET carries `-R` suffix variants (NVDR, e.g. `A-R.BK` alongside `A.BK`). They are non-voting depositary receipts of the same underlying — likely duplicates. Filter `re.compile(r'-R\.BK$')` at seed time. Confirm with a sample before deciding.

`MARKETS['idx']` and `MARKETS['set']` stay `False` after this phase — the `tickers` table seed is independent of the runtime toggle.

### Phase 2 — Bulk fundamentals seed via yahooquery — DONE 2026-05-16

**Schema correction:** the live `stock_fundamentals` column is **`mkt_cap_usd`** (see `sql/schema/stock_fundamentals.sql:14`). `data/cache_manager.py:81` aliases that column to the Python key `market_cap_usd` for downstream consumers — that alias is why earlier sections of this plan said "market_cap_usd". The SQL writes the underlying column name `mkt_cap_usd`.

**Result:** Coverage exceeds the >= 80% acceptance threshold on both exchanges and runtime is ~12x under budget.

| Exchange | with_mcap | total seeded | coverage | threshold |
|---|---:|---:|---:|---|
| IDX | 145 | 149 | 97.3% | >= 120 of 149 |
| SET | 293 | 325 | 90.2% | >= 260 of 325 |

Combined IDX/SET upsert: 438 rows. Skipped 36 (currency mismatch, missing marketCap, or non-EQUITY quoteType). Wall time: 2.64 s (single 474-symbol HTTP call to Yahoo's plural `?symbols=` endpoint took 1.31 s of that; FX rate calls memoised once per currency).

DB verification:

```
[('IDX', 145, 145), ('SET', 293, 293)]
```

All 438 rows have positive `mkt_cap_usd` (the `with_mcap` count equals the total).

#### Files added

- `scripts/etl/yahooquery/seed_idx_set_fundamentals.py` — bulk seeder. Reads `db.get_actionable_tickers('IDX' / 'SET')`, chunks at 500 (single chunk in practice), filters by `quoteType=='EQUITY'`, `marketCap>0`, and currency-suffix match, normalises via `data.currency.usd_market_cap`, and calls `db.execute_values_file('etl/stock_fundamentals_yq_upsert.sql', rows)`. ASCII-only output; `if __name__ == "__main__":` guard; no module-scope side effects (verified by both the import-safety hook and `import scripts.etl.yahooquery.seed_idx_set_fundamentals` succeeding without DB / network activity).
- `sql/etl/stock_fundamentals_yq_upsert.sql` — sparse UPSERT writing exactly six columns: `ticker, company_name, mkt_cap_usd, price_currency, exchange_code, exchange_country`. `last_fundamental_update` is set to `CURRENT_TIMESTAMP` only in the `ON CONFLICT DO UPDATE SET` clause (matches the `stock_fundamentals_fd_upsert.sql` pattern; first insert leaves the column NULL).

#### FX-rate caching

`data.currency.get_live_fx_rate` hits a public FX API per call. Calling `usd_market_cap` 438 times would have been 438 HTTP requests. The script memoises `currency_mod.get_live_fx_rate` via `functools.lru_cache(maxsize=8)` at script scope so each unique currency (IDR, THB) costs one FX call total. `usd_market_cap` continues to be the single conversion entry point — the cache wraps its dependency, not its caller.

#### NVDR (`-R.BK`) still unfiltered

`-R.BK` rows were upserted alongside their underlyings. The decision deferred from Phase 1 is now decidable from data, but explicitly left for a separate pass (Open Question #1) since Phase 3's min-cap derivation can proceed regardless and may inform the call.

---

#### Original Phase 2 spec (kept for reference)

New script: `scripts/etl/yahooquery/seed_idx_set_fundamentals.py`.

```python
# Pseudocode for the structure; production code under if __name__ == "__main__":
def seed():
    db = get_db()
    tickers = db.query(
        "SELECT ticker FROM tickers WHERE market IN ('idx','set') AND (status='ACTIVE' OR status IS NULL)"
    )
    syms = [r[0] for r in tickers]
    # Yahoo v7 quote endpoint URL caps at ~1000 symbols; chunk for safety.
    rows = []
    for chunk in chunked(syms, 500):
        q = Ticker(chunk, asynchronous=False).quotes
        rows.extend((s, r.get('marketCap'), r.get('currency'), r.get('quoteType'))
                    for s, r in q.items() if r.get('marketCap'))
    # Write to stock_fundamentals (sparse columns: ticker, market_cap_usd, currency, …)
    # Use db.execute_values_file('etl/stock_fundamentals_yq_upsert.sql', rows)
```

Conventions to honour:

- `if __name__ == "__main__":` guard (enforced by `scripts/hooks/import_safety.py`).
- Externalised SQL under `sql/etl/` (enforced by `scripts/hooks/sql_guard.py`).
- ASCII-only output (Windows codepage 1252 — see DEVELOPMENT.md and the `screener/universe.py:79` masking-bug fix in commit `9ea60c7`).
- Currency conversion: yahooquery returns marketCap in **local currency** (IDR / THB). Use `data/currency.usd_market_cap()` to normalise to USD before writing. The currency-conversion path already exists for the IBKR provider — do not duplicate.

Acceptance:

- ≥ 80% of cap-filtered IDX tickers and ≥ 80% of cap-filtered SET tickers have non-NULL `mkt_cap_usd` after the run. (Note: the SQL column is `mkt_cap_usd`; `data/cache_manager.py:81` exposes it to Python as `market_cap_usd` — same data, different name.)
- Run completes in < 30 s wall time (≤ 2 chunked HTTP calls).
- Per-exchange count via:
  ```sql
  SELECT
    CASE WHEN ticker LIKE '%.JK' THEN 'IDX'
         WHEN ticker LIKE '%.BK' THEN 'SET' END AS exch,
    COUNT(*) FILTER (WHERE mkt_cap_usd > 0) AS with_mcap,
    COUNT(*) AS total
  FROM stock_fundamentals
  WHERE ticker LIKE '%.JK' OR ticker LIKE '%.BK'
  GROUP BY 1;
  ```

### Phase 3 — Wire screener thresholds — DONE 2026-05-16

**Thresholds pinned in `config/markets.py` MARKET_REGISTRY:**

| Exchange | threshold_usd | Universe at threshold | Retain |
|---|---:|---:|---:|
| IDX | **600,000,000** | 87 / 145 | 60.0% |
| SET | **450,000,000** | 176 / 293 | 60.1% |

Each pin retains ~60% of the cap-filtered universe with positive `mkt_cap_usd`, the target band identified in the plan. The EMERGING `$150M` default was too aggressive for these weak-currency markets — it would have admitted ~83% of IDX and ~76% of SET, defeating the "Large+Mid+Small" filtering work in Phase 1.

**Distribution that drove the choice** (probed against `stock_fundamentals` after Phase 2):

| Exchange | p25 | p40 | p50 | p75 | p90 | min | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| IDX | ~289M | ~606M | ~788M | ~1.86B | ~4.69B | ~6.0M | ~42.7B |
| SET | ~242M | ~453M | ~578M | ~1.35B | ~4.40B | ~6.5M | ~121.8B |

The IDX pin sits between p40 and p50; the SET pin lands right at p40. Both pins are round numbers chosen to roughly match the universe-retention target — not statistically anchored thresholds.

**Mapping check:** `screening/screening_utils.py:52` already maps `.JK -> IDX` and `.BK -> SET` in `exchange_map`, so `get_min_market_cap()` already routes correctly. No edit needed there.

**Untouched:** other exchanges' thresholds (`NSE 150M`, `ASX 500M`, `SEHK 500M`, …) and `MARKETS['idx']` / `MARKETS['set']` (both remain `False`).

---

#### Original Phase 3 spec (kept for reference)

`screening/screening_utils.py:52` already maps `.JK → IDX` and `.BK → SET` — re-verify post-Phase-2 instead of editing.

`config/markets.py:get_min_market_cap('IDX')` and `get_min_market_cap('SET')` need sane values. Confirm before flipping markets:

- IDR/THB are weak currencies; a $1B+ floor likely cuts most of the universe. Recommend $50M–$200M as a starting floor for IDX/SET specifically. Do not adopt the SMA / NSE thresholds wholesale.
- Source the threshold by sampling the seeded `mkt_cap_usd` distribution from Phase 2 (SQL column name; Python alias is `market_cap_usd`); pin a value that retains the top ~60% of the cap-filtered universe.

### Phase 4 — End-to-end smoke — DONE 2026-05-16

**Result:** Both IDX and SET smokes passed cleanly with `DATA_SOURCE=yfinance`. `MARKETS['idx']` and `MARKETS['set']` flipped to `True`.

#### Backfill

`scripts/etl/yfinance/collect_historical_yfinance.py --exchange IDX,SET --period 2y` ran in **39.4s** and inserted **208,781 rows** into `prices_daily`:

| Suffix | rows in prices_daily | distinct tickers |
|---|---:|---:|
| .JK | 69,797 | 146 (of 149 seeded) |
| .BK | 138,984 | 293 (of 325 seeded) |

35 tickers failed (3 IDX delisted: RMBA, FREN, TURI; 32 SET delisted or NVDR variants not on Yahoo — mostly `-R.BK` along with a few primary listings like STARK, ESSO, TMB, MAKRO).

#### IDX smoke

```powershell
$env:DATA_SOURCE='yfinance'
.\.venv\Scripts\python.exe main.py --exchanges IDX --mode test --skip-collection --skip-flattening
```

- Exit code: **0**
- `Loaded 149 actionable IDX tickers from DB.` (matches Phase 1 count)
- Provider chain: `Falling back to Optimized Scan (yfinance with caching)... Optimized YFinance: bulk download for 149 stocks` (single bulk `yf.download`, not per-ticker)
- `Optimized YFinance: 0 catches from 149 tickers`
- Reached `DAILY PIPELINE COMPLETE`
- 3 failed downloads (RMBA / FREN / TURI delisted) — same names as backfill, not rate-limit symptoms.

#### SET smoke

```powershell
$env:DATA_SOURCE='yfinance'
.\.venv\Scripts\python.exe main.py --exchanges SET --mode test --skip-collection --skip-flattening
```

- Exit code: **0**
- `Loaded 325 actionable SET tickers from DB.` (matches Phase 1 count)
- Provider chain: bulk yfinance download for 325 stocks (single call)
- `Optimized YFinance: 0 catches from 325 tickers`
- Reached `DAILY PIPELINE COMPLETE`
- 32 failed downloads (same delisted/NVDR cohort as backfill)

#### Catches

**Zero** in both runs. Acceptable per the smoke criteria — confirms the pipeline reaches completion cleanly without rate-limit warnings or per-ticker loop fan-out. Real near-low setups absent today.

#### Toggles flipped

`config/markets.py` `MARKETS['idx']` and `MARKETS['set']`: `False -> True`. Verified post-edit: `from config import MARKETS` returns `True True`.

#### Scheduler check

`scheduler/market_scheduler.py` already maps both markets to the `emerging_asia` region (`market_scheduler.py:34-35`), which has an existing `Asia/Bangkok` scan window of 10:30 - 16:30 (`market_scheduler.py:61-65`). The emerging_asia region appears in the active-regions list at `:328`. No edit needed; scheduler dispatch for IDX/SET works out of the box once `MARKETS['idx']` / `MARKETS['set']` are `True`.

#### Hooks and diff

```text
.\.venv\Scripts\python.exe scripts\hooks\import_safety.py   # exit 0
.\.venv\Scripts\python.exe scripts\hooks\sql_guard.py       # exit 0
git diff --check                                            # clean (CRLF warnings only)
```

---

#### Original Phase 4 spec (kept for reference)

Run during Asian market hours (UTC+7 / +8). Pre-condition: `current_market_data` must be fresh; the daily YF collector must have run for `.JK`/`.BK` since `--exchanges` was last toggled.

```powershell
.\.venv\Scripts\python.exe main.py --exchanges IDX --mode test
.\.venv\Scripts\python.exe main.py --exchanges SET --mode test
```

Acceptance:

- Pipeline reaches `🎉 DAILY PIPELINE COMPLETE` for both runs.
- `Loaded N actionable IDX/SET tickers from DB` matches Phase 1 counts ± `-R` filter.
- Catches > 0 only if real near-low setups exist; 0 catches with clean exit is also a pass.
- No yfinance rate-limit warnings in the log.

If smoke passes, flip `MARKETS['idx']=True` and `MARKETS['set']=True`. If only one of the two passes, flip just that one — the markets are independent.

### Phase 5 — Promote and schedule — DONE 2026-05-16

**Result:** all four promotion items landed cleanly.

| Item | Outcome |
|---|---|
| `yahooquery` pinned | `requirements.txt` — `yahooquery==2.4.1` under "Financial Data APIs" |
| Monthly refresh wrapper | `scripts/etl/yahooquery/schedule_monthly_idx_set_fundamentals.py` (new) |
| Forced refresh | 438 rows upserted; IDX 145/145 + SET 293/293 retained; `last_fundamental_update` set |
| Telegram currency | `.JK -> Rp ` and `.BK -> ฿` already wired at `alerts/telegram.py:22-23` — no edit needed |

#### Monthly wrapper behaviour

- ASCII-only output; `if __name__ == "__main__":` guard; no DB / subprocess side effects on import (verified via import-safety hook + plain `import` smoke).
- `--dry-run`: prints the command and cwd; exits 0 without calling the seeder.
- `--run`: bypasses the due rule; invokes the seeder via `sys.executable` with `cwd=REPO_ROOT`.
- Default (no flag): runs only when due. Due rule = 1st of month OR latest `stock_fundamentals.last_fundamental_update` for `.JK`/`.BK` rows is NULL or older than 25 days. Last-update lookup uses `db.py/get_db()` (no raw `psycopg2`).
- Exit codes: 0 when not due; 0 when due/forced run succeeds; nonzero if the seeder subprocess returns nonzero.
- NULL last_update is treated as due (Phase 2's upsert only sets `last_fundamental_update` on conflict, so first-insert rows leave it NULL — that's a documented seam, not a bug).

#### Verification commands (all 2026-05-16)

```text
.\.venv\Scripts\python.exe -c "import scripts.etl.yahooquery.schedule_monthly_idx_set_fundamentals as s; print('import ok')"
# Output: import ok

.\.venv\Scripts\python.exe scripts\etl\yahooquery\schedule_monthly_idx_set_fundamentals.py --dry-run
# Output: Should run: True / Reason: No previous IDX/SET fundamental update found (NULL) / [dry-run] Would execute ...

.\.venv\Scripts\python.exe scripts\etl\yahooquery\schedule_monthly_idx_set_fundamentals.py --run
# Output: Forced run; seeder reported "Loaded 474 ... Upserted 438 rows"; "[ok] Seeder completed successfully."

# Default mode after the forced run, to confirm the due-rule path
.\.venv\Scripts\python.exe scripts\etl\yahooquery\schedule_monthly_idx_set_fundamentals.py
# Output: Last IDX/SET update: 2026-05-16 16:16:22.630909 / Should run: False / [skip] Not due. Use --run to force.

# Post-run fundamentals probe
[('IDX', 145, 145, 2026-05-16 16:16:22), ('SET', 293, 293, 2026-05-16 16:16:22)]

# Final checks
.\.venv\Scripts\python.exe -c "from config import MARKETS; print(MARKETS['idx'], MARKETS['set'])"   # True True
.\.venv\Scripts\python.exe scripts\hooks\import_safety.py   # exit 0
.\.venv\Scripts\python.exe scripts\hooks\sql_guard.py       # exit 0
git diff --check                                            # clean (CRLF warnings only)
```

#### Files added / changed

- `requirements.txt` — added `yahooquery==2.4.1`.
- `scripts/etl/yahooquery/schedule_monthly_idx_set_fundamentals.py` — new monthly wrapper.
- `docs/tasks/idx_set_enablement_plan.md` — this section + status header.
- `docs/tasks/provider_cleanup_progress.md` — Phase 5 closeout appended.
- `alerts/telegram.py` — **not modified**; pre-existing mappings already cover IDX/SET.
- `scheduler/market_scheduler.py` — **not modified**; refresh is invoked via the standalone wrapper, not a scheduler-internal cron. Task brief instructs not to touch scheduler unless there is a real runtime gap.

#### Behaviour not covered in this pass

- The new wrapper has to be invoked externally (Windows Task Scheduler, cron, or an upstream orchestrator). It does not register itself with `scheduler/market_scheduler.py`.
- NVDR `-R.BK` filtering still deferred; at the $450M SET threshold the urgency is low.
- 35 delisted `.JK`/`.BK` tickers still marked ACTIVE. Side-cleanup candidate; not run this pass per the Phase 5 brief.

---

#### Original Phase 5 spec (kept for reference)

- `requirements.txt`: add `yahooquery` with a tested version pin.
- Scheduling: marketCap drifts on the order of weeks for these caps. Add a monthly run of `seed_idx_set_fundamentals.py` to `scheduler/market_scheduler.py` or its successor. Do not run daily — that wastes Yahoo's quota on near-static data.
- Telegram alert path: confirm the `.JK`/`.BK` exchange currency symbols (`Rp`, `฿`) render correctly in `alerts/telegram.py` (Task 7 wired exchange-aware currency for the IBKR-free seven; IDX/SET were not exercised).
- Daily YF OHLCV collector (`scripts/etl/yfinance/collect_daily_yfinance.py`) already iterates the `tickers` table and uses bulk `yf.download` — no change needed; the seed from Phase 1 unblocks it automatically once `MARKETS['idx']`/`MARKETS['set']` are `True`.

## Open questions

1. **NVDR (`-R.BK`) handling.** Filter at seed time, or keep both and de-duplicate at screening time? Recommend filter at seed time — fewer downstream surprises.
2. **FD bucket fallback.** If yahooquery returns NULL marketCap for some tickers, do we fall back to the FD bucket (Large/Mid/Small) translated to a synthetic USD threshold, or skip the ticker? Recommend skip on first pass; revisit if Phase 2 yields < 80% coverage.
3. **Schema.** Reuse `stock_fundamentals` (sparse) or add `stock_fundamentals_yq`? Recommend reuse — same pattern as IBKR-light exchanges. Add a new column only if a yahooquery field is needed that the schema lacks.
4. **Min-cap floor for IDX/SET.** Pin at Phase 3 from the actual distribution, not from the SMA default. The plan deliberately does not name a number.
5. **Trading-hour scheduling.** IDX is UTC+7 (open 02:00–09:00 UTC); SET is UTC+7 (open 03:00–09:30 UTC). The scanner's existing per-market schedule entries (`scheduler/market_scheduler.py`) need new rows. Confirm before Phase 4 smoke.

## Risks

1. **yahooquery is a Yahoo wrapper.** Same backend as yfinance; same risk class. Yahoo can change endpoints unannounced. Mitigation: pin version; keep the bulk path narrow (only `.quotes`); accept that this is fallback-quality data.
2. **FD `country='Indonesia'` includes European depositary receipts.** Already mitigated in Phase 1 by `AND exchange IN ('JKT','SET')`. Double-check the `screener/universe.py` filter actually applies the AND, not OR.
3. **NVDR double-counting.** If `-R.BK` ticker variants are kept, market scanning will double-count Thai names. Treat the seed-time filter (Phase 1) as load-bearing.
4. **Currency conversion for IDR / THB.** `data/currency.py` must have current FX rates for both. Confirm before Phase 2.
5. **The 5 IDR-billion-cap edge case.** A "Large Cap" Indonesian stock at IDR 5T ≈ USD 320M — well below typical SMA thresholds. The min-cap floor in Phase 3 must be *exchange-specific*, not the global default, or the entire IDX universe gets rejected.

## References

- `data/providers.py:OptimizedYFinanceProvider` — bulk `yf.download` path (rewritten 2026-05-09)
- `screener/universe.py` — FD-driven seeding pattern (Task 12 / Task 12.5)
- `config/markets.py` — `MARKETS`, `MARKET_REGISTRY`, `CAP_FILTERED_EXCHANGES`, `get_min_market_cap`
- `scripts/etl/yfinance/collect_daily_yfinance.py` — bulk OHLCV ETL (the daily collector this plan unblocks)
- `scripts/hooks/import_safety.py` + `scripts/hooks/sql_guard.py` — guards Phase 2 must satisfy
- `DEVELOPMENT.md` — bulk YF policy (`#149`), import-safety rule (`#120`), SQL externalisation (`#99`)
- yahooquery source: `yahooquery/base.py` — verified 2026-05-09 that `?symbols=…` plural endpoint is bulk
- FinanceDatabase 2.3.1 — verified 2026-05-09 that JKT/SET-listed rows carry `.JK`/`.BK` identifiers and Large+Mid+Small bucket counts of 149 / 325

## Next recommended step

All five phases are DONE (2026-05-16). `MARKETS['idx']` and `MARKETS['set']` are `True`; `yahooquery==2.4.1` is pinned; the monthly refresh wrapper is wired and verified end-to-end (NULL-due, forced --run, then default-not-due). Telegram currency support for `.JK`/`.BK` is confirmed pre-existing.

The next recommended step is to **commit / review the completed IDX/SET enablement change set**. Suggested commit shape (per the no-Claude-attribution policy):

- `feat(idx-set): enable Indonesia (IDX) and Thailand (SET) markets via yahooquery fundamentals`
  - Bundles: `screener/universe.py` FD-seeding, `config/markets.py` thresholds + toggles, the yahooquery seeder + SQL, the monthly wrapper, the `requirements.txt` pin.
- `docs(tasks): IDX/SET enablement plan + provider cleanup progress`

Optional side-cleanup (independent of Phase 5):

- Mark the 35 delisted `.JK`/`.BK` tickers `INACTIVE` in the `tickers` table so the daily collector stops retrying them on each run.
- Decide NVDR `-R.BK` filtering (Open Question #1). At the $450M SET threshold most NVDRs already fall below cap, so the urgency is much lower than it was at $150M; defer or fold into the inactive-ticker pass.
- External cron / Task Scheduler entry that invokes `scripts/etl/yahooquery/schedule_monthly_idx_set_fundamentals.py` once a day. The wrapper's internal due rule keeps it cheap on non-due days; this just guarantees it fires on the 1st of each month / after a 25-day staleness.

---

#### Original Next-step (kept for reference) Pre-conditions:

- Run during Asian market hours (UTC+7 / UTC+8) so `current_market_data` is fresh.
- The daily YF OHLCV collector must have run for `.JK` and `.BK` since the markets were last toggled. Since `MARKETS['idx']` / `MARKETS['set']` are still `False`, this requires either (a) temporarily flipping the toggle and letting the daily collector backfill, or (b) running `scripts/etl/yfinance/collect_historical_yfinance.py --exchange IDX,SET` once to seed `prices_daily` for the 474 tickers.
- Add scheduler entries to `scheduler/market_scheduler.py` for IDX/SET trading hours (IDX 02:00-09:00 UTC, SET 03:00-09:30 UTC) before flipping toggles in production.

Smoke commands:

```powershell
.\.venv\Scripts\python.exe main.py --exchanges IDX --mode test
.\.venv\Scripts\python.exe main.py --exchanges SET --mode test
```

Acceptance: pipeline reaches `DAILY PIPELINE COMPLETE` for both; `Loaded N actionable IDX/SET tickers from DB` matches Phase 1 counts (149 / 325); no yfinance rate-limit warnings in the log; catches > 0 only if real near-low setups exist (0 catches with clean exit is also a pass).

If smoke passes, flip `MARKETS['idx']` / `MARKETS['set']` to `True` (independently — they can ship one at a time). Then Phase 5 (pin `yahooquery` in `requirements.txt`, schedule monthly cap refresh, confirm `.JK` / `.BK` currency symbols render in `alerts/telegram.py`).

Still deferred: NVDR `-R.BK` filtering decision. Open Question #1 is now decidable from data — Phase 3's 60% cut already drops most low-cap NVDRs, so the universe-quality impact is smaller than it would have been at the prior `$150M` floor.
