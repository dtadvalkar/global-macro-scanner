# Offline Backtest v1 — 52-week-low strategy

## Task

- Short task name: Build a first offline backtest of the scanner's 52-week-low strategy.
- Owner / agent: Claude (Opus 4.7)
- Date: 2026-05-16

## Status

- Current status: **DONE.** New script `scripts/spark/06_backtest_52w_strategy.py` ran end-to-end against `prices_daily` for NSE+IDX+SET. Outputs land in the gitignored `data_files/spark/backtest_52w/`. Sample (50 tickers/market) and broader (full universe) runs both green; sanity checks clean.
- Confidence: High for v1 scope. Strategy *result* is honest: across this window the 52w-low + days-since-low filter underperforms (mean returns negative for most horizons). That's a useful baseline.

## Files touched

- `scripts/spark/06_backtest_52w_strategy.py` (new) — vectorised pandas backtest workflow with CLI, sanity checks, JSON + Parquet outputs. Lives in `scripts/spark/` per repo convention; the actual implementation is pure pandas (Spark JVM not required for this data scale).
- `sql/analytics/prices_daily_by_markets.sql` (new) — joins `tickers` so the loader can be market-scoped without resolving ticker lists in Python first.
- `sql/analytics/stock_fundamentals_mcap.sql` (new) — pulls `mkt_cap_usd` for a ticker batch (only rows with positive caps).
- `docs/tasks/backtest_52w_strategy_progress.md` (this file).
- Outputs (gitignored): `data_files/spark/backtest_52w/backtest_52w_signals.parquet`, `data_files/spark/backtest_52w/backtest_52w_summary.json`.

## Implementation summary

Per-ticker pipeline (vectorised on numpy / pandas):

1. Trailing-252-row rolling features: `low_52w = low.rolling(252).min()`, `high_52w = high.rolling(252).max()`, `avg_volume_20d = volume.rolling(20).mean()`, `avg_volume_30d = volume.rolling(30).mean()`, `rvol = volume / avg_volume_30d`.
2. `days_since_low` via `sliding_window_view` on `low` (returns the relative index of the first occurrence of the rolling min, matching pandas `Series.idxmin()` tie-break).
3. Forward closes via `close.shift(-h)` for each horizon `h in {5, 10, 20}` -- by construction *no lookahead*: the signal on date D uses only the trailing window through D, and forward returns are then evaluated post hoc.
4. Signal filter mirrors `screening_utils.should_pass_screening`'s CLIENT-SIDE block:
   - `close > 0`
   - `close <= low_52w * 1.03` (`price_52w_low_pct`)
   - `close <= high_52w * 0.50` (`price_52w_high_pct`)
   - `1 <= days_since_low <= 30` (`min/max_days_since_low`)
   - `volume >= 50_000` **OR** `rvol >= 2.0` (matches the OR gate in `screening_utils.py:90`)
   - `avg_volume_20d >= 50_000`
   - `1 <= close <= 1000`
5. Market-cap filter applied **after** the per-ticker compute: join `mkt_cap_usd` from `stock_fundamentals`, keep `mkt_cap_usd >= get_min_market_cap(market)`. Tickers without fundamentals coverage are dropped unless `--no-market-cap-filter`.
6. Forward returns are left NULL when the future close is unavailable -- the summary reports `with_data` and `missing_future` per horizon so the edge effect is visible, not silent.

### CLI

```
--start-date YYYY-MM-DD     (default 2024-01-01)
--end-date   YYYY-MM-DD     (default today)
--markets    NSE,IDX,SET    (default NSE,IDX,SET)
--sample-tickers N          (first N tickers per market alphabetical; diagnostic)
--horizons   5,10,20        (trading-row offsets; default)
--output-dir data_files/spark/backtest_52w
--no-market-cap-filter      (skip mkt_cap_usd floor; diagnostic only)
```

### V1 intentional omissions (documented; *not* failures)

The v1 filter set deliberately excludes the following indicators from `should_pass_screening`. Each can be added in a v2 pass without re-doing the data plumbing:

- RSI (`rsi_enabled`) -- would require a per-row rolling RSI(14) over close; not implemented to keep the v1 surface area small.
- SMA50 / SMA200 ratios (`ma_enabled`) -- would require rolling means + per-row ratio checks.
- ATR (`atr_enabled`) -- needs True Range computation.
- Pattern recognition (`double_bottom_enabled`, `breakout_enabled`) -- pattern detectors live in `screening_utils.detect_*`; reimplementing here invites drift.
- IBKR-stored-data path quirks (`_screen_stored_market_data` shortcuts) -- the backtest is OHLCV-only; the IBKR stored path is orthogonal.

