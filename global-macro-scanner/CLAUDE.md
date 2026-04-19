# CLAUDE.md — Instructions for Claude (Global Macro Scanner)

This file is the **single source of truth** for how Claude should work in this repository alongside Cursor. Follow it **literally** when making changes, proposing commands, or answering questions.

Shared project rules also live in `AGENT_GUIDE.md`. If this file and `AGENT_GUIDE.md` ever diverge, follow the more project-specific instruction here and surface the conflict.

---

## 1. What this project is

**Global Macro Scanner** is a Python application focused on **NSE (India)** market data and screening:

- **PostgreSQL** stores raw captures, flattened fundamentals, daily OHLCV history, and current market snapshots.
- **Yahoo Finance** supplies bulk historical OHLCV (e.g. into `prices_daily`).
- **Interactive Brokers (IBKR)** supplies **NSE** market snapshots and related raw payloads (stored in `raw_ibkr_nse`, flattened to `current_market_data` where applicable).
- **FinanceDatabase** (and related flows) feed long-lived / quarterly-style fundamentals; universe and screening logic must stay consistent with what is actually in the DB.

**Primary daily orchestration** lives in `main.py` (collection → flatten → freshness → screen → optional Telegram alerts).

---

## 2. Repository map (where things live)

| Area | Path | Role |
|------|------|------|
| Daily entrypoint | `main.py` | Orchestrates pipeline; subprocesses for IBKR scripts where configured |
| Config | `config/` (`criteria.py`, `markets.py`, `settings.py`) + root `config.py` if present | Criteria, markets, env-backed settings |
| Screening | `screener/` | Universe + core screening |
| Data providers / cache | `data/` | Providers, `cache_manager.py` — align with `stock_fundamentals` schema |
| Persistence helpers | `storage/` | DB helpers, CSV logging |
| Alerts | `alerts/` | Telegram |
| **Central DB access** | **`db.py`** | **Preferred** Python DB interface (pool, `query` / `execute`, health helpers) |
| ETL & one-off tools | `scripts/etl/`, `scripts/analysis/`, `scripts/testing/`, `scripts/utils/` | Organized by purpose; not all are “production” |
| Docs | `README.md`, `docs/`, `DEVELOPMENT.md`, `implementation_plan.md` | Architecture and workflow |

If a path is ambiguous, **open the file** or grep before assuming.

---

## 3. Environment rules (agent-facing)

> For full setup instructions see `README.md`. This section records only the rules agents must follow.

- **Venv**: `.venv` at scanner root. Never install into the outer-root `pyproject.toml` environment.
- **Dependencies**: `requirements.txt` is authoritative. Do not add packages without user approval.
- **Secrets**: `.env` at scanner root. Never commit or log secret values.
- **UTF-8 on Windows**: Many scripts set `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")`. Preserve this if present unless asked to remove it.

**Typical commands** (from scanner root, venv activated):

```text
python main.py --exchanges NSE --mode test
python db.py health
python db.py validate
```

Exact flags are defined in `main.py` and `config/` — do not invent new CLI contracts without user approval.

---

## 4. Non-negotiables (database and “script sprawl”)

These rules align with `DEVELOPMENT.md` and explicit project decisions:

1. **Do not create new ad-hoc Python scripts** whose only purpose is “check Postgres” or run one-off `SELECT`s scattered in random files.
2. **Prefer `db.py`** for new Python-side DB access:
   - Add a **small, named method** on `Database` (or a thin helper module **only if** the user agrees) rather than new `check_*.py` files.
   - Reuse `get_db()` / `Database` patterns already in `db.py`.
3. **Complex data logic** should eventually live in **SQL / migrations / views** where appropriate; Python should orchestrate and call through the DB layer. Until SQL files exist, keep queries **centralized** in `db.py` rather than spread across scripts.
4. **Do not duplicate** the same query in multiple modules. One place, one name.

If the user explicitly asks for a **temporary** diagnostic, keep it under an agreed location (e.g. `scripts/testing/`) and **delete or fold it into `db.py`** once done — unless they say otherwise.

---

## 5. Data model expectations (high level)

Claude should treat these as **conceptual contracts** (exact columns: inspect DB or `db.py` / migrations):

- **`stock_fundamentals`**: Flattened fundamentals (many columns). Screening and ticker lists often key off this.
- **`prices_daily`**: Historical OHLCV bars (e.g. from YFinance), keyed by ticker, date, **source**.
- **`raw_*` tables** (`raw_fd_nse`, `raw_ibkr_nse`, `raw_yf_nse`): Verbatim / archival JSON or XML payloads.
- **`current_market_data`**: **Current** IBKR-derived snapshot fields — not a substitute for long OHLCV history in `prices_daily`.

When debugging “wrong screen” issues, **verify**:

- Ticker symbol conventions (`.NS` vs `.NSE` vs base symbol) match the table you query.
- 52-week highs/lows for screening should come from **history** (`prices_daily`) when that is the project rule — not stale XML fields in fundamentals unless explicitly documented otherwise.

---

## 6. Coding standards (for Claude-generated changes)

- **Minimal diffs**: Only touch what the task requires. No drive-by refactors.
- **Match existing style**: imports, logging, naming, and error handling as in neighboring code.
- **IBKR**: Respect NSE-only assumptions where documented; do not reintroduce fundamentals calls into “market data only” paths unless asked.
- **YFinance**: Prefer **bulk** patterns already used in the codebase; do not add per-ticker hammering that risks rate limits unless the user approves.
- **Docs**: Do not expand markdown docs unless the user asks (README / plans are user-controlled).

---

## 7. Working alongside Cursor

- Treat **Cursor’s prior layout and refactors** as current unless the user reverts them.
- **Prefer extending canonical paths** (`main.py`, `db.py`, `scripts/etl/...`) over adding new top-level scripts.
- If unsure between two designs, **ask one focused question** instead of implementing both.

---

## 8. What to read first (onboarding order)

1. `AGENT_GUIDE.md` — shared project contract  
2. `main.py` — daily pipeline and flags  
3. `config/criteria.py` — screening thresholds  
4. `db.py` — DB access patterns and CLI helpers  
5. `DEVELOPMENT.md` — engineering principles (central DB access, avoid sprawl)  
6. `README.md` / `docs/developer_guide/` — ETL and table documentation  

---

## 9. MCP / external tools

**MCP setup is deferred** unless the user re-enables it. Do not block tasks on MCP. Use `db.py` and agreed SQL workflows for DB inspection unless instructed otherwise.

---

## 10. Definition of done

A change is “done” when:

- It runs under the **project venv** without new secret leaks.
- DB access follows **§4** (no new random `check_db_*.py` unless explicitly requested and scoped).
- **Screening / ETL** behavior matches the user’s stated data sources (YF vs IBKR vs fundamentals).
- **Tests or smoke commands** the user cares about are mentioned if behavior changed (do not claim tests were run unless they were).

---

*Maintainers: keep this file short, authoritative, and updated when workflow rules change.*
