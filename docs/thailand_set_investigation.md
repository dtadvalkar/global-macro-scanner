# Thailand SET Exchange Investigation

## Issue
Thailand stocks (.BK suffix) were generating "Invalid destination or exchange" errors when processed through IBKR.

## Investigation Conducted

### Tests Performed
1. ✅ **Direct exchange code**: `Stock('PTT', 'SET', 'THB')` → ❌ Invalid destination
2. ✅ **SMART routing**: `Stock('PTT', 'SMART', 'THB', primaryExchange='SET')` → ❌ Invalid destination
3. ✅ **Alternative codes**: BKKSET, THAILAND, BKK, XBKK, XTHA → ❌ All failed
4. ✅ **Contract search**: `reqMatchingSymbolsAsync('PTT')` → ❌ 33 results, ZERO with THB currency
5. ✅ **Contract details**: `reqContractDetailsAsync()` → ❌ No details found
6. ✅ **Account verification**: Confirmed delayed data (Type 3) works for US, Canada, India

### Root Cause
**IBKR does not support Thailand SET exchange** in the current account configuration (U11571501). This is not a:
- ❌ Code issue
- ❌ Delayed data issue (Type 3 is working correctly)
- ❌ Exchange code syntax issue

The exchange simply does not exist in IBKR's database for this account type.

## Resolution

### Code Changes
1. **`data/providers.py`**: Added early return for `.BK` symbols to skip IBKR processing
2. **`config/markets.py`**: Documented the limitation with inline comments

### Current Behavior
- Thailand stocks (.BK) are **automatically routed to YFinance** for all data requests
- No IBKR errors are generated for Thailand stocks
- Scanning continues to work perfectly via the YFinance fallback

## Future Options
To enable IBKR support for Thailand, contact IBKR support to:
1. Enable Thailand trading permissions for your account
2. Subscribe to Thailand/Asia-Pacific market data (if available for your account type)

## Verification
YFinance confirmed working for Thailand stocks:
```python
import yfinance as yf
stock = yf.Ticker('PTT.BK')
hist = stock.history(period='1mo')
# Returns 20 days of valid data
```
