# Task 11 — Multi-exchange IBKR fundamentals round-trip — 2026-04-27

## TL;DR

✅ **DONE.** `stock_fundamentals` is now multi-exchange — **1,844 rows across 7 IBKR-free exchanges** (was 398 NSE-only at start of session). Both worker scripts are exchange-parameterized; no NSE hardcodes remain.

| Exchange | Final rows | Seed | Collected | Flatten errors |
|---|---|---|---|---|
| SEHK | 597 | 664 | 612 | 15 (empty XML) |
| NSE | 408 | 612 (fd_capfilter) | 408 | 0 |
| ASX | 327 | 498 | 359 | 32 |
| LSE | 241 | 1,326 | 242 | 1 |
| SGX | 124 | 172 | 133 | 9 |
| TADAWUL | 96 | 103 | 99 | 3 |
| JSE | 51 | 81 | 51 | 0 |
| **Total** | **1,844** | | | |

NSE end-to-end re-validated during market hours: `main.py --exchanges NSE --mode test` exit 0, 388 fresh market data, 950 actionable tickers screened, 0 catches.

## Plan vs reality

The plan (`~/.claude/plans/vast-greeting-brooks.md`) was mostly right but two of its assumptions cost time. Both were structural and worth recording.

### 1. The in-tree `flatten_ibkr_final.py` was a stub, not the canonical flatten

**Plan said:** "Switch from `raw_ibkr_nse` → `ibkr_fundamentals`. (One-line fix — same column shape.)"

**Reality:** The in-tree `flatten_ibkr_final.py` had a 41-column schema. The live `stock_fundamentals` table has ~80 columns (`industry_trbc`, `org_perm_id`, `isin`, `ric`, `exchange_country`, splits, shares_out, address, 5 named officer slots, `price_currency` vs `currency`, etc.). The 398 existing rows had richer data than the in-tree script could ever have produced. First JSE flatten attempt errored with `column "sector" of relation "stock_fundamentals" does not exist`.

**Recovery:** The canonical flatten was `flatten_ibkr_mega.py` (331 lines), deleted in commit `b55b8de` (2026-03-03 cleanup). I recovered it via `git show b55b8de^:…/flatten_ibkr_mega.py`, then adapted it with the planned Step 2 changes (multi-exchange, UPSERT, per-row rollback). The recovered version produced the 398 NSE rows — it's the right base. Now lives at `scripts/etl/ibkr/flatten_ibkr_final.py` (commit `bc0af26`).

### 2. The LSE `trailing_period` rule was wrong

**Plan said (implicit):** "Reuses existing `normalise_ibkr_symbol()` from `config/markets.py:65` — no new logic needed there."

**Reality:** The first LSE collect collapsed to 9/1326 (0.7%). The 9 successes were all 2-letter symbols (AV, BA, BP, JD, NG, QQ, SN, TW, UU). 3+ letter symbols (HSBA, GSK, AZN, RIO, ULVR, BARC, LLOY, DGE, VOD) all failed contract qualification.

**Diagnosis:** Probed IBKR directly with `Stock(sym, 'LSE', 'GBP')` qualifyContractsAsync, both with and without trailing period. IBKR's LSE catalog only carries the period for the historical 2-character common-stock convention; 3+ char symbols are listed without it. The blanket rule was over-applying.

**Fix (commit `6b56730`):** Made the rule conditional on `len(symbol) <= 2`. Re-running LSE lifted collect to 233/1317. The remaining ~1k LSE failures are the FD `0A*` historical security IDs IBKR doesn't carry — separate data-hygiene problem, candidate for a regex filter at FD seed time.

## Run order (actually executed)

Pivoted from the plan's "smallest first" order partway through — once the pipeline was validated on JSE+TADAWUL+SGX, the user asked for the full run with NSE specifically completing during market hours.

| Order | Exchange | When | Notes |
|---|---|---|---|
| 1 | JSE | smoke 2/2 → full 49/79 | First validation; surfaced the flatten-stub problem |
| 2 | TADAWUL | 99/103 | First clean post-flatten-fix run |
| 3 | SGX | 133/172 | |
| 4 | NSE re-seed | 408/612 | Pulled forward to land during NSE market hours |
| 5 | SEHK | 612/664 | strip_leading_zeros normalisation worked first try |
| 6 | ASX | 359/498 | Market closed during run, but fundamentals don't need market hours |
| 7 | LSE v1 | 9/1326 | Collapsed — surfaced the trailing-period bug |
| 8 | LSE v2 | 233/1317 | Post-fix; only retried the v1 failures (resume filter skipped the 9 fresh) |

Per-ticker IBKR round-trip averaged ~3–7 seconds (depends on success/failure mix; failures are faster).

## Validation

`main.py --exchanges NSE --mode test` ran during NSE market hours immediately after the NSE flatten:

- Step 1 (IBKR market data): 388 new records → `current_market_data` (now 923 total)
- Step 2 (flatten): green
- Step 3 (freshness): pass — "Current market data: 923 records; AGE: 6.0 hours old"
- Step 4 (screen): 950 actionable NSE tickers, 0 catches (consistent with prior bull-market result)
- Exit 0

## Open items

1. **LSE `0A*` filter.** ~1k FD-seeded LSE entries are historical security IDs IBKR doesn't carry. A regex filter (`^0[A-Z0-9]+\.L$`) at FD seed time in `screener/universe.py` would shrink the LSE seed to ~330 tickers and lift the collect success rate dramatically. Low priority — current `stock_fundamentals` already has the IBKR-listable ones.
2. **NSE re-seed wiped manual renames.** `--replace` on the NSE flatten reverted yesterday's manual hygiene fixes (AKZOINDIA→JSWDULUX, INFIBEAM→CCAVENUE) since the raw `ibkr_fundamentals` table still has the old symbols. Re-apply manually if desired, or fix at the FD-seed level so renames flow through naturally.
3. **Empty `{}` XMLs.** A handful of tickers per exchange (TADAWUL 3, SGX 9, SEHK 15, etc.) qualify in IBKR but the fundamentals snapshot returns `{}`. Collector marks them success, flatten correctly errors and skips. Could tighten the collector's success criterion to require non-empty XML.
4. **Other exchange e2e validation.** Only NSE was re-validated end-to-end (it was the only exchange in market hours when we got there). SEHK / LSE / SGX / ASX / TADAWUL / JSE main.py-test runs are deferred — should each pass by construction now that `stock_fundamentals` has rows for them, but worth confirming during their respective market hours.

## Commits

- `bc0af26` — Task 11 — multi-exchange IBKR fundamentals collect+flatten
- `6b56730` — fix(LSE): trailing-period rule applies only to 2-char codes

## Logs

`logs/task11_*_collect_20260427.log` — one per exchange, plus `task11_lse_collect_v2_20260427.log` for the post-fix LSE re-run.
