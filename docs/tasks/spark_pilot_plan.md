# Spark Pilot Plan

## Task

- Short task name: Spark pilot for analytics-scale price screening
- Owner / agent: Codex draft + Claude redline; assign before Phase 0 execution
- Date: 2026-05-02 (Codex draft); 2026-05-02 (Claude redline)
- Status: Planned; not started. **Phase 0 blocked on use-case decision (see Open Questions Q5) and on JVM upgrade (see Phase 0).**

## Context

No formal Spark plan was found in the repo or Claude plan store on 2026-05-02. Prior notes only mention "near-term analytics/Spark pilot work" in `docs/tasks/sql_externalization_review_brief.md`.

The SQL externalization work has already centralized active ETL SQL under `sql/` and routed active DB access toward `db.py`. The local database currently has empty `tickers` and `stock_fundamentals` because of the reset incident documented in `docs/tasks/sql_externalization_recovery_plan.md`, but `prices_daily` remains intact at roughly 5.6M rows. That makes Spark work viable if the first pilot operates on `prices_daily` and does not require live scanner validation.

PySpark is not currently installed in `.venv` as of 2026-05-02 (`pip show pyspark` reported not found). Treat Spark dependency setup as an explicit phase, not an assumed environment capability.

**Verified environment state (2026-05-02, Claude redline):**

- Python: 3.12.10, 64-bit (`platform.architecture()` → `('64bit', 'WindowsPE')`).
- Java: `1.8.0_461`, **HotSpot Client VM** (legacy 32-bit JIT profile). This is a Phase 0 blocker — see Phase 0.
- User decision after Phase 0: install **Temurin 17 64-bit JDK** and proceed with use case **(a) offline analytics / backtesting only**.
- `prices_daily`: row-count baseline to be captured in Phase 0 via `db.py info --table prices_daily`.
- `sql/analytics/` already exists in the tree (currently `.gitkeep` only) — reuse it for Spark analytics SQL.
- `scripts/analysis/` is occupied by XML/JSON dump utilities; `scripts/testing/` by test scripts. Neither is a good home for the pilot — see Open Questions Q1.

## Decision

Proceed with the Spark plan before DB recovery.

Do not execute the SQL recovery plan first unless the Spark implementation explicitly needs:

- `tickers` contents
- `stock_fundamentals` contents
- `main.py --exchanges ...` scanner smoke tests
- ETL validation paths that join through the empty tables

For the first Spark pilot, prefer a read-only analytical path over the intact `prices_daily` table.

## Goals

1. Prove Spark can run locally from the canonical `.venv` on Windows.
2. Build a narrow Spark analytics pilot over `prices_daily`.
3. Match an existing pandas/Postgres result for a small ticker/date sample before scaling.
4. Keep the production scanner path unchanged until the Spark result is proven.
5. Document setup, commands, and limitations so future agents do not depend on chat history.

## Non-goals

- Do not replace the daily scanner orchestration in `main.py` during the pilot.
- Do not rewrite existing ETL jobs into Spark yet.
- Do not run live IBKR, YFinance, or Telegram workflows as part of initial Spark validation.
- Do not create ad-hoc destructive DB scripts.
- Do not recover `tickers` or `stock_fundamentals` merely to start Spark work.

## Proposed pilot scope

Start with a read-only Spark job that computes screening-friendly technical features from `prices_daily`, such as:

- 52-week low and high
- latest close
- distance from 52-week low
- 20-day average volume
- recent volume
- days since 52-week low

The output can initially be a DataFrame preview or a local artifact under a clearly documented generated-output location. Only add persisted DB writes after the read-only pilot is verified.

## Architecture preference

Keep Spark isolated from production runtime until proven:

1. New pilot code should live under `scripts/spark/`. This keeps Spark sessions, JVM assumptions, and PySpark imports isolated from existing XML/JSON analysis utilities and test/audit scripts.
2. Shared SQL should live under `sql/analytics/` when the query is meaningful and reusable.
3. DB reads should reuse `db.py` settings or environment conventions instead of duplicating connection config.
4. Production code in `main.py`, `screener/`, and active ETL should remain untouched in Phase 1 unless review shows a tiny integration point is necessary.

