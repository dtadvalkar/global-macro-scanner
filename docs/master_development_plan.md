# Global Market Scanner — Master Development Plan

## Overview
Global Market Scanner is a stock screening system that identifies high-potential trading opportunities near 52-week lows across global markets, combining IBKR (NSE and accessible markets) and YFinance (bulk OHLCV history and fallback markets) data sources.

## Current Status
**Progress: 10 of 10 Phase 1 tasks complete. Tasks 11 + 12 + 12.5 all DONE. `stock_fundamentals` is now multi-exchange (1,844 rows across 7 IBKR-free exchanges).**

**2026-04-27** — Task 11 complete. Multi-exchange IBKR fundamentals round-trip executed across NSE / SEHK / ASX / LSE / SGX / TADAWUL / JSE. Final per-exchange counts in `stock_fundamentals`: NSE 408, SEHK 597, ASX 327, LSE 241, SGX 124, TADAWUL 96, JSE 51 = **1,844 total**. NSE end-to-end re-validated post-Task-11 with `main.py --exchanges NSE --mode test` during NSE market hours (exit 0, 388 fresh market data, 0 catches, 4/4 steps green). Notable side-fix: LSE `trailing_period` rule was over-applying — corrected in `config/markets.py` to only fire for ≤2-char symbols (commit 6b56730), lifting LSE collect from 9/1326 to 233/1317. See `docs/tasks/task11_progress.md`.

**2026-04-24** — NSE end-to-end re-validated. Daily collector was pointing at `stock_fundamentals_fd` (raw FD seed); corrected to `stock_fundamentals` (curated). See `docs/tasks/nse_e2e_progress.md`.

| # | Task | Status |
|---|------|--------|
| 1 | Enhanced Scanning Logic | ✅ DONE |
| 2 | Performance Optimizations | ✅ DONE |
| 3 | Automated Scheduling System | ✅ DONE |
| 4 | Repo Cleanup & Trust Restoration | ✅ DONE |
| 5 | Market Expansion — config + two-source strategy | ✅ DONE (config/markets.py updated; registry, toggles, symbol rules in place) |
| 6 | Current Markets Testing (NSE, ASX, SGX) | ✅ DONE (pipeline validated 2026-04-22; 408/612 NSE tickers via IBKR) |
| 7 | Telegram Alert Enhancements | ✅ DONE (signal strength, batching, retry, exchange-aware currency) |
| 8 | Database Optimization | ✅ DONE (get_recent_low_date() added; indexes verified; bug fixed) |
| 9 | Phase 1 Criteria Enhancements | ✅ DONE (RVOL cap + avg_volume_20d + days_since_low all wired) |
| 10 | New Exchange Ticker Universe & Screener Wiring | ✅ DONE (SEHK/LSE/JSE/TADAWUL seeded from static lists; 615k OHLCV rows backfilled; end-to-end verified 2026-04-22) |

**Phase 1 complete.** Phase 2 priorities (Fundamental Integration, Advanced Criteria) are deferred per schedule below.

*Last Updated: 2026-04-22*

---

## Architecture

### Core Components (stable)

| Path | Role |
|------|------|
| `main.py` | Primary daily orchestration entrypoint |
| `main/main_automated.py` | Scheduler-driven runner (called by `scheduler/market_scheduler.py`) |
| `main/main-paper.py` | Paper-trading entrypoint (IBKR paper mode) |
| `scheduler/market_scheduler.py` | Intelligent market timing and scheduling |
| `config/criteria.py` | All screening thresholds (single source of truth) |
| `config/markets.py` | Market and exchange definitions |
| `config/settings.py` | Environment-backed runtime settings (IBKR, DB, Telegram) |
| `data/providers.py` | IBKR + YFinance data providers with fallback logic |
| `screener/core.py` | Multi-provider screening orchestration |
| `screening/screening_utils.py` | Centralized filtering and technical analysis |
| `alerts/telegram.py` | Telegram notification system |
| `db.py` | Central DB access layer (pool, query, execute, health) |

### ETL Scripts

