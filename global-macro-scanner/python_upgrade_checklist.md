# Python Upgrade: 3.11.9 → 3.12 - Safety Checklist

## ✅ Pre-Upgrade Verification

### 1. Virtual Environment Status
- [ ] Confirm you're using a virtual environment: `which python` should point to venv
- [ ] Check virtual environment is activated: prompt should show `(venv)`
- [ ] Verify current packages: `pip list`

### 2. Dependencies Compatibility Check
- [ ] Check all requirements are compatible with Python 3.12:
  ```bash
  # Test current environment still works
  python -c "import psycopg2, yfinance, ib_insync, pandas, numpy; print('All imports OK')"
  ```

### 3. Backup Current Setup
- [ ] Create virtual environment backup if needed
- [ ] Note exact package versions: `pip freeze > requirements_before_upgrade.txt`

## 🚀 Upgrade Process

### Option 1: Recreate Virtual Environment (Recommended)
```bash
# Deactivate current venv
deactivate

# Remove old venv (optional, but clean)
rm -rf venv

# Install Python 3.12 (via your method of choice)
# Then recreate venv with Python 3.12

# Create new venv with Python 3.12
python3.12 -m venv venv

# Activate new venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### Option 2: Upgrade in Place (Higher Risk)
```bash
# Upgrade Python installation
# Then upgrade packages
pip install --upgrade -r requirements.txt
```

## 🧪 Post-Upgrade Testing Checklist

### Phase 1: Basic Functionality
- [ ] Python version: `python --version` should show 3.12.x
- [ ] Basic imports work:
  ```bash
  python -c "import sys; print(f'Python {sys.version}')"`
  python -c "import psycopg2, yfinance, ib_insync, pandas; print('Core imports OK')"
  ```

### Phase 2: Database Interface Testing
- [ ] DB connection: `python db.py health`
- [ ] DB validation: `python db.py validate`
- [ ] Table info: `python db.py info --table stock_fundamentals`

### Phase 3: ETL Pipeline Testing
- [ ] YFinance import: `python -c "from scripts.etl.yfinance.test_raw_ingestion import get_fundamentals_tickers; print('YF import OK')"`
- [ ] IBKR import: `python -c "from scripts.etl.ibkr.flatten_ibkr_market_data import create_current_market_data_table; print('IBKR import OK')"`

### Phase 4: Main Application Testing
- [ ] Config imports: `python -c "from config import CRITERIA, MARKETS; print('Config OK')"`
- [ ] Screener imports: `python -c "from screener.core import screen_universe; print('Screener OK')"`
- [ ] Main script dry run: `python main.py --mode test --exchanges NSE`

### Phase 5: Integration Testing
- [ ] Full pipeline test (if market is open)
- [ ] Telegram alerts test (if configured)

## ⚠️ Potential Issues & Solutions

### Common Issues:
1. **psycopg2 compatibility**: May need `psycopg2-binary` instead of `psycopg2`
2. **ib-insync**: Usually works fine, but test connection
3. **yfinance**: Generally compatible
4. **pandas/numpy**: Usually no issues

### If Issues Occur:
1. **Recreate venv** with Python 3.12 and reinstall all packages
2. **Check package versions**: Some may need updating for Python 3.12
3. **Virtual environment conflicts**: Ensure you're using the right Python executable

### Rollback Plan:
1. Keep Python 3.11.9 installation available
2. Switch back to old venv if needed
3. `pip install -r requirements_before_upgrade.txt` to restore exact versions

## 📊 Expected Results

### ✅ Success Indicators:
- All imports work without errors
- Database connections successful
- ETL scripts run without import errors
- Main application starts correctly

### 📈 Performance Improvements Expected:
- Python 3.12 has performance improvements
- Better async performance (relevant for IBKR operations)
- Improved memory usage

## 🎯 MCP Installation After Upgrade

Once Python 3.12 is confirmed working:

```bash
# Install MCP server
pip install mcp-server-postgres

# Test installation
mcp-server-postgres --help

# Configure in Cursor IDE settings
```

## 📞 Support

If issues occur:
1. Check Python version: `python --version`
2. Check venv: `which python`
3. Test imports individually
4. Check error messages carefully
5. Consider recreating venv if persistent issues

---
*Last updated: 2026-01-19*
*Tested upgrade path: 3.11.9 → 3.12.x*