# Run from repo root with venv activated
# Windows: use Git Bash or WSL

PYTHON = python

.PHONY: health validate scan-test check-nse check-progress

# Database health and schema validation
health:
	$(PYTHON) db.py health

validate:
	$(PYTHON) db.py validate

# Smoke test: load NSE universe only (no IBKR, no scan)
check-nse:
	$(PYTHON) scripts/testing/test_nse_universe.py

# DB progress summary
check-progress:
	$(PYTHON) scripts/testing/check_progress.py

# Offline screener test (no IBKR required)
scan-test:
	$(PYTHON) scripts/testing/test_offline_screener.py

# YFinance collection smoke test (internet required)
check-yf:
	$(PYTHON) scripts/testing/test_yfinance_collection.py

# Full pipeline in test mode (requires TWS)
run-test:
	$(PYTHON) main.py --exchanges NSE --mode test
