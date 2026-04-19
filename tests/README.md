# Tests

All test and diagnostic scripts in this directory were written during active development against live IBKR TWS. They are retained as executable references — do not delete them.

`scripts/testing/` holds DB-side diagnostics and offline screener tests. See that directory for tools that do not require TWS.

---

## Requires TWS (live IBKR connection)

### Basic connectivity
| File | What it tests |
|------|--------------|
| `ib_test.py` | Basic IB connect/disconnect |
| `test_qualify.py` | `qualifyContracts` against live TWS |
| `verify_mapping.py` | IBKRProvider contract mapping |
| `verify_scans.py` | IBKR scanner scan types |
| `debug_historical.py` | Historical bar data retrieval |
| `debug_suffixes.py` | YF/IBKR suffix cross-check |

### NSE / India
| File | What it tests |
|------|--------------|
| `test_intl.py` | IBKRScannerProvider + screener.core |
| `test_option_b.py` | Async screener.core path |
| `test_utf8.py` | UTF-8 output from screener |

### Thailand SET (research — not yet in production)
| File | What it tests |
|------|--------------|
| `check_thailand_permissions.py` | Account permissions for SET |
| `diagnose_thailand.py` | Exchange code discovery for SET |
| `diagnose_thailand_comprehensive.py` | All approaches to SET access |
| `test_set_exchange.py` | SET as primary exchange |
| `test_set_smart.py` | SET via SMART routing + primaryExchange |
| `test_set_variations.py` | SET exchange code variations |
| `test_thailand_all_accounts.py` | SET access across all IBKR accounts |
| `verify_thailand_account_settings.py` | Account settings / delayed data |
| `find_ptt.py` | PTT contract lookup (specific ticker test) |

### Other markets (research)
| File | What it tests |
|------|--------------|
| `test_indonesia_access.py` | IDX (Indonesia) access via IBKR |

---

## Requires DB + IBKR

| File | What it tests |
|------|--------------|
| `integration_tests/test_current_markets.py` | NSE + ASX + SGX multi-market scan |
| `integration_tests/test_enhanced_features.py` | RSI, MA, ATR, pattern recognition |
| `integration_tests/debug_india_screening.py` | Debug why India stocks fail screening |

---

## Offline / no TWS required

| File | Dependencies | What it tests |
|------|-------------|--------------|
| `provider_tests/test_provider_data.py` | internet | YFinance fundamental fields |
| `provider_tests/test_fundamental_cache.py` | internet | CacheManager integration |
| `test_yf.py` | internet | YFinanceProvider async path |
| `verify_criteria.py` | internet | yfinance ticker lookup |
| `verify_pg.py` | DB | psycopg2 connectivity |

---

## Running scripts

These are standalone scripts, not a pytest suite. Run them directly:

```bash
# Basic IBKR connectivity (TWS must be running)
python tests/ib_test.py

# Verify NSE contract mapping
python tests/verify_mapping.py

# Thailand SET research
python tests/test_set_exchange.py

# YFinance provider (no TWS needed)
python tests/test_yf.py
```

For DB diagnostics and offline screener tests, see `scripts/testing/`.
