# NSE end-to-end test — progress & results (2026-04-24)

## TL;DR

- ✅ **NSE e2e pipeline ran cleanly end-to-end** (`main.py --exchanges NSE --mode test`). All four steps green. Exit code 0.
- ✅ Root cause of the initial failure — the daily IBKR collector was reading the wrong universe table — **fixed** by a one-line SQL change.
- 📌 **3 stale symbols in the curated 398**: INFIBEAM, AKZOINDIA, SEQUENT — IBKR can't resolve them. Data-hygiene fix needed, details below.
- 🔵 No retry needed. 0 catches in this morning's screen is a legitimate market result.
- ⏳ ASX/SGX parked as TODO (see `Open items for tomorrow`).

## Timeline

| Time (UTC) | Event |
|---|---|
| 03:49 | Session started — NSE ~34 min past open (IST 09:19). Kicked off first `main.py --exchanges NSE --mode test` run. |
| ~03:55 | Observed systemic Error 200 "no security definition" on almost every contract. Stopped run and investigated. |
| 04:10 | Root-caused the problem. Planned a one-line SQL fix. |
| 04:15 | Second run kicked off after fix. Ran cleanly for ~150 reqIds. Then IBKR server-side pushed Error 1100 (TWS↔IBKR servers connectivity lost). All subsequent qualifications failed because contract lookup needs server-side access. Run finished at 77 success / 321 fail. Stopped. |
| 04:25 | User reconnected TWS and handed session over for autonomous operation. |
| 04:28 | Run 3 kicked off. |
| ~04:35 | Run 3 green end-to-end: 395/398 collected, flattened, freshness-passed, screened, 0 catches. Pipeline exit 0. |

## The fix

`scripts/etl/ibkr/collect_daily_ibkr_market_data.py:67-71` — changed universe source from `stock_fundamentals_fd` to `stock_fundamentals`.

Before:
```sql
SELECT ticker FROM stock_fundamentals_fd
WHERE market_cap_category IN ('Large Cap','Mid Cap','Small Cap')
ORDER BY ticker
```

After:
```sql
SELECT ticker FROM stock_fundamentals
ORDER BY ticker
```

## Why the fix is right

`stock_fundamentals_fd` is the **input** to fundamentals collection (raw FD seed, 1,921 NSE rows). `stock_fundamentals` is the **output** — the 398 names that survived IBKR qualification and now have fundamentals. The daily market-data collector should obviously be using the IBKR-verified output set; it was drifting from that intent because `stock_fundamentals_fd` got re-seeded by Task 12 (2026-04-22) and suddenly contained lots of names IBKR doesn't recognise under the stored symbol. The fix realigns the collector with the architectural intent already documented at `screener/universe.py:12-14`.

## Why this was fine "a month or two ago"

The collector has read from `stock_fundamentals_fd` since it was born (commit `bdf8734`, 2026-01-20). What changed was the **contents** of that table: Task 12 (`e8d5fb2`, 2026-04-22) and Task 12.5 (`9900cb0`, 2026-04-23) re-seeded it from the upgraded FinanceDatabase 2.3.1. The older snapshot had fewer rows and happened to align with what IBKR recognises; the fresh re-seed pulled in a wider set — including names IBKR doesn't carry. The daily collector didn't change; the data underneath it did.

## Final successful run — metrics

From `logs/nse_e2e_20260424T042820Z.log`:

- **Step 1 (IBKR collection)**: 395/398 success, 3 failed
- **Step 2 (flatten)**: 395 records flattened into `current_market_data` (table total now 920)
- **Step 3 (freshness)**: pass — "Current market data: 920 records; AGE: 6.0 hours old; [OK]"
- **Step 4 (screen)**: ran over 950 actionable NSE tickers from the `tickers` table; returned 0 catches. Consistent with the 2026-04-22 Task 10 note ("0 opportunities found — expected, bull market").
- **Alerts**: `--mode test` disables Telegram by design (main.py:152). Not a silent failure.

## The 3 failing tickers — diagnosis

`stock_fundamentals` contains INFIBEAM.NS, AKZOINDIA.NS, SEQUENT.NS. All three are ≤9 chars — no truncation issue. IBKR simply doesn't carry them under those names. Probe (`reqMatchingSymbols` against live IBKR):

| DB ticker | IBKR finds | Root cause |
|---|---|---|
| INFIBEAM.NS | `CCAVENUE` on NSE (conId 287232453) | Company renamed to Infibeam Avenues → NSE symbol changed to CCAVENUE. Our DB has the old symbol. |
| AKZOINDIA.NS | No NSE/BSE match (AKZONOBEL, AKZO, Akzo — all return 0) | Not carried by IBKR today. Either delisted from IBKR's catalog, or a symbol our DB has but theirs doesn't know. |
| SEQUENT.NS | No NSE/BSE match | Likely delisted / merged (Sequent Scientific had corporate activity). |

**CCAVENUE** and **AKZONOBEL** are NOT in `stock_fundamentals`, `stock_fundamentals_fd`, or `tickers` — so renaming INFIBEAM → CCAVENUE in our tables would need to be paired with a fresh fundamentals fetch for the new symbol.

