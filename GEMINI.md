# GEMINI.md — Gemini / Antigravity Overlay

Read `AGENTS.md` first. It is the shared source of truth for this project.

## Gemini-specific expectations

- Treat this repository root as the real project root.
- Treat `main.py` as the primary scanner runner unless the user explicitly says otherwise.
- Prefer concise answers, but do not trade away correctness.
- Before suggesting structural changes, inspect the current repo state first.
- Do not invent new canonical paths, env locations, or dependency workflows.

## Working rules

- Prefer editing existing canonical modules over adding new Python files.
- For DB work, prefer `db.py` instead of new one-off scripts.
- Keep docs consistent with `README.md`, `DEVELOPMENT.md`, and `AGENTS.md`.
- Be conservative with cleanup: classify before deleting.
- If work is unfinished, leave or update a `docs/tasks/*_progress.md` note before stopping.

## Antigravity note

If Antigravity does not support a separate repo-local instruction file, it should still follow `AGENTS.md` plus the visible task state in `docs/master_development_plan.md` and `docs/tasks/`.
