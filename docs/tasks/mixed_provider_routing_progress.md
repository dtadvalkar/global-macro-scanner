# Mixed Provider Routing Progress

## Task

- Short task name: Productionize mixed-provider routing for DATA_SOURCE=auto with IDX/SET enabled
- Owner / agent: Claude (Opus 4.7)
- Date: 2026-05-16

## Status

- Current status: **DONE.** `screener/core.py` now splits the universe by provider and runs IBKR + YFinance branches independently in `auto` mode. New unit tests cover all three DATA_SOURCE modes plus the scanner-early-return regression and the automated runner. Three production-like smokes pass (IDX-only, IDX+SET, NSE+IDX) reaching DAILY PIPELINE COMPLETE with the expected provider split.
- Confidence: High. Tests + smokes all green.

## Files touched

- `screener/core.py` — rewritten around three helpers (`get_provider_for_ticker`, `split_universe_by_provider`, `dedupe_results`) plus internal `_run_scanner_then_deep_scan` / `_run_ibkr_bulk` / `_run_yfinance` runners. Public `screen_universe(universe, criteria, markets=None)` signature unchanged.
- `main/main_automated.py` — `scan_markets` now passes `markets_to_scan` as the third argument to `screen_universe(...)`, so scheduled region scans keep their market scope through routing.
- `tests/provider_tests/test_mixed_provider_routing.py` (new) — five unit tests; no live IBKR / YFinance / DB.
- `docs/tasks/mixed_provider_routing_progress.md` (this file).

## What changed

### Problem

Pre-change `screener/core.py` treated the universe as a single batch:

1. In `DATA_SOURCE in ('ibkr','auto')` it always tried the IBKR scanner first, then **returned early** on any scanner hit.
2. If no scanner hits, it ran IBKR bulk on the *full* universe — including YFINANCE-only `.JK` / `.BK` tickers that IBKR cannot screen.
3. Only after IBKR returned `None` (rare; it returns `[]` on no catches) did it fall back to YFinance.

After flipping `MARKETS['idx']` / `MARKETS['set']` to `True` in commit `a15a6be`, default `DATA_SOURCE=auto` runs mishandled IDX/SET — the IDX/SET smokes only worked when `DATA_SOURCE=yfinance` was forced.

### Routing rules now

| DATA_SOURCE | Behavior |
|---|---|
| `yfinance` | All tickers → `OptimizedYFinanceProvider`. IBKR untouched. |
| `ibkr` | Scanner + IBKR-bulk only on IBKR-compatible tickers. YFINANCE-only tickers are skipped with a warning. |
| `auto` | Universe split by provider. IBKR scanner (only for enabled IBKR-compatible scanner markets) + IBKR bulk runs on IBKR-compatible slice; `OptimizedYFinanceProvider` runs on YFINANCE-only slice. Both always run; one's failure or empty result does not block the other. Results combined and de-duped by `symbol` / `ticker`. |

`get_provider_for_ticker(ticker)` derives the provider from `MARKET_REGISTRY[exchange]['provider']` via `exchange_from_yf_ticker`. `IBKR` and `IBKR_PAID` are treated identically for routing (the tier is what API to call, not subscription state). Unknown suffixes and bare US-style tickers default to IBKR.

`ALL_SCANS` is unchanged — it already only references IBKR-compatible market keys. IDX/SET are not added there.

### Tests

`tests/provider_tests/test_mixed_provider_routing.py` covers:

1. `test_auto_mode_splits_universe_by_provider` — mixed universe; IBKR sees only `RELIANCE.NS`; YFinance sees `AALI.JK` and `AOT.BK`; combined result count is 3.
2. `test_yfinance_mode_skips_ibkr` — neither IBKR provider nor scanner is instantiated.
3. `test_ibkr_mode_skips_yfinance_only_tickers` — `.JK` / `.BK` filtered out of IBKR bulk; YFinance provider not instantiated.
4. `test_auto_mode_runs_yfinance_even_when_scanner_finds_hot_ibkr_ticker` — regression for the old early-return bug; both scanner deep-scan and YFinance results appear in the output.
5. `test_scan_markets_passes_markets_to_screen_universe` — `main/main_automated.py:scan_markets({'idx': True})` propagates that dict to `screen_universe(..., markets={'idx': True})`.

