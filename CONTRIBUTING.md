# Contributing

## Where things live

| Area | Path |
|------|------|
| Daily entrypoint | `main.py` |
| Config / criteria | `config/criteria.py`, `config/settings.py` |
| Screening logic | `screener/` |
| Data providers | `data/providers.py`, `data/cache_manager.py` |
| DB access | `db.py` — the only place for new DB queries |
| ETL scripts | `scripts/etl/ibkr/`, `scripts/etl/yfinance/` |
| Diagnostics | `scripts/testing/` |
| IBKR live tests | `tests/` |

## DB access rule

All new Python-side DB access goes through `db.py`. Do not create new `check_*.py` files or scatter raw SQL across modules. Add a named method to `Database` or use an existing one (`query`, `execute`, `health_check`).

## Adding a test

- **Offline / no dependencies** → `scripts/testing/` or `tests/provider_tests/`
- **Requires live DB** → mark with `@pytest.mark.requires_db`
- **Requires TWS** → `tests/` root or `tests/integration_tests/`; mark with `@pytest.mark.requires_ibkr`
- Do not add pytest markers to scripts that are meant to be run directly (the IBKR live scripts in `tests/`)

## Commit style

```
<type>(<scope>): short description

body (optional, wrap at 72 chars)
```

Types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`

Examples:
```
fix(screener): correct 52w high/low source to prices_daily
chore(etl): remove stale flatten_ibkr_mega reference
docs(readme): update venv activation commands
```

## Before committing

```bash
python db.py validate      # schema check
make scan-test             # offline screener smoke test
```

## What not to do

- Do not install packages system-wide — use the `.venv` at repo root and `requirements.txt`
- Do not commit `.env`, log files, or anything under `data_files/processed/`
- Do not create new top-level scripts without proposing path + purpose first
- Do not duplicate a query already in `db.py`