| Path | Role |
|------|------|
| `scripts/etl/ibkr/flatten_ibkr_final.py` | Flattens IBKR XML ratios → `stock_fundamentals` |
| `scripts/etl/ibkr/flatten_ibkr_market_data.py` | Flattens IBKR snapshots → `current_market_data` |
| `scripts/etl/ibkr/collect_daily_ibkr_market_data.py` | Daily IBKR market data collection |
| `scripts/etl/ibkr/seed_exchange_tickers.py` | Seeds `tickers` table for SEHK/LSE/JSE/TADAWUL via IBKR MOST_ACTIVE scanner |
| `scripts/etl/yfinance/collect_historical_yfinance.py` | Bulk YFinance OHLCV → `prices_daily`; `--exchange` flag for per-exchange backfill |
| `scripts/etl/yfinance/collect_daily_yfinance.py` | Daily incremental OHLCV updates |
| `scripts/etl/finance_db/flatten_fd_nse.py` | FinanceDatabase → `stock_fundamentals_fd` |

### Data Source Strategy (two-source, IBKR-primary)

**Historical OHLCV:** Always `yf.download()` batch lists via `collect_historical_yfinance.py` → `prices_daily`. No per-ticker hammering.

**Live(ish) / screening data:** IBKR Type 3 Delayed primary; `yf.download()` as fallback if IBKR fails or market unsupported.

| Exchange | Market | IBKR code | IBKR free? | yfinance suffix | Notes |
|----------|--------|-----------|------------|-----------------|-------|
| NSE | India | `NSE` | ✅ Free | `.NS` | Primary market |
| BSE | India | `BSE` | ✅ Free | `.BO` | |
| ASX | Australia | `ASX` | ✅ Free | (none) | |
| SGX | Singapore | `SGX` | ✅ Free | `.SI` | |
| SEHK | Hong Kong | `SEHK` | ✅ Free | `.HK` | Strip leading zeros: `0005`→`5` |
| LSE | UK | `LSE` | ✅ Free | `.L` | Add trailing period: `BP`→`BP.` |
| JSE | South Africa | `JSE` | ✅ Free | `.JO` | |
| TADAWUL | Saudi Arabia | `TADAWUL` | ✅ Free | `.SR` | Vision 2030 open data mandate |
| TSEJ | Japan | `TSEJ` | ❌ Paid sub | `.T` | Qualifies, Error 162 on data |
| SMART/NYSE | US | `SMART` | ❌ Paid sub | (none) | |
| TSE | Canada | `TSE` | ❌ Paid sub | `.TO` | |
| IBIS | Germany | `IBIS` | ❌ Paid sub | `.DE` | |
| SBF | France | `SBF` | ❌ Paid sub | `.PA` | |
| KSE | Korea | Not in IBKR | — | `.KS` | yfinance-only |
| TWSE | Taiwan | Not in IBKR | — | `.TW` | yfinance-only |
| BOVESPA | Brazil | Not in IBKR | — | `.SA` | yfinance-only |
| Bursa | Malaysia | Not in IBKR | — | `.KL` | yfinance-only |
| SET | Thailand | Not in IBKR | — | `.BK` | yfinance-only |
| IDX | Indonesia | Not in IBKR | — | `.JK` | yfinance-only |

---

## Tasks

### ✅ 1. Enhanced Scanning Logic
Technical indicators and pattern recognition implemented in `screening/screening_utils.py` and `config/criteria.py`.
- RSI filtering (20–45 range)
- Moving average support (price ≤ 1.03× SMA50)
- ATR volatility filtering (1.5–8% range)
- Double bottom pattern detection, volume spike confirmation, breakout detection

### ✅ 2. Performance Optimizations
`OptimizedYFinanceProvider` in `data/providers_optimized.py`:
- Intelligent caching (1-hour TTL)
- Parallel processing (5 concurrent requests, semaphore-controlled)
- Adaptive rate limiting (0.8 req/sec)
- Early filtering to reduce API calls

### ✅ 3. Automated Scheduling System
Implemented. Primary files: `scheduler/market_scheduler.py`, `main/main_automated.py`.
See `docs/market_scheduling_guide.md` for optimal scan times per timezone.

