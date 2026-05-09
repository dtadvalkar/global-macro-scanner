# Spark Pilot Progress

## Task

- Short task name: Spark pilot for analytics-scale price screening
- Owner / agent: Claude
- Date: 2026-05-02

## Status

- Current status: **Phases 0–5 complete. Pilot transformation passes Phase 4 acceptance (50/50 exact match) and Phase 5 scale test (5.6M rows, 2,718 features in ~24s Spark wall-time).**
- Confidence: High — every phase produced expected output; no skipped checks.

## Files touched

Tracked changes (untracked or `M`):

- `.gitignore` — added Spark local-mode artifacts + `data_files/spark/`
- `docs/tasks/spark_pilot_plan.md` — Codex draft + Claude redline + Codex updates (untracked)
- `docs/tasks/spark_pilot_progress.md` — this file
- `scripts/spark/01_export_sample.py` — bounded sample export (NSE × 50 × 1y)
- `scripts/spark/02_features_spark.py` — Phase 3 Spark transformation
- `scripts/spark/03_features_pandas.py` — Phase 4 pandas baseline mirroring `data/providers.py:66,247,270-273`
- `scripts/spark/04_compare.py` — Phase 4 diff (exit 0 on full agreement)
- `scripts/spark/05_scale_test.py` — Phase 5 scale test over full `prices_daily`

Untracked artifacts (gitignored under `data_files/spark/`):

- `prices_daily_sample.parquet` (523 KB) — Phase 2 bounded input
- `features_spark.parquet/` — Phase 3 Spark output
- `features_pandas.parquet` — Phase 4 baseline
- `prices_daily_full.parquet` (151 MB) — Phase 5 input
- `features_full.parquet/` — Phase 5 output

System changes (out-of-tree):

