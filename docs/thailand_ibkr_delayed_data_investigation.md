# Thailand SET - IBKR Delayed Data Investigation

## User's Valid Point

**User's Hypothesis:** IBKR should support delayed data (Type 3) for any market, as that's one of IBKR's key value propositions - global market access with delayed data.

**This is a valid concern!** Let's investigate whether:
1. Thailand access needs to be enabled in account settings
2. There's a different exchange code or contract specification
3. A market data subscription is required (even for delayed)
4. Regional permissions need to be activated

## Current Understanding

### What We Know
- ✅ IBKR delayed data (Type 3) works for: US, Canada, India (NSE), Indonesia (IDX)
- ❌ Thailand SET does NOT work with any tested exchange codes
- ❌ Contract qualification fails for all Thailand attempts
- ❌ Symbol search returns no THB currency matches

### Web Research Findings
According to IBKR's market data pricing page and documentation:
- **IBKR does NOT provide delayed data for Thailand SET**
- Even delayed data requires agreements between IBKR and exchanges
- SET is not among exchanges with delayed data agreements
- To access SET data, a real-time subscription would be required (if available)

**However**, this contradicts the user's expectation that delayed data should work globally.

## Possible Explanations

### 1. Account Settings / Permissions
**Hypothesis:** Thailand access might need to be enabled in IBKR account settings.

**To Check:**
- Log into IBKR TWS/Gateway
- Go to Account Settings > Market Data Subscriptions
- Look for "Thailand" or "SET" in available markets
- Check if there's a free delayed data option

### 2. Exchange Code Issue
**Hypothesis:** Maybe the exchange code is different than expected.

**Tested Codes:**
- SET, BKKSET, THAILAND, BKK, XBKK, XTHA
- SMART routing with primaryExchange
- All failed

**Could Try:**
- Check IBKR's exchange directory
- Contact IBKR support for correct code
- Check if it's listed under a different name

### 3. Regional Permissions
**Hypothesis:** Account might need regional permissions enabled.

**To Check:**
- Account Settings > Trading Permissions
- Look for Asia-Pacific or Southeast Asia region
- Verify if Thailand is listed separately

### 4. Market Data Subscription Required
**Hypothesis:** Even delayed data might require a subscription for Thailand.

**To Check:**
- Market Data Subscriptions page
- Look for Thailand/SET pricing
- Check if there's a free delayed option

## Comparison with Working Markets

### Indonesia IDX (Works)
- Exchange code: `IDX`
- Currency: `IDR`
- Delayed data: ✅ Works
- Contract: `Stock('BBRI', 'IDX', 'IDR')`

### India NSE (Works)
- Exchange code: `NSE`
- Currency: `INR`
- Delayed data: ✅ Works
- Contract: `Stock('RELIANCE', 'NSE', 'INR')`

### Thailand SET (Doesn't Work)
- Exchange code: `SET` (tested)
- Currency: `THB`
- Delayed data: ❌ Doesn't work
- Contract: `Stock('PTT', 'SET', 'THB')` → Fails

## Action Items

### Immediate
1. ✅ Run `verify_thailand_account_settings.py` to check account permissions
2. ✅ Check IBKR TWS/Gateway for Thailand in Market Data Subscriptions
3. ✅ Compare with Indonesia IDX (working market) to see differences

### If Thailand Still Doesn't Work
1. Contact IBKR Support with specific question:
   - "Does IBKR support delayed data for Thailand SET exchange?"
   - "If yes, what exchange code should I use?"
   - "Do I need to enable any account permissions?"

2. Check IBKR Official Resources:
   - Market Data Pricing page
   - Exchange Directory
   - API Documentation for supported exchanges

3. Verify Account Type:
   - Some account types may have different market access
   - Institutional vs. retail accounts may differ

## Current Workaround

**Status:** ✅ Working correctly

The YFinance fallback is functioning well:
- Provides reliable data for Thailand stocks
- No errors or issues
- Free and accessible
- Sequential processing (slightly slower than IBKR parallel)

**Recommendation:** Keep using YFinance for Thailand until IBKR access is confirmed/available.

## Testing Scripts

1. **`verify_thailand_account_settings.py`** (NEW)
   - Checks account permissions
   - Tests alternative contract specifications
   - Compares with working markets
   - Tests scanner locations

2. **`diagnose_thailand_comprehensive.py`**
   - Comprehensive diagnostic
   - All exchange code variations
   - Contract details testing

## Conclusion

The user's point is valid - IBKR should theoretically support delayed data globally. However:
- Web research suggests SET is not available even for delayed data
- Extensive testing shows no working exchange codes
- Comparison with Indonesia (which works) suggests Thailand is different

**Next Step:** Verify account settings and contact IBKR support to confirm whether Thailand SET is available and what's needed to enable it.