### ✅ 4. Repo Cleanup & Trust Restoration
Completed 2026-04-18. Full execution log: `docs/tasks/global_macro_cleanup_progress.md`.
- 37 junk files deleted
- Script taxonomy verified and documented
- Outer repo declared as monorepo shell
- Stale plans archived to `docs/archive/`

---

### ✅ 5. Market Expansion — IBKR + yfinance Two-Source Strategy

**Research completed 2026-04-22** via live TWS diagnostics. Four additional markets confirmed free via IBKR API; all markets also covered via `yf.download()` bulk as fallback.

**Two-source principle:**
- **Historical OHLCV** → always `yf.download()` bulk (`collect_historical_yfinance.py` pattern)
- **Live(ish) / screening** → IBKR Type 3 Delayed primary; `yf.download()` fallback if IBKR fails

**Newly confirmed free via IBKR (2026-04-22 diagnostic):**
- SEHK (Hong Kong) — symbol format: strip leading zeros (`0005` → `5`)
- LSE (UK) — symbol format: add trailing period (`BP` → `BP.`)
- JSE (South Africa) — standard symbols
- TADAWUL (Saudi Arabia) — numeric codes (e.g., `2222` for Aramco); Vision 2030 open data mandate

**Deliverables:**

1. **`config/markets.py`** — add SEHK, LSE, JSE, TADAWUL with IBKR exchange codes; document symbol format rules per exchange; add Korea/Taiwan/Brazil/Malaysia/Thailand/Indonesia as yfinance-only markets

2. **`data/providers.py`** — extend IBKR provider to handle new exchanges; add symbol format normalisation (HK zero-strip, UK trailing period); yfinance fallback already exists, confirm it picks up new markets

3. **`scripts/etl/yfinance/collect_historical_yfinance.py`** — extend ticker lists to include SEHK (`.HK`), LSE (`.L`), JSE (`.JO`), TADAWUL (`.SR`), plus yfinance-only markets (`.KS`, `.TW`, `.SA`, `.KL`, `.T`)

4. **`scripts/testing/test_ibkr_market_access_final.py`** — update market list with correct symbol formats and findings; fix Japan from wrong `TSE` → `TSEJ`; add SEHK/LSE/JSE/TADAWUL as confirmed-free; mark Korea/Taiwan/Brazil/Malaysia as yfinance-only

**Verify:** Run updated test: `PYTHONPATH="." python scripts/testing/test_ibkr_market_access_final.py`

---

### ✅ 6. Current Markets Testing (NSE, ASX, SGX)

Completed 2026-04-22. Pipeline validated end-to-end:
- IBKR collected 408/612 NSE tickers (204 are stale/merged tickers — known, harmless)
- `avg_volume_20d` and `days_since_low` guard conditions confirmed working on IBKR path
- 0 opportunities found — expected (bull market, no NSE stocks near 52w lows)

---

### ✅ 7. Telegram Alert Enhancements

Completed 2026-04-22. Changes in `alerts/telegram.py`:
- Signal strength: 🔥 EXTREME (RSI ≤ 25 + RVOL ≥ 5×), ⚡ STRONG (RSI ≤ 35 or RVOL ≥ 3×), 📌 WATCH
- Exchange-aware currency symbols (₹ NSE/BSE, S$ SGX, A$ ASX, £ LSE, etc.)
- Single batched message grouped by exchange — no per-stock spam
- Retry with exponential backoff (3 attempts, handles 429 rate limit)
- `send_alert(catch)` kept for backward compatibility

---

### ✅ 8. Database Optimization

Completed 2026-04-22. Changes in `db.py`:
- `get_recent_low_date(ticker, lookback_days=365)` added — queries `prices_daily` using existing composite PK index `(ticker, price_date)`
- Fixed bug: method originally used non-existent column `trade_date` and dict access on a tuple — corrected to `price_date` and `result[0]`
- Composite PK `(ticker, price_date)` confirmed present — no new indexes needed
- Pool size (5) confirmed appropriate for sequential subprocess pipeline

---

### ✅ 10. New Exchange Ticker Universe & Screener Wiring