- Installed Temurin 17 JDK (`C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot\`); installer set `JAVA_HOME` at machine scope.
- Downloaded `winutils.exe` + `hadoop.dll` for Hadoop 3.3.5 to `C:\hadoop\bin\` (cdarlint/winutils; closest available to bundled Hadoop 3.3.4).
- Installed `pyspark==3.5.8` (within plan's `>=3.5.1,<4.0` pin) and `pyarrow==24.0.0` into `.venv` (local-only; **not** added to `requirements.txt` per plan).

## Phase 0 audit results

### Python

- Version: **3.12.10**
- Arch: `('64bit', 'WindowsPE')`, machine `AMD64`
- Path: `.venv/Scripts/python.exe` (canonical project venv)

### Java (resolved)

- **Before:** `1.8.0_461`, HotSpot Client VM, `JAVA_HOME` unset → blocker.
- **After:** `17.0.18+8`, **OpenJDK 64-Bit Server VM Temurin-17.0.18+8**, `JAVA_HOME = C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot\` (machine scope; current shell sessions need `export JAVA_HOME=...` until restarted).

### Database

- `db.py health` → `issues: []` (verified pre- and post-pilot).
- `prices_daily`: **5,598,705 rows**, **2,718** distinct tickers, dates **2016-04-18 → 2026-04-23**.
- `tickers` and `stock_fundamentals`: 0 rows (expected — recovery plan deferred).

### `prices_daily` schema

| Column | PG type | Parquet (pyarrow chose) | Spark sees |
|---|---|---|---|
| `ticker` | text | string | `string` |
| `price_date` | date | date32 | `date` |
| `open`/`high`/`low`/`close` | numeric | decimal128(20,15) | `decimal(20,15)` |
| `volume` | bigint | int64 | `long` |

**Phase 3 lesson learned.** The plan's instruction to use an explicit `StructType(... DecimalType(20,8) ...)` was wrong for Parquet inputs — Parquet has its own footer-embedded schema, and forcing a coarser scale triggers `SchemaColumnConvertNotSupportedException`. The "no inferSchema" rule applies to CSV/JSON, not Parquet. The current scripts read Parquet without an explicit schema and assert column-set equality post-read. **The plan should be updated.**

### Indexes

- PK `prices_daily_pkey` on `(ticker, price_date)` UNIQUE
- `idx_prices_daily_date` on `(price_date)`
- `idx_prices_daily_ticker` on `(ticker)`

### Per-suffix distribution (distinct tickers / total rows)

| Suffix | Distinct | Total rows |
|---|---:|---:|
| `.L` (LSE) | 961 | 1,579,336 |
| `.HK` (SEHK) | 665 | 1,445,981 |
| `.NS` (NSE) | 395 | 920,150 |
| `.AX` (ASX) | 357 | 839,293 |
| `.SI` (SGX) | 149 | 359,551 |
| `.SR` (TADAWUL) | 113 | 271,755 |
| `.JO` (JSE) | 78 | 182,639 |
| **Total** | **2,718** | **5,598,705** |

## Phase 1 — environment setup

- `pip install "pyspark>=3.5.1,<4.0"` → resolved to **pyspark 3.5.8** (py4j 0.10.9.9). Build wheel ~318 MB; install completed cleanly.
- `pip install pyarrow` → 24.0.0 (added because pandas needs it for Parquet I/O; not in the plan but unavoidable).
- `.gitignore` updated (`metastore_db/`, `spark-warehouse/`, `derby.log`, `_SUCCESS`, `*.crc`, `data_files/spark/`).
- **Probe** (`SparkSession.builder.master('local[2]').appName('probe').getOrCreate(); s.range(3).collect(); s.stop()`) passed. Printed a `winutils.exe not found` WARN but Spark fell back to builtin-java for in-memory ops — not a failure for the probe.
- **However**, the first real I/O run (Phase 3 Parquet write) hit the actual `HADOOP_HOME unset` error and aborted. Set `HADOOP_HOME=C:\hadoop` after dropping `winutils.exe` + `hadoop.dll` (Hadoop 3.3.5 from cdarlint/winutils, binary-compatible with PySpark's bundled 3.3.4); subsequent runs were clean. **Plan note:** the probe is necessary but not sufficient — real Parquet I/O is what surfaces winutils issues. The plan should call this out so the next agent doesn't think the probe alone clears Phase 1.

## Phase 2/3 — bounded sample + Spark transformation

- Sample: 50 NSE tickers, alphabetical, full-year coverage (≥240 trading days) over 2025-04-17..2026-04-17. **12,398 rows / 523 KB Parquet.**
- Spark job uses two window functions: trailing-252 partition by ticker, then min-by-low with deterministic tie-break (`low ASC, price_date ASC`). This matches `pandas.Series.idxmin()`'s "first label with min value" semantics.
- Output: 50 ticker rows × {`low_52w`, `low_date`, `days_since_low`}.

## Phase 4 — correctness

Baseline producer in current worktree (verified, matches plan):

- `data/providers.py:66, 247` — `low_52w = hist['Low'].min()` over the full `hist` frame (yfinance `period='1y'`, ~252 trading days).
- `data/providers.py:270-273` — `low_series = hist['Low'].tail(252) if len(hist) >= 252 else hist['Low']; low_date = low_series.idxmin(); days_since_low = (datetime.now() - low_date).days`.

Reproducibility tradeoff: production uses `datetime.now()` against live yfinance data — not reproducible against historical Postgres. The honest comparison is "Spark on Postgres" vs "pandas on Postgres" using **identical input data and identical algorithm**. As-of date pinned to `2026-04-17` (latest NSE date in sample) for both.

Acceptance result:

```
spark rows:  50  cols: ['ticker', 'low_52w', 'low_date', 'days_since_low']
pandas rows: 50 cols: ['ticker', 'low_52w', 'low_date', 'days_since_low']
low_52w        matches: 50/50
low_date       matches: 50/50
days_since_low matches: 50/50
PASS: Spark and pandas baselines agree on all 50 tickers.
```

## Phase 5 — scale test

Full `prices_daily` (5,598,705 rows / 2,718 tickers) exported to Parquet; Spark transform run end-to-end:

| Stage | Rows | Wall time |
|---|---:|---:|
| Postgres → pandas → Parquet (chunks of 500K, `psycopg2`) | 5,598,705 | **281.4 s** |
| Spark Parquet read | 5,598,705 | **13.0 s** |
| Spark window transform + Parquet write | 2,718 | **10.8 s** |
| **Total** | | **319.4 s** |

Per-suffix output reconciles to Phase 0 baseline exactly (LSE 961 / SEHK 665 / NSE 395 / ASX 357 / SGX 149 / TADAWUL 113 / JSE 78 = 2,718).

**Memory observation.** The chunked psycopg2 export held all 5.6M rows in pandas before writing Parquet — ~3.1 GB peak. Fine on a 16 GB workstation but a real ceiling. For a future iteration, switch to incremental Parquet writes via `pyarrow.parquet.ParquetWriter` (or use Postgres `COPY ... TO STDOUT WITH (FORMAT BINARY)` directly into pyarrow). The export is the only slow stage; Spark itself is fast.

**Spark vs Postgres tradeoff (relevant to Phase 6).** Spark transform = ~24 s end-to-end after parquet is materialized. The same window query in Postgres (with the existing `(ticker, price_date)` PK) would also be sub-30 s. The pilot shows Spark *can* do this work without correctness drift, not that it *must*. The user-selected use case (a) offline analytics is the conservative call; integration into scanner runtime is not justified by these numbers.

## Final verification

```
.venv/Scripts/python.exe -m pip check       → No broken requirements found.
.venv/Scripts/python.exe db.py health        → issues: []
git status --short                            → only intended files modified;
                                                 data_files/spark/ properly gitignored.
```

## Blockers or failures

None outstanding. Two issues hit during execution and resolved:

1. **`SchemaColumnConvertNotSupportedException`** when reading Parquet with explicit `DecimalType(20,8)`. Resolved by removing the explicit schema; Parquet metadata is canonical for this input. Plan should be updated.
2. **`HADOOP_HOME unset`** on first real Parquet I/O (despite probe passing). Resolved by installing winutils to `C:\hadoop\bin` and exporting `HADOOP_HOME`. Plan should add the bare probe is not the full Phase 1 acceptance test.

## Next recommended step

Pilot is complete for the (a) offline analytics use case. Suggested follow-ups, not gated:

1. Update `spark_pilot_plan.md` Phase 1 + Phase 3 to fix the two issues above (no explicit schema for Parquet inputs; probe is necessary-but-not-sufficient → require a real Parquet I/O round-trip in Phase 1 acceptance).
2. Decide whether to commit `scripts/spark/` and the `.gitignore` updates, or keep the pilot fully local until Codex reviews.
3. If staying with offline analytics, no further dependency promotion needed (`requirements.txt` stays untouched per plan). If moving toward scenario (b) or (c) later, that re-opens Q5 and triggers a follow-up plan.

## Notes for the next agent

- Two environment requirements: `JAVA_HOME` (Temurin 17) and `HADOOP_HOME=C:\hadoop`. The Temurin installer set `JAVA_HOME` at machine scope, so new shells will see it; `HADOOP_HOME` is currently shell-local — promote to a user/machine env var if you want it persistent.
- Decimal precision in Parquet is `decimal(20,15)` (pyarrow's choice). Don't override this on read.
- The chunked export uses `LIMIT/OFFSET` ordered by `(ticker, price_date)`. For tables larger than ~10M rows, switch to keyset pagination on the PK to avoid the OFFSET cost.
- Production `days_since_low` uses `datetime.now()` against live yfinance. Any future "Spark replaces production" scenario must address that as-of-date reproducibility question — historical Postgres data + a pinned as-of date will not match a live `datetime.now()` evaluation.
- The recovery plan (`sql_externalization_recovery_plan.md`) remains deferred. The Spark pilot did not need `tickers` or `stock_fundamentals`.
- `.claude/settings.local.json` modified by harness state, exclude from any commit.
