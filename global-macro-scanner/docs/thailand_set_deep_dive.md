# Thailand SET Exchange - Deep Dive Investigation

## Executive Summary

**Status:** ❌ IBKR does NOT support Thailand SET exchange  
**Current Solution:** ✅ YFinance fallback working correctly  
**Root Cause:** IBKR service limitation, not a code issue

## Investigation History

### Previous Tests Conducted

1. **Direct Exchange Codes** (All Failed)
   - `Stock('PTT', 'SET', 'THB')` → "Invalid destination or exchange"
   - `Stock('PTT', 'BKKSET', 'THB')` → "Invalid destination"
   - `Stock('PTT', 'THAILAND', 'THB')` → "Invalid destination"
   - `Stock('PTT', 'BKK', 'THB')` → "Invalid destination"
   - `Stock('PTT', 'XBKK', 'THB')` → "Invalid destination"
   - `Stock('PTT', 'XTHA', 'THB')` → "Invalid destination"

2. **SMART Routing** (Failed)
   - `Stock('PTT', 'SMART', 'THB', primaryExchange='SET')` → "Invalid destination"
   - `Stock('PTT', 'SMART', 'THB')` → No THB currency matches

3. **Contract Search** (No Results)
   - `reqMatchingSymbolsAsync('PTT')` → 33 results, **ZERO with THB currency**
   - `reqMatchingSymbolsAsync('CPALL')` → No THB matches
   - All results were for other exchanges (US, etc.)

4. **Contract Details** (Failed)
   - `reqContractDetailsAsync()` → No details found for any SET contract

5. **Account Verification** (Confirmed)
   - Delayed data (Type 3) works for: US, Canada, India, Indonesia
   - Account has proper IBKR connection
   - Issue is specific to Thailand SET

## Web Research Findings

### IBKR Official Status
- IBKR has **NOT** established connection with Thailand SET
- IBKR has expanded to other Asian markets (Taipei Exchange, Korea) but NOT Thailand
- SET requires Direct Market Access (DMA) through member brokers
- Institutional investors need prior approval from SET

### SET Exchange Requirements
- SET offers DMA for institutional investors
- Requires member broker with SET approval
- Orders routed through broker's infrastructure to SET trading system
- Not available through standard IBKR retail accounts

## Current Implementation

### Code Location
**File:** `data/providers.py` (lines 122-126)

```python
elif symbol.endswith('.BK'):
    # Thailand SET not supported by IBKR - skip to YFinance fallback
    # Tested: SMART routing, primaryExchange, direct SET all fail
    # Error: "The destination or exchange selected is Invalid"
    return None
```

### Behavior
1. `.BK` symbols are detected early in `IBKRProvider.process_stock()`
2. Function returns `None` immediately (skips IBKR processing)
3. Falls back to `YFinanceProvider` in `screener/core.py`
4. YFinance successfully provides data for Thailand stocks

### Verification
```python
import yfinance as yf
stock = yf.Ticker('PTT.BK')
hist = stock.history(period='1mo')
# Returns valid data ✅
```

## Possible Solutions

### Option 1: Keep Current Solution (Recommended)
**Pros:**
- ✅ Already working
- ✅ No code changes needed
- ✅ YFinance provides reliable data for Thailand
- ✅ Free and accessible

**Cons:**
- ⚠️ Slightly slower than IBKR (sequential processing)
- ⚠️ Rate limits may apply with large universes

### Option 2: Contact IBKR Support
**Steps:**
1. Contact IBKR customer support
2. Request Thailand SET access
3. Verify if institutional account needed
4. Check market data subscription requirements

**Likelihood:** Low - IBKR has not announced Thailand support

### Option 3: Use Local Thai Brokerage
**Steps:**
1. Open account with SET member broker
2. Integrate their API (if available)
3. Add as alternative data provider

**Pros:**
- ✅ Direct SET access
- ✅ Real-time data

**Cons:**
- ❌ Additional account required
- ❌ API integration complexity
- ❌ May require residency/regulations

### Option 4: Alternative Data Providers
**Options:**
- Alpha Vantage (has Thailand support)
- Polygon.io (check coverage)
- Quandl/Nasdaq Data Link
- Bloomberg API (expensive)

**Consideration:** Cost vs. benefit analysis needed

## Testing Scripts Available

1. **`tests/check_thailand_permissions.py`**
   - Checks account permissions
   - Tests contract details

2. **`tests/diagnose_thailand.py`**
   - Deep dive exchange code search
   - Tests multiple variations

3. **`tests/test_set_exchange.py`**
   - Basic SET exchange tests

4. **`tests/test_set_smart.py`**
   - SMART routing tests

5. **`tests/test_set_variations.py`**
   - Comprehensive exchange variations

6. **`tests/diagnose_thailand_comprehensive.py`** (NEW)
   - All-in-one comprehensive diagnostic
   - Tests all possible approaches

## Recommendations

### Short Term
1. ✅ **Keep current YFinance fallback** - It's working well
2. ✅ **Monitor IBKR announcements** - Check for Thailand support updates
3. ✅ **Run comprehensive diagnostic** - Use new script to verify current state

### Medium Term
1. Consider alternative data providers if YFinance becomes unreliable
2. Monitor IBKR API updates for new exchange support
3. Evaluate cost/benefit of local brokerage integration

### Long Term
1. If IBKR adds Thailand support, update code to use IBKR first
2. Maintain YFinance as fallback for all markets
3. Consider multi-provider strategy for redundancy

## Code Maintenance

### Current Status: ✅ Working Correctly

The code correctly:
- Detects `.BK` symbols
- Skips IBKR processing (avoids errors)
- Falls back to YFinance automatically
- Provides data for Thailand stocks

**No immediate action required** - the workaround is functioning as intended.

## References

- [IBKR Market Access](https://www.interactivebrokers.com/en/index.php?f=1563)
- [SET Direct Market Access](https://www.set.or.th/en/services/institutions/direct-market-access)
- [IBKR API Documentation](https://interactivebrokers.github.io/tws-api/)
- Previous investigation: `docs/thailand_set_investigation.md`
