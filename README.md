## Global Market Scanner Monorepo

This repository contains multiple related projects, including the core **Global Macro Scanner** application in `global-macro-scanner/`.

- `global-macro-scanner/`: Python-based macro scanner that pulls market data from IBKR (delayed Type 3) and Yahoo Finance, stores data in PostgreSQL, and runs screening/alerting. See `global-macro-scanner/README.md` for full details.
- `client/`, `server/`, `shared/`: Supporting application components (frontend, backend, and shared code) when present in your local checkout.
- `scripts/`: Auxiliary or legacy scripts at the monorepo level.

### Getting Started (Scanner)

For installation, configuration, and usage instructions for the scanner itself, see:

- `global-macro-scanner/README.md`

