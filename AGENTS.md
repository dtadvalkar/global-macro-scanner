# AGENTS.md — Shared Contract for Coding Agents

This is the shared project contract for coding agents working in this repository. Agent-specific overlays such as `CLAUDE.md`, `.cursorrules`, and `GEMINI.md` should stay aligned with this file and only add genuinely agent-specific behavior.

## Project identity

- This repository root is the active project root.
- The primary scanner runner is `main.py`.
- Secondary runners such as `main/main_automated.py` should be described conservatively unless explicitly validated for the task at hand.

## Environment and dependencies

- Canonical virtual environment: `.venv/`
- Canonical dependency file: `requirements.txt`
- Canonical secrets file: `.env`
- Canonical env template: `.env.example`
- Do not modify committed secrets or `.env` values.

## Canonical paths

- Core runtime: `main.py`, `db.py`, `config/`, `screener/`, `screening/`, `data/`, `storage/`, `alerts/`, `scheduler/`
- Main docs: `README.md`, `DEVELOPMENT.md`, `docs/master_development_plan.md`
- Shared handoff docs: `docs/tasks/`
- Historical material: `docs/archive/`, `scripts/legacy/`

## Database rules

- Prefer `db.py` for Python-side database access.
- Do not create new ad-hoc Postgres inspection scripts unless explicitly requested.
- Keep repeated SQL logic centralized instead of duplicating queries across scripts.

## Editing rules

- Make minimal diffs.
- Reuse existing code paths before adding new ones.
- Prefer extending canonical modules over adding new top-level Python files.
- Do not treat backup files or generated artifacts as source.
- Avoid touching `data_files/raw/` unless the task truly requires it.

## Working alongside other agents

Start of session:

1. Read this file and any relevant agent overlay.
2. Run `git log --oneline -20` to see recent work.
3. Run `git status --short` to detect local in-progress changes.
4. Read `docs/master_development_plan.md` for the canonical task ledger.
5. Check `docs/tasks/` for any open `*_plan.md`, `*_progress.md`, or `*_findings.md`.

End of session:

1. Update `docs/master_development_plan.md` if task status changed.
2. If work is partial, leave or update a `*_progress.md` note in `docs/tasks/` before stopping.
3. Do not leave critical context only in chat history or proprietary memory.
4. Use clear commits such as `Task N — ...`, `feat:`, `fix:`, `docs:`, or `chore:`.

## Partial-work handoff discipline

- Partial work must never be left only in unstated assumptions, chat history, or proprietary memory.
- Before stopping on unfinished work, create or update a `docs/tasks/*_progress.md` file.
- Use `docs/tasks/_progress_template.md` when starting a new progress note.
- Every partial-work note should include:
  - task or scope
  - current status
  - files touched
  - commands run
  - blockers or failures
  - next recommended step
- If you changed code but could not verify it, say so explicitly in the progress note.
- If the worktree contains unrelated local changes, note that clearly so the next agent does not misattribute them.

## Quickstart for a fresh agent

1. Activate `.venv`.
2. Copy `.env.example` to `.env` and fill in the required values.
3. Run `pip install -r requirements.txt` if dependencies are missing.
4. Run `python db.py health`.
5. Read `docs/master_development_plan.md` and then `docs/tasks/` for current work.

## Documentation hierarchy

- `README.md`: canonical setup and usage doc
- `DEVELOPMENT.md`: engineering workflow and DB-layer guidance
- `AGENTS.md`: shared agent workflow
- `docs/master_development_plan.md`: canonical task ledger
- `docs/tasks/`: shared plans, findings, and progress notes
- `docs/archive/`: archived historical plans and retired one-off docs

## Execution expectations

- Validate important paths against the repo before declaring them canonical.
- If a runner or ETL script is not fully validated, describe it conservatively.
- When a task changes behavior, update the nearby docs that would otherwise become false.
- If you find ambiguity that affects structure, entrypoints, or data safety, stop and surface it instead of guessing.
