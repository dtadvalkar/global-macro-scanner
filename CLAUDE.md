# CLAUDE.md — Claude Overlay

Read `AGENTS.md` first. It is the shared source of truth for this repository.

## Claude-specific expectations

- Keep diffs small and grounded in the current repo state.
- Prefer `db.py` for DB-facing work instead of creating one-off inspection scripts.
- Keep any cross-agent handoff context in repo files, not only in Claude memory or chat history.
- If a file and `AGENTS.md` disagree about project structure, treat the repo itself as authoritative and surface the mismatch.

## Working style

- For structural or multi-file work, check `git status --short` before moving files.
- Use `README.md`, `DEVELOPMENT.md`, and `docs/master_development_plan.md` as the canonical supporting docs.
- Use `docs/tasks/` for shared plan, findings, and progress notes.
- If work stops midstream, leave or update a `docs/tasks/*_progress.md` note before stopping.

## What to read first

1. `AGENTS.md`
2. `README.md`
3. `DEVELOPMENT.md`
4. `db.py`
5. `docs/master_development_plan.md`