## Phase 0 — Environment audit

Read-only checks:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip show pyspark
java -version
.\.venv\Scripts\python.exe db.py health
.\.venv\Scripts\python.exe db.py info --table prices_daily
```

Capture and record in this doc (or a Phase 0 progress note):

- Python version + arch.
- Java version + VM type (Client/Server) + arch.
- `prices_daily` schema (column names + dtypes), row count, min/max `date`, ticker count.

Expected as of 2026-05-02:

- Python venv exists; Python 3.12.10, 64-bit (verified).
- PySpark is not installed yet (verified).
- `prices_daily` exists and has roughly 5.6M rows.
- `tickers` and `stock_fundamentals` are empty; this is expected and should not block Phase 1.

**JVM blocker (must resolve before Phase 1):** the current `java -version` reports `HotSpot Client VM` from a 1.8 JRE. The Client VM is the legacy 32-bit-flavored JIT and caps heap at roughly 1.5 GB — not viable for Spark on `prices_daily` at 5.6M rows. PySpark 3.5+ is formally on Java 8/11/17 LTS, and Spark 4.x drops Java 8 entirely. User selected Temurin 17. Required:

- Install **Temurin 17 64-bit JDK**.
- `JAVA_HOME` points at the new JDK.
- `java -version` reports `64-Bit Server VM`.

Do not proceed to Phase 1 until that is true.

## Phase 1 — Dependency setup

Add Spark dependency deliberately after choosing the target:

- Option A: install `pyspark` into `.venv` for local-only pilot.
- Option B: add `pyspark` to `requirements.txt` if Spark becomes part of the reproducible project environment.

Prefer Option A for the very first experiment. Move to Option B only **after Phase 4 (correctness) passes** — promoting earlier forces every other agent doing unrelated work to download ~300 MB of pyspark + JVM artifacts.

**Version pin.** Do not let `pip install pyspark` resolve to whatever's latest. PySpark 3.5.0 does not officially support Python 3.12; PySpark 3.5.1+ does; Spark 4.0 has tighter Java requirements. Pin:

```powershell
.\.venv\Scripts\python.exe -m pip install "pyspark>=3.5.1,<4.0"
```

**Hadoop / winutils.exe (Windows local-mode risk).** Official Spark local-mode setup primarily requires a compatible Java installation on `PATH` or `JAVA_HOME`, but Windows local filesystem/Hadoop paths often fail without a matching `winutils.exe` on `HADOOP_HOME`. Treat `winutils.exe` / `HADOOP_HOME` as likely required for this repo's Windows pilot, with the SparkSession probe below as the acceptance test. Steps if the probe fails with Hadoop/winutils-style errors:

1. Identify the Hadoop version bundled with the installed PySpark (`pyspark.version.__hadoop_version__` or check `pyspark/jars/hadoop-*`).
2. Download the matching `winutils.exe` (and `hadoop.dll`) into `C:\hadoop\bin\` (or any path).
3. Set `HADOOP_HOME=C:\hadoop` and prepend `%HADOOP_HOME%\bin` to `PATH`. Restart the shell.

**Output artifact hygiene.** A local Spark session drops `metastore_db/`, `derby.log`, `spark-warehouse/`, and `_SUCCESS`/`*.crc` files in CWD. Add to `.gitignore` before running anything:

```
metastore_db/
spark-warehouse/
derby.log
_SUCCESS
*.crc
```

Verification:

```powershell
.\.venv\Scripts\python.exe -c "import pyspark; print(pyspark.__version__)"
.\.venv\Scripts\python.exe -c "from pyspark.sql import SparkSession; s=SparkSession.builder.master('local[2]').appName('probe').getOrCreate(); print(s.range(1).collect()); s.stop()"
```

The second command forces JVM startup and exposes `JAVA_HOME` or PySpark/Java version mismatches, but it is **necessary, not sufficient**. The in-memory `range(1).collect()` does not exercise the local filesystem path that requires `winutils.exe`, so a Hadoop/`HADOOP_HOME` misconfiguration will still pass this probe and only fail later on the first real Parquet write. Do not consider Phase 1 accepted until you have done a real Parquet round-trip from Spark — for example, `s.range(10).write.mode('overwrite').parquet('data_files/spark/_probe.parquet')` followed by `s.read.parquet('data_files/spark/_probe.parquet').count()`. If that errors with `HADOOP_HOME unset` or `winutils.exe` not found, install winutils per the steps above before continuing.

## Phase 2 — Read path selection

User selected use case **(a) offline analytics / backtesting only**. Optimize the first Spark path for reproducible local analysis, not scanner-runtime integration.

Choose one of two read strategies:

1. JDBC from PostgreSQL into Spark.
2. Export a bounded `prices_daily` sample and load it into Spark locally.

Recommended first pass: bounded local sample exported to Parquet. It avoids JDBC driver friction and proves Spark transformation logic first. Since the chosen use case is offline analytics/backtesting, JDBC is not needed unless a later decision changes the scope.

The sample should be small enough to iterate quickly but realistic enough to cover window functions:

- several hundred tickers, or
- one market suffix if available from ticker naming, or
- a fixed recent date range plus a handful of known tickers.

## Phase 3 — Implement pilot transformation

Create a narrow Spark script that:

1. Starts a local Spark session (`local[*]` master, named app, explicit driver memory).
2. Loads the bounded sample. **For Parquet inputs, do not pass an explicit `StructType`** — Parquet has its own footer-embedded schema, and forcing a different precision (e.g. `DecimalType(20,8)` over the on-disk `decimal(20,15)`) raises `SchemaColumnConvertNotSupportedException` at read time. Read without an explicit schema and assert the column-set/dtype against the Phase 0 baseline immediately after load. The "no inferSchema" rule from Spark folklore applies to CSV/JSON, not Parquet.
3. Computes the technical features listed in "Proposed pilot scope" (but for Phase 4 acceptance, only the two named there — see below).
4. Prints row counts and a deterministic preview (sorted, fixed seed if sampling).
5. Exits cleanly without writing to production tables.

Keep the first script deliberately boring and auditable. Avoid wiring it into `main.py`.

## Phase 4 — Correctness comparison

The baseline must be the **existing canonical computation**, not a freshly-written pandas reference. `screening/screening_utils.py` only consumes `days_since_low`; the current upstream producer is `data/providers.py` in the YFinance feature-building path:

- `low_52w = hist['Low'].min()` over the one-year `hist` frame.
- `days_since_low` uses `low_series = hist['Low'].tail(252) if len(hist) >= 252 else hist['Low']`, then `low_series.idxmin()`, then `(datetime.now() - low_date.replace(tzinfo=None)).days`.

Before writing Phase 3, re-check this producer in the current worktree and treat it as the Phase 4 spec. Spark agreeing with itself is not the test; Spark agreeing with the production computation is.

**As-of-date rule.** The current production path computes `days_since_low` as calendar days from `datetime.now()` back to the date of the low, not from each historical row date. Phase 4 must match that production "as of now/latest evaluation date" behavior. A per-row historical `days_since_low` may be useful later for backtesting, but it is a different feature and should not be used as the first acceptance baseline.

**Phase 4 acceptance — only two features.** Don't acceptance-test all six. Pick:

1. `52w low` per ticker over the same lookback window.
2. `days_since_low` (calendar days from the agreed as-of date back to the date of the 52w low).

Compare on a tiny sample:

- same ticker set
- same date range
- same 52-week lookback definition (calendar-365 vs trading-252 — pin which the baseline uses)
- same as-of date for `days_since_low`
- (later) same volume averaging window

Acceptance criteria:

- Spark and baseline agree on row count.
- Per-ticker `52w_low` matches exactly (it's a min — no tolerance).
- `days_since_low` matches exactly for the agreed as-of date.
- Empty or sparse-history tickers are handled explicitly (NULL vs error vs row-skip — pin which).

Once these two pass, expand to the rest of the feature set listed in "Proposed pilot scope" without re-gating Phase 5.

## Phase 5 — Scale test

Run against the full intact `prices_daily` table or a large export.

Measure:

- runtime
- memory behavior
- startup overhead
- output row count
- failure mode on malformed/null rows

This phase can happen before DB recovery because it only needs `prices_daily`.

## Phase 6 — Integration decision

After the pilot works, decide whether Spark should remain an analysis tool or become part of scanner runtime.

Current user-selected use case for this plan: **offline analytics / backtesting only**.

Options:

1. Keep as offline analytics only.
2. Use Spark to precompute technical feature tables.
3. Use Spark for broad historical backtests.
4. Integrate Spark into scanner execution.

Recommended default and current decision: keep Spark offline until it proves clear value over SQL/Postgres for the target workload.

## Verification commands

Minimum before marking the pilot complete:

```powershell
.\.venv\Scripts\python.exe db.py health
.\.venv\Scripts\python.exe <spark-pilot-script>
```

If dependencies are added to committed project files:

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Do not use `main.py --exchanges NSE --mode test` as a required Spark-pilot check until `tickers` and `stock_fundamentals` are restored.

## Risks

1. Local Spark setup on Windows may fail because of Java, Hadoop/winutils, path, or PySpark version issues. **Most likely failure mode** — see Phase 0 (Server VM requirement) and Phase 1 (SparkSession probe, winutils fallback, and version pin).
2. JDBC setup may add driver friction; avoid it in the first transformation pass if possible.
3. Spark startup overhead may outweigh benefits for daily scanner workloads. Single-node Spark on 5.6M rows is often slower than indexed Postgres for narrow queries — this is what Phase 5 is meant to surface.
4. Feature definitions can drift from the existing screener if not compared carefully. Phase 4 mitigates by pinning the existing screener computation as the baseline, not a fresh pandas reference.
5. Empty `tickers` / `stock_fundamentals` can create false failures if someone uses scanner smoke tests too early.
6. Spark drops `metastore_db/`, `derby.log`, `spark-warehouse/` into CWD on every run — easy to commit by accident. `.gitignore` updates land in Phase 1.

## Open questions

Claude redline (2026-05-02) — recommended answers below; user to confirm Q5 before Phase 1.

1. **Folder.** Use new `scripts/spark/`. `scripts/analysis/` is currently XML/JSON dump utilities (`audit_mkt_json.py`, `discover_xml.py`, `dump_xml.py`, etc.); `scripts/testing/` is test/audit scripts. Neither matches a recurring analytics pipeline. A dedicated `scripts/spark/` keeps Spark sessions, JVM artifacts, and pyspark imports isolated from agents working on the rest of the repo.
2. **Read path.** Parquet export, not JDBC. Avoids the Postgres JDBC driver download dance on first run; lets Phase 3 prove transformation logic before adding driver friction. Promote to JDBC only if Phase 6 chooses scanner integration.
3. **Phase 4 feature set.** Two features only — `52w low` and `days_since_low` — compared against the existing screener computation. See updated Phase 4. Six-feature acceptance is too wide for a first pass.
4. **`requirements.txt`.** Local-only (`pip install` into `.venv`) until Phase 4 passes. Promote to `requirements.txt` after correctness is proven, not before.
5. **Use case — RESOLVED.** User selected **(a) offline analytics / backtesting only**. This means Phase 2 should prefer a Parquet/local-sample path, and JDBC/materialized feature tables are out of scope unless a future plan changes the goal.

## Next recommended step

After acceptance, begin Phase 1 only after the JVM blocker is resolved; do not install PySpark or implement code until:

1. Temurin 17 64-bit JDK is installed.
2. `JAVA_HOME` points to Temurin 17.
3. `java -version` reports `64-Bit Server VM`.
4. Phase 0 environment audit is captured in this doc or a `spark_pilot_progress.md` note.