These are data-hygiene issues in the curated list, not pipeline bugs. See Open items for options.

## DB state snapshot (post-run)

```
current_market_data: 920          (was 525 before run; +395 fresh NSE)
ibkr_market_data:    1458         (raw JSON blobs; accumulates)
prices_daily:        5,598,705    (historical — unchanged)
tickers total:       7,810
  NSE:     1,933                  (full FD-seeded universe for NSE; 950 active, 983 inactive)
  LSE:     1,326
  SET:     1,312
  TSE:     1,003
  IDX:       718
  SEHK:      664
  ASX:       498
  SGX:       172
  TADAWUL:   103
  JSE:        81
stock_fundamentals:    398        (curated, IBKR-verified, NSE only)
stock_fundamentals_fd: 1,921      (FD-seeded raw, NSE only)
```

## Architectural note (not a reconciliation issue — just flagging)

NSE pipeline currently has:
- Collector populates `current_market_data` for the 398 curated names (`stock_fundamentals`)
- Screener reads 950 "actionable" tickers (`tickers` where status=ACTIVE or null/stale last_updated)

So the screener is technically processing 950 against criteria, but only 398 have fresh `current_market_data` — the other 552 are either stale or missing. Usually a no-op, but if any of those 552 happened to hit a match opportunity on a given day, we wouldn't see it. Worth thinking about whether the screener should also read from `stock_fundamentals` for NSE so the whole pipeline is centered on the 398 curated set. Low-priority question but worth deciding.

## Applied during follow-up session (2026-04-24, post-handoff)

1. **AKZOINDIA → JSWDULUX** (corporate action, JSW acquisition of Akzo Nobel India):
   - `stock_fundamentals`: renamed `AKZOINDIA.NS` → `JSWDULUX.NS` (still 398 rows).
   - `prices_daily`: renamed 2,471 historical rows from `AKZOINDIA.NS` → `JSWDULUX.NS` (coverage 2016-04-18 → 2026-04-17, no target-side collision).
   - Result: JSWDULUX should be IBKR-qualifiable on the next collector run.
2. **INFIBEAM → CCAVENUE** (symbol change, company renamed Infibeam Avenues):
   - `stock_fundamentals`: renamed `INFIBEAM.NS` → `CCAVENUE.NS` (still 398 rows).
   - `prices_daily`: 0 rows for INFIBEAM, nothing to migrate.
   - **Still not fully resolved** — see TODO below (IBKR returns two contracts for CCAVENUE on NSE; qualifier rejects the ambiguity).

## Open items

### NSE — data hygiene TODOs
1. **CCAVENUE qualifier ambiguity (carry-over).** After renaming INFIBEAM → CCAVENUE, IBKR's NSE catalog returns two contracts for `CCAVENUE`: conId 287232453 ("AVENUESAI LTD", regular) and conId 800289087 ("CCAVENUE_E1", partly-paid). `Stock('CCAVENUE','NSE','INR')` fails to qualify because the match is non-unique. Options: (a) store conId alongside the symbol in `stock_fundamentals` and qualify by conId, (b) add a localSymbol equality filter to the collector to prefer the regular class, (c) drop CCAVENUE from the curated 398. Low priority — one ticker in a 398-name universe.
2. **SEQUENT investigation.** IBKR returns no NSE/BSE match for `SEQUENT`. Sequent Scientific had corporate activity; likely delisted or merged under a new symbol. Needs a lookup against NSE's own listing data to find the successor (if any), otherwise drop from the curated list. Curated count would go 398 → 397.

### NSE — screener/collector universe source (decision needed)
3. **Should `screener.universe.get_universe()` read from `stock_fundamentals` instead of `tickers` (via `get_actionable_tickers`) for NSE?** Current flow pulls 950 "actionable" names from `tickers` — but only the 398 curated names get fresh `current_market_data` each morning, so the 552-row gap is always stale/missing. Tracked for user review (see "tickers table + history" note below).

### ASX / SGX — parked until Task 11
4. ASX/SGX have cap-filtered FD seeds in `tickers` (498 / 172) but no `stock_fundamentals` rows yet. The prerequisite is **Task 11** (already queued in master plan): run `collect_ibkr_fundamentals.py` against the cap-filtered seeds, flatten into `stock_fundamentals`, then they reach NSE parity. Do not run the daily collector against them until Task 11 completes — same class of failure NSE hit pre-fix would reappear.

## Commits

The one-line SQL fix in `scripts/etl/ibkr/collect_daily_ibkr_market_data.py`, the status note in `docs/master_development_plan.md`, and this progress report are the three working-tree changes to commit. The DB renames in `stock_fundamentals` / `prices_daily` are data changes and not tracked in git.

## Logs for review

- `logs/nse_e2e_20260424T034937Z.log` — first run (aborted due to systemic Error 200s pre-fix)
- `logs/nse_e2e_20260424T041501Z.log` — second run (TWS disconnect mid-run)
- `logs/nse_e2e_20260424T042820Z.log` — **third run, fully green end-to-end** ← read this one