**Completed 2026-04-22.** SEHK/LSE/JSE/TADAWUL activated via curated static universe lists. IBKR scanner turned out to require a paid subscription (even for exchanges whose market data is free), so universe seeding uses major-index constituents instead.

**Final state:** 264 tickers seeded (SEHK 72, LSE 95, JSE 47, TADAWUL 50); 615k rows backfilled into `prices_daily`; all four exchanges pass end-to-end smoke tests via `main.py --exchanges X --mode test`.

#### What was implemented (2026-04-22)

**Ticker format translation layer** (`config/markets.py`) — single source of truth for all IBKR↔yfinance symbol conversions:
- `ibkr_to_yfinance(ibkr_symbol, exchange)` — converts IBKR scanner output to yfinance format (LSE trailing-period strip, suffix append, etc.)
- `exchange_from_yf_ticker(yf_ticker)` — reverse-lookup exchange from yfinance ticker; derived from `MARKET_REGISTRY` so it stays in sync as exchanges are added
- `normalise_ibkr_symbol(symbol, exchange)` — existing function (yfinance base → IBKR); now documented as the counterpart direction
- All per-exchange edge cases live here only — no duplicate format logic in callers

**`data/providers.py`**:
- `IBKRScannerProvider.get_scanner_results()` now takes `exchange` (MARKET_REGISTRY key) instead of raw `yf_suffix`; delegates to `ibkr_to_yfinance()` internally
- `IBKRProvider._get_exchange_from_symbol()` is now a one-liner calling `exchange_from_yf_ticker()`

**`screener/core.py`**:
- ALL_SCANS expanded with SEHK, LSE, JSE, TADAWUL entries
- 5-tuple format updated: `(instrument, location, scan_code, market_key, ibkr_exchange)` where `ibkr_exchange` is a MARKET_REGISTRY key

**`screener/universe.py`**:
- SEHK, LSE, JSE, TADAWUL added to the exchange mapping with `fd_key=None` (no FinanceDatabase seeding)
- Prints guidance message when `tickers` table is empty for these exchanges

**`scripts/etl/ibkr/seed_exchange_tickers.py`** (new):
- Connects to IBKR MOST_ACTIVE scanner for SEHK/LSE/JSE/TADAWUL
- Uses `ibkr_to_yfinance()` for all symbol translation
- Writes to `tickers` table via `db.save_tickers()`
- Supports `--exchanges` and `--dry-run` flags

**`scripts/etl/yfinance/collect_historical_yfinance.py`**:
- `--exchange` flag added; reads from `tickers` table for the given exchange and bulk-downloads OHLCV

#### Why static lists instead of IBKR scanner (discovered 2026-04-22)

Live dry-run returned "Market Scanner is not configured for one of the chosen locations" (Error 162) for all four exchanges. `reqScannerParameters()` XML revealed:
- `STK.EU.LSE` and `STK.ME.TADAWUL` are tagged `access=restricted` (require specific subscription IDs).
- `STK.HK.SEHK` is unrestricted but still returns 0 results on a free delayed feed.
- JSE (South Africa) has no scanner location at all — absent from every location tree.

"IBKR market data is free" ≠ "IBKR scanner works for free." Scanner is a separately-licensed product.

**Resolution:** curated static lists per exchange (`scripts/etl/ibkr/universe_lists/{sehk,lse,jse,tadawul}.json`) sourcing from major-index constituents (HSI, FTSE 100, JSE Top 40, TASI large-caps). `seed_exchange_tickers.py --source static` is the default. The `--source ibkr` scanner path is preserved for if a scanner subscription is added.

#### Operator guide — refresh the universe

Edit the JSON files in `scripts/etl/ibkr/universe_lists/` every 6–12 months as indices rebalance, then:

```bash
# Reseed from the updated JSONs (idempotent; upserts on conflict)
PYTHONPATH="." .venv/Scripts/python.exe scripts/etl/ibkr/seed_exchange_tickers.py

# Backfill any new tickers (existing bars are unaffected — ON CONFLICT DO UPDATE)
PYTHONPATH="." .venv/Scripts/python.exe scripts/etl/yfinance/collect_historical_yfinance.py --exchange SEHK,LSE,JSE,TADAWUL
```

