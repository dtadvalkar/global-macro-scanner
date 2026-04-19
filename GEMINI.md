# GEMINI.md — Instructions for Gemini (Global Macro Scanner)

Read `AGENT_GUIDE.md` first. It is the shared source of truth for this project.

## Gemini-specific expectations

- Treat `global-macro-scanner/` as the real project root
- Treat `main.py` as the primary scanner runner unless the user explicitly says otherwise
- Prefer concise answers, but do not trade away correctness
- Before suggesting structural changes, inspect the current repo state first
- Do not invent new canonical paths, env locations, or dependency workflows

## Working rules

- Prefer editing existing canonical modules over adding new Python files
- For DB work, prefer `db.py` instead of new one-off scripts
- Keep docs consistent with `README.md` and `AGENT_GUIDE.md`
- Be conservative with cleanup: classify before deleting
- If a file looks historical but still documented or referenced, do not remove it casually

## What to read first

1. `AGENT_GUIDE.md`
2. `CLAUDE.md`
3. `README.md`
4. `db.py`
5. `main.py`