The backtest only models the **core entry decision**: near a fresh 52-week low, with a sane liquidity / price range and an exchange-appropriate market cap floor. Adding the technical filters typically *narrows* the signal set, so v1's numbers should be read as an upper bound on how often the strategy *fires*.

## Commands run

```text
.\.venv\Scripts\python.exe -m py_compile scripts\spark\06_backtest_52w_strategy.py   # OK
.\.venv\Scripts\python.exe scripts\hooks\import_safety.py   # exit 0
.\.venv\Scripts\python.exe scripts\hooks\sql_guard.py       # exit 0

# Sample run: 50 tickers per market.
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe scripts\spark\06_backtest_52w_strategy.py `
    --sample-tickers 50 --start-date 2024-01-01 --end-date 2026-04-30

# Broader run: full universe for NSE+IDX+SET.
.\.venv\Scripts\python.exe scripts\spark\06_backtest_52w_strategy.py `
    --markets NSE,IDX,SET --start-date 2024-01-01 --end-date 2026-04-30

# Diagnostic: skip mcap floor to see the raw signal distribution.
.\.venv\Scripts\python.exe scripts\spark\06_backtest_52w_strategy.py `
    --markets NSE,IDX,SET --start-date 2024-01-01 --end-date 2026-04-30 `
    --no-market-cap-filter --output-dir data_files\spark\backtest_52w_diag
```

## Results

### Sample (50 tickers/market, NSE+IDX+SET, 2024-01-01 -> 2026-04-30)

| Metric | Value |
|---|---|
| Loaded | 75,348 rows / 150 tickers in 3.8 s |
| Pre-mcap signal rows | 71 |
| Post-mcap signal rows | 20 (all SET; 5 distinct tickers) |
| Signal date range | 2025-05-29 -> 2025-07-09 |
| 5d  mean / win | -1.10% / 35.0% |
| 10d mean / win | +2.14% / 45.0% |
| 20d mean / win | +8.90% / 65.0% |
| Sanity checks | clean (no duplicates, no out-of-range dates) |

### Broader (full universe, NSE+IDX+SET, 2024-01-01 -> 2026-04-30)

| Metric | Value |
|---|---|
| Loaded | 427,091 rows / 827 tickers in 4.3 s |
| Pre-mcap signal rows | 829 (per-ticker compute in 2.2 s) |
| Post-mcap signal rows | **123** (all SET; 17 distinct tickers) |
| mcap coverage | 826/827 tickers had positive `mkt_cap_usd` (99.9%) |
| Dropped: missing mcap | 0 |
| Dropped: below per-market threshold | 706 |
| Signal date range | 2025-05-27 -> 2026-03-26 |
| 5d  mean / win | -1.40% / 41.5% |
| 10d mean / win | -1.56% / 38.2% |
| 20d mean / win | -0.72% / 38.2% |
| Sanity checks | clean |

### Diagnostic (`--no-market-cap-filter`)

| Market | Signals | Tickers | 5d mean / win | 10d mean / win | 20d mean / win |
|---|---:|---:|---|---|---|
| NSE | 484 | 73 | -1.20% / 37% | -0.52% / 41% | -2.25% / 42% |
| SET | 291 | 39 | -0.53% / 42% | -1.07% / 40% | +0.83% / 43% |
| IDX |  54 |  5 | +0.06% / 48% | -1.23% / 46% | -1.02% / 43% |
| **Total** | **829** | **117** | -0.89% / 39% | -0.76% / 41% | -0.99% / 43% |

Edge-effect warnings (correctly emitted): 2 signals lack +5d / +10d future close and 69 lack +20d future close because the dataset ends within the horizon window. Those signals appear in the parquet but with NULL `fwd_return_*` columns and are excluded from the per-horizon averages.

### What the numbers mean

- **The filtered strategy is unprofitable in this window.** Across 123 post-mcap signals, all three horizons produced negative mean returns and sub-50% win rates. The v1 filter set captures "near a fresh 52-week low" without the timing / quality indicators (RSI, MA, ATR) that production layers on top -- so this is the *floor* of strategy performance, not the realistic deployment.
- **The mcap filter is doing most of the work.** 829 raw signals reduce to 123 after the per-market USD cap floor (NSE 150M / IDX 600M / SET 450M). Specifically, *all* surviving signals were SET. The post-mcap signal set is so SET-skewed because (a) NSE was in a bull regime over the window so few large-cap NSE names hit 52w lows, (b) IDX has only ~1y of valid signal dates given the 2024-05-15 first-row constraint plus the 252-row warmup, and (c) the SET universe at the new 450M threshold still leaves room.
- **AOT.BK vs AOT-R.BK divergence is real and noteworthy.** The signal set picks up both the underlying ordinary share and the NVDR (`-R.BK`). For 2025-07-02..2025-07-09 the NVDR returned +20-36% over the +10d/+20d horizons while the underlying returned -10% to -19%. Per-ticker per-event analysis is a follow-up; the open NVDR policy question (filter at seed time vs. dedupe at signal time) is tracked in `docs/tasks/idx_set_enablement_plan.md` Open Q #1 and partially addressed in the operations hardening doc.

