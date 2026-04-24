Archived from `.cursor/plans/CODEBASE_CLEANUP_PLAN.md` on 2026-04-23 so this historical cleanup plan is visible to all agents.

---
name: codebase-cleanup-plan
overview: Single canonical document for Global Macro Scanner repo cleanup—policy (phases A–E), verification rules, protected paths, and batched execution steps to avoid agent loops.
todos:
  - id: phase-a-verify-junk
    content: "(Phase A) Inventory candidate junk, prove each file is unreferenced, then delete only verified generated artifacts and backup copies."
    status: pending
  - id: phase-b-map-entrypoints
    content: "(Phase B) Build and record the canonical path map before moving anything: primary entrypoints, scheduler flows, ETL scripts, ops helpers, tests, and historical alternates."
    status: pending
  - id: phase-c-safe-moves
    content: "(Phase C) Move only clearly non-canonical but still potentially useful files into scripts/legacy/, scripts/ops/, or docs/archive/ with same-change path updates where needed."
    status: pending
  - id: phase-d-prove-orphans
    content: "(Phase D) Delete only legacy files that have zero code/docs/runtime references and no retained historical value; log every deletion and move in docs/tasks/global_macro_cleanup_progress.md."
    status: pending
  - id: phase-e-docs-finalize
    content: "(Phase E) Update README and developer docs so canonical entrypoints, script taxonomy, and archived locations are accurate immediately after restructuring."
    status: pending
isProject: true
---

# Codebase cleanup plan (policy + runbook)

This archived file preserves a historical cleanup spec that originally lived under `.cursor/plans/`.
Its metadata and pending-style checklist entries are preserved for history only and must not be treated as current task state.

## Part 1 — Policy (phases A–E)

### Intent

- Reduce clutter without breaking known workflows.
- Make canonical runtime paths obvious.
- Avoid deleting files just because they look old.
- Preserve enough history that maintainers can still trace prior experiments.

### Canonical assumptions to verify before edits

Before any move or deletion, confirm these against the current tree and references:

- Primary daily orchestration: `main.py`
- Centralized DB interface: `db.py`
- Scheduler flow: `scheduler/market_scheduler.py`
- Core screening path: `screener/universe.py`, `screener/core.py`
- Canonical IBKR ETL candidates:
  - `scripts/etl/ibkr/collect_daily_ibkr_market_data.py`
  - `scripts/etl/ibkr/flatten_ibkr_market_data.py`
- Canonical YFinance ETL candidate(s):
  - `scripts/etl/yfinance/collect_historical_yfinance.py`
  - `scripts/etl/yfinance/collect_daily_yfinance.py`

### Protected paths

Do not delete or relocate these without explicit maintainer approval:

- `.env`
- `main.py`
- `db.py`
- `requirements.txt`
- `.venv/`
- `README.md`
- `tests/README.md`
- `docs/master_development_plan.md`
- `docs/developer_guide/architecture.md`

### Required verification before any move or delete

For every candidate file, check:

1. Code references
2. Documentation references
3. Operational relevance

### Phase A — Verified garbage only

Delete only after checks confirm disposable generated artifacts.

### Phase B — Build the path map first

Before structural moves, create or update `docs/tasks/global_macro_cleanup_progress.md` with a short current canonical map section.

### Phase C — Conservative restructuring

Create directories if needed:

- `scripts/legacy/`
- `scripts/ops/`
- `docs/archive/`
- `docs/tasks/`

### Phase D — Orphan deletion

Delete only when code references, doc references, scheduler usage, and historical value have all been ruled out.

### Phase E — Final documentation pass

Update docs before calling cleanup complete.

## Part 2 — Runbook (batches; anti-loop)

Use one batch per session unless the maintainer says to continue. After each batch, append a short note to `docs/tasks/global_macro_cleanup_progress.md`.