All five tests pass with no live external calls (IBKR/YFinance/DB are monkeypatched). The automated-runner test loads `main/main_automated.py` by file path because `main.py` at repo root shadows the `main/` directory in import resolution, and `main/` has no `__init__.py`; it also stubs `scheduler.market_scheduler` because that module pulls in `schedule`, which is not in `requirements.txt`.

## Commands run

```text
.\.venv\Scripts\python.exe -m py_compile screener\core.py main\main_automated.py   # OK
.\.venv\Scripts\python.exe -m pytest tests\provider_tests\test_mixed_provider_routing.py -q
# 5 passed in 3.34s
.\.venv\Scripts\python.exe scripts\hooks\import_safety.py   # exit 0 (SyntaxWarning noise only)
.\.venv\Scripts\python.exe scripts\hooks\sql_guard.py       # exit 0 (SyntaxWarning noise only)
git diff --check                                            # clean (CRLF warnings only)

$env:DATA_SOURCE='auto'
.\.venv\Scripts\python.exe main.py --exchanges IDX --mode test --skip-collection --skip-flattening
.\.venv\Scripts\python.exe main.py --exchanges IDX,SET --mode test --skip-collection --skip-flattening
.\.venv\Scripts\python.exe main.py --exchanges NSE,IDX --mode test --skip-collection --skip-flattening
Remove-Item Env:DATA_SOURCE -ErrorAction SilentlyContinue
```

## Smoke outcomes

| Smoke | Provider split | Result | Exit |
|---|---|---|---|
| `IDX --skip-collection --skip-flattening` | `IBKR=0, YFINANCE=149` | bulk yfinance, 0 catches, DAILY PIPELINE COMPLETE | 0 |
| `IDX,SET --skip-collection --skip-flattening` | `IBKR=0, YFINANCE=474` | bulk yfinance, 0 catches, DAILY PIPELINE COMPLETE | 0 |
| `NSE,IDX --skip-collection --skip-flattening` | `IBKR=1933, YFINANCE=149` | IBKR stored-data path + bulk yfinance both ran, 0 catches, DAILY PIPELINE COMPLETE | 0 |

All three runs print the new `Provider split: IBKR=X, YFINANCE=Y (DATA_SOURCE=auto)` line, followed by the per-branch invocations and the closing `Combined results: scanner=N, ibkr_bulk=N, yfinance=N, total_after_dedupe=N` line.

Step 3 freshness warnings (`current_market_data` 173h old) are present in all three runs — expected per the smoke spec for test-mode runs that don't actually hit IBKR live; the pipeline still reaches DAILY PIPELINE COMPLETE.

NSE+IDX smoke specifically:
- 1933 NSE tickers go through `IBKR Stored Data Scan` (the offline path that reads `current_market_data`).
- 149 IDX tickers go through `OptimizedYFinanceProvider` via a single bulk `yf.download` (3 delisted ticker warnings only — no rate-limit fan-out).
- Both branches reach completion in the same run.

No yfinance per-ticker fan-out or rate-limit flood observed in any of the three smokes.

## Blockers or failures

None.

## Next recommended step

Commit the change set and move to Part B (Spark pilot verification). Suggested commit:

- `fix(screener): route yfinance-only markets in auto mode`

Bundles: `screener/core.py`, `main/main_automated.py`, `tests/provider_tests/test_mixed_provider_routing.py`, `docs/tasks/mixed_provider_routing_progress.md`.

`.claude/settings.local.json` and any other unrelated files must stay out of the commit.

## Notes for the next agent

- `DATA_SOURCE` defaults to `auto` (`config/settings.py:18`); IDX/SET will now route correctly in production without forcing `DATA_SOURCE=yfinance`.
- `get_provider_for_ticker` collapses `IBKR` and `IBKR_PAID` to a single "IBKR-compatible" tier. If a future market needs a third tier (e.g., a different API client), extend the helper rather than special-casing call sites.
- `main/main_automated.py` loaded by file path in the new test because of the `main.py` vs `main/` shadowing and the optional `schedule` dep. Don't try `from main import main_automated` in tests — it fails.
- The new test file is the first unit test in `tests/provider_tests/` that exercises `screener.core`. Future provider-routing tests should follow the same monkeypatch-the-provider-classes pattern to stay offline.