## Sanity checks

The script enforces five checks at runtime, all of which passed for both the sample and broader runs:

1. No duplicate (`ticker`, `signal_date`) rows.
2. All `signal_date` values fall within the requested `[--start-date, --end-date]` window.
3. Per-horizon `with_data` counts plus `missing_future` always equal the signal total (forward closes are NULL by construction when the future row is past the dataset end).
4. Market-cap coverage report is printed pre-filter, with a WARNING if coverage < 80%.
5. Empty-market WARNINGs print explicitly when a requested market returned no rows.

## Limitations of v1

1. **No RSI / MA / ATR / pattern checks.** The strategy result is a floor; adding these will reduce signal count and (typically) improve win rate. Tracked in "intentional omissions" above.
2. **Calendar-day `days_since_low`.** This matches the production logic (`data/providers.py:80-86`), but pandas semantics here mean the difference is computed in *calendar days* between adjacent trading rows. Long weekends / holidays inflate the value relative to a pure trading-day count. Acceptable for v1 because production does the same.
3. **No transaction costs / slippage / position sizing.** Forward returns are raw close-to-close. A v2 with even a flat 10 bps per side would shift the win threshold meaningfully.
4. **No exit logic.** Holding-to-horizon is the only exit. A trailing stop or take-profit would change the picture.
5. **Signal-cluster dependency.** Many signals are consecutive days on the same ticker (the price stays near the low for a few sessions). Treating each as an independent observation overstates the effective sample size; the 5d / 10d / 20d horizons partially overlap. A v2 should dedupe to one signal per ticker per "event" (e.g. first day in a contiguous run).
6. **Lookback handling for IDX/SET.** Only ~1 year of valid signal dates is available because the IDX/SET history starts 2024-05-15 and we require 252 trading rows of warmup. That's a data ceiling, not a script limitation.
7. **All-cash, all-in implied.** No portfolio construction, no max-concurrent-positions cap. Real-money use would gate on both.

## Recommended next iteration

1. **Add the RSI / MA / ATR filters.** Replicate `calculate_rsi` etc. on the rolling windows; verify they match the production producer on a small sample (the existing Phase 4 pattern in `scripts/spark/04_compare.py` is the template).
2. **Event-dedup.** Collapse contiguous signal runs per ticker to one entry signal (first day of the cluster). Re-evaluate horizon returns.
3. **NVDR dedup.** When both `X.BK` and `X-R.BK` qualify on the same date, keep the higher-volume one (or both with a flag column). Coordinate with the open-question policy in the IDX/SET plan.
4. **Cost / slippage model.** Apply 5-15 bps per side; recompute win rates.
5. **Per-year / per-regime stratification.** Slice signals by year + market and recompute. The current aggregate hides regime-specific behavior.
6. **Compare against a baseline.** Buy-and-hold the same universe over the same window; see whether the strategy beats it on risk-adjusted terms, not just absolute returns.
7. **Wire the runtime CRITERIA fully** (e.g. apply a preset from `config/criteria.py:PRESETS`). The script currently reads only the literal CRITERIA values that map to the v1 filter set.

## Blockers or failures

None.

## Notes for the next agent

- The script is **pandas-only** despite living under `scripts/spark/`. The Spark dependency (JVM, HADOOP_HOME, PATH prepend) is *not* required to run it. The location is for pattern consistency with the existing analytics scripts; the data scale (~430K rows for NSE+IDX+SET) fits comfortably in memory.
- For a future scale-out (e.g. all 5.6M rows, all markets, multi-year backtest matrix), switching the per-ticker `for` loop in `generate_signals()` to a `groupBy('ticker').applyInPandas()` over a Spark DataFrame is a 20-line edit. The `per_ticker_signals` function is already the unit-of-work.
- Outputs are written to `data_files/spark/backtest_52w/` (default `--output-dir`). That path is already in `.gitignore` via the `data_files/spark/` pattern (see `.gitignore:42`).
- `config/criteria.py` is the source of strategy thresholds. If thresholds change in production, the backtest picks them up on the next run -- *unless* you also need to bump the `LOOKBACK_TRADING_DAYS` constant in the script (currently pinned at 252).
- One ticker out of 827 has no fundamentals row (mcap coverage 99.9%). Acceptable for now; identifying it would be a one-liner if needed.