#### IDX / SET — already populated

DB check on 2026-04-22 showed IDX has 718 rows and SET has 1,312 rows in the `tickers` table (yfinance-only ETL pulled them in at some point). No action needed unless they go stale.

#### Follow-up: upgrade new-exchange universes to NSE-grade (Task 11 / Task 12)

The Task 10 static index lists (SEHK 72 / LSE 95 / JSE 47 / TADAWUL 50) are a **bootstrap**, not the long-term universe. They filter by *index membership* (HSI / FTSE 100 / JSE Top 40 / TASI large-caps) — which is a different and much narrower criterion than the one behind the 398 NSE tickers in `stock_fundamentals`.

**The canonical universe criterion (reverse-engineered from the NSE pipeline 2026-04-22):**

> FinanceDatabase equities for the target exchange where `market_cap_category IN ('Large Cap', 'Mid Cap', 'Small Cap')` — **excluding** Nano Cap, Micro Cap, and None.

For NSE this yielded ~612 candidates, of which 398 ultimately had IBKR fundamentals XML returned. Large+Mid+Small gives meaningful mid/small-cap coverage where 52-week-low setups are most interesting, while dropping Nano/Micro avoids unscreenable illiquid names.

##### ✅ Task 11 — IBKR fundamentals pipeline for the 6 new exchanges + NSE re-seed — DONE 2026-04-27

Ran the full NSE-style pipeline for SEHK / LSE / ASX / SGX / TADAWUL / JSE plus an NSE re-seed (the 2026-01 fundamentals were three months stale). `stock_fundamentals` now covers all 7 IBKR-free exchanges with the same ~80-column mega-schema.

**Final per-exchange counts:** NSE 408, SEHK 597, ASX 327, LSE 241, SGX 124, TADAWUL 96, JSE 51 = **1,844 total**.

