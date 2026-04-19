# Agent Guide — Global Macro Scanner

This is the shared project contract for coding agents working in this repository. Agent-specific files such as `CLAUDE.md`, `.cursorrules`, and `GEMINI.md` should stay aligned with this guide.

## Project identity

- The active Python project is this directory: `global-macro-scanner/`
- The outer repo root is a monorepo shell, not the scanner app
- The primary scanner runner is `main.py`
- Secondary runners must not be treated as canonical unless explicitly documented that way

## Environment and dependencies

- Canonical virtual environment: `.venv/` in this directory
- Canonical dependency file: `requirements.txt`
- Canonical secrets file: `.env` in this directory
- Do not install scanner dependencies from the outer-root `pyproject.toml`

## Repo structure

- Canonical application paths:
  - `main.py`
  - `db.py`
  - `config/`
  - `data/`
  - `storage/`
  - `screener/`
  - `screening/`
  - `scheduler/`
  - `scripts/etl/`
- Ops and diagnostics:
  - `scripts/analysis/`
  - `scripts/testing/`
  - `scripts/utils/`
- Legacy/archive:
  - `scripts/legacy/`
  - `docs/archive/`

## Database rules

- Prefer `db.py` for Python-side database access
- Do not create new ad-hoc Postgres inspection scripts unless explicitly requested
- Keep repeated SQL logic centralized instead of duplicating queries across scripts

## Editing rules

- Make minimal diffs
- Reuse existing code paths before adding new ones
- Prefer extending canonical modules over adding new top-level Python files
- Do not treat backup files or generated artifacts as source
- Avoid touching raw sample payloads in `data_files/raw/` unless the task truly requires it

## Git and generated files

- Be conservative with deletes and moves
- Classify logs, dumps, raw payloads, and outputs before removing them
- Preserve local files when untracking generated artifacts; prefer `git rm --cached` where appropriate
- Do not modify secrets or `.env` values

## Documentation hierarchy

- Outer repo `README.md`: monorepo-shell guidance only
- This directory’s `README.md`: canonical setup and usage doc for the scanner
- `CLAUDE.md`, `.cursorrules`, `GEMINI.md`: agent operating instructions
- Topic docs under `docs/`: specialized details only; they should not redefine core setup or canonical entrypoints

## Execution expectations

- Validate important paths against the repo before declaring them canonical
- If a runner or ETL script is not fully validated, describe it conservatively
- When a task changes behavior, update the nearby docs that would otherwise become false

## Collaboration

- This repo may be worked on by multiple agents at once
- Check worktree state before large moves or cleanups
- If you find ambiguity that affects structure, entrypoints, or data safety, stop and surface it instead of guessing
