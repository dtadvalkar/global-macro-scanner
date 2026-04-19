## Global Market Scanner Monorepo

This is the **monorepo shell**. The only active Python scanner project is `global-macro-scanner/`. Everything else at this outer root is workspace scaffolding.

### Repo layout

| Path | Role |
|------|------|
| `global-macro-scanner/` | **Active scanner project** — Python app, DB, screening logic, ETL scripts |
| `client/` | Frontend application components (when present in your checkout) |
| `server/` | Backend application components (when present in your checkout) |
| `shared/` | Code shared between client and server (when present) |
| `scripts/` | Auxiliary monorepo-level scripts (currently empty) |
| `main.py` | Thin convenience wrapper — forwards to `global-macro-scanner/main.py` |
| `pyproject.toml` | Monorepo-level metadata only; scanner deps live in `global-macro-scanner/requirements.txt` |

### Where to work

- **All scanner work** happens inside `global-macro-scanner/`. That is the real project root.
- **Environment**: `global-macro-scanner/.venv` (Python 3.12)
- **Secrets**: `global-macro-scanner/.env` (never committed)
- **Dependencies**: `global-macro-scanner/requirements.txt`

### Getting started (scanner)

```bash
cd global-macro-scanner
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # fill in DB and API credentials
python main.py --exchanges NSE --mode test
```

For full setup, architecture, and ETL docs see `global-macro-scanner/README.md`.