Two scripts were generalised (commit `bc0af26`):
- `collect_ibkr_fundamentals.py` — `--exchange`, `--source tickers|fd_capfilter`, `--max-age-days` resume, `--include-inactive`, `--limit`. NSE/INR hardcodes replaced with MARKET_REGISTRY currency + `normalise_ibkr_symbol()`.
- `flatten_ibkr_final.py` — recovered the canonical mega-schema flattener from `b55b8de^` (the in-tree stub didn't match the live ~80-column schema), then adapted: source `ibkr_fundamentals` (not legacy `raw_ibkr_nse`), `--exchange` filter by yf suffix, `CREATE IF NOT EXISTS` + per-row UPSERT, `--replace` for per-suffix delete, per-row commit/rollback so one bad XML doesn't poison the batch.

Side-fix on LSE (commit `6b56730`): the blanket `trailing_period` rule was incorrectly appending `.` to all LSE symbols, collapsing the LSE collect to 9/1326. IBKR's LSE catalog only carries the trailing period for the historical 2-char convention (BP, AV, BA, …); 3+ char symbols (HSBA, GSK, AZN, …) are listed without it. Conditional rule lifted LSE collect to 233/1317. The remaining ~1k LSE failures are FD's `0A*` historical security IDs that IBKR doesn't carry — candidate for a regex filter at FD-seed time (`^0[A-Z0-9]+\.L$`).

NSE end-to-end re-validation: `main.py --exchanges NSE --mode test` ran during NSE market hours 2026-04-27 — 388 fresh market data, 923 in current_market_data, 950 actionable NSE tickers screened, 0 catches, exit 0.

See `docs/tasks/task11_progress.md` for the full run report.

##### ✅ Task 12 — Replace bootstrap lists with FinanceDatabase seed — DONE 2026-04-22

FD 2.3.1 upgrade unblocked the re-seed. Static bootstrap lists retired in favor of `fd.Equities().search()` with the canonical Large+Mid+Small cap filter applied in `screener/universe.py`.

**Final state after Task 12:**

| Our exchange | FD code | Seeded | prices_daily coverage |
|---|---|---|---|
| SEHK | `HKG` | 664 | 628 (94.6%) |
| LSE | `LSE` | 1,326 | 953 (71.9%)* |
| JSE | `JNB` | 81 | 68 (84.0%) |
| TADAWUL | `SAU` | 103 | 99 (96.1%) |

*LSE coverage is held down by ~236 `0XXX.L` historical security IDs that FD carries but yfinance doesn't cover. Follow-up would be to filter these out of the FD seed in `screener/universe.py` (regex `^0[A-Z0-9]+\.L$`).

`universe_lists/*.json` kept as offline fallback (`seed_exchange_tickers.py --source static` still works).

**Caveat — column rename in FD 2.3.1:** `market_cap_category` → `market_cap`. `stock_fundamentals_fd` still has the old column (frozen data). `universe.py` reads `market_cap` from live FD.

#### Deferred exchanges
BOVESPA, KSE, TWSE, BURSA remain `False` in `MARKETS` until ticker universe work is done for them.

#### Future todo — FinanceDatabase re-integration
FinanceDatabase currently returns HTTP 404 (remote GitHub data URL broken). When it recovers, replace scanner-seeded lists with a fundamentals-quality universe (same standard as 398 NSE tickers):
1. Run `scripts/utils/orchestrate_ibkr_pipeline.py` for each new exchange
2. Filter `stock_fundamentals_fd` by market cap threshold (~$1B+)
3. Collect IBKR fundamentals via `collect_ibkr_fundamentals.py`
4. Flatten via `flatten_ibkr_final.py` → `stock_fundamentals`

---

### ✅ 9. Phase 1 Criteria Enhancements

All three filters implemented and verified (2026-04-22):

| Filter | Config key | Value | Status |
|--------|-----------|-------|--------|
| RVOL anomaly cap | `max_rvol` | 20.0 | ✅ Done (`screening_utils.py:93-95`) |
| 20-day avg volume floor | `min_avg_volume_20d` | 50000 | ✅ Done (`providers.py` + `screening_utils.py`) |
| Days-since-low window | `min/max_days_since_low` | 1–30 days | ✅ Done (`providers.py` + `screening_utils.py`) |

- `data/providers.py` — populates `avg_volume_20d` and `days_since_low` in `symbol_data` from `hist` DataFrame
- `screening/screening_utils.py` — two filter blocks after RVOL cap; guard conditions pass IBKR-path stocks through unchanged
- `db.py` — `get_recent_low_date(ticker, lookback_days)` method for offline screener path

**Verified:** `PYTHONPATH="." python scripts/testing/test_offline_screener.py` — 398 NSE stocks processed, no crashes

---

## Phase 2 (Deferred)

### 🔮 Fundamental Integration (Q3 2026)
Earnings quality, revenue growth, debt-to-equity, institutional ownership. Deferred until core scanning is stable and profitable.

### 🔮 Advanced Criteria System (Q4 2026)
Sector rotation, correlation filtering, market regime detection, time-based opportunity windows. Deferred until Phase 1 proves out.

---

## Screening Criteria Reference

See `config/criteria.py` for all thresholds. Current active criteria:

**Core filters:** Price ≤ 1.01× 52-week low, volume ≥ 100k or RVOL ≥ 2.0×, market cap thresholds, price $1–$1000

**Technical filters (implemented):** RSI 20–45, price ≤ 1.03× SMA50, ATR 1.5–8%, RVOL ≤ 20×

**Technical filters (implemented):** avg_volume_20d ≥ 50k, days_since_low 1–30 days

---

## Testing & Verification

```bash
# Offline screener (no external calls, uses DB data)
PYTHONPATH="." python scripts/testing/test_offline_screener.py

# DB health
python db.py health
python db.py validate

# Full test scan (NSE)
python main.py --exchanges NSE --mode test

# Integration tests
python -m pytest tests/integration_tests/ -v
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Signal accuracy | ≥ 70% of alerts are actionable |
| False positive rate | ≤ 30% of filtered stocks |
| Market coverage | ≥ 80% of target markets accessible |
| Scan speed | < 5 min for 5000 stocks |
| API efficiency | < 50% redundant calls (via caching) |
| Daily uptime | ≥ 95% successful scans |
