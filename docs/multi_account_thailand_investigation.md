# Multi-Account Thailand SET Investigation

## User's Hypothesis

**User's Question:** "Is it possible that I have two accounts (margin and RRSP), and only one of them has access to Thailand stock market, and the reason these scripts are failing is because my margin account isn't being used for this purpose?"

## Analysis

### Current Code Behavior

1. **Account Selection:**
   - Code uses: `ib.managedAccounts()[0]` - **always uses the FIRST account**
   - No account selection logic
   - No way to specify which account to use

2. **IBKR Connection:**
   - When you connect to IBKR TWS/Gateway, you get access to ALL managed accounts
   - Contract qualification and historical data requests are **not explicitly account-specific** in the API
   - However, **account permissions** may differ per account

3. **Market Data Permissions:**
   - Market data subscriptions can be:
     - **Per-account** (each account has its own subscriptions)
     - **Shared** (all accounts share the same subscriptions)
   - Trading permissions are typically **per-account**

### Why This Could Be The Issue

If you have:
- **Account 1 (Margin):** No Thailand permissions
- **Account 2 (RRSP):** Has Thailand permissions

And the code always uses `managedAccounts()[0]` (which might be the margin account), then:
- Contract qualification might fail
- Historical data requests might fail
- But if you switched to the RRSP account, it might work!

### Testing Strategy

The script `test_thailand_all_accounts.py` will:
1. List ALL managed accounts
2. Test Thailand access for EACH account separately
3. Identify which account (if any) has Thailand access
4. Show account types (margin, RRSP, etc.)

### How IBKR API Works

**Important Note:** 
- Contract qualification (`qualifyContractsAsync`) is **not account-specific**
- Historical data requests (`reqHistoricalDataAsync`) are **not account-specific**
- However, the **underlying permissions** that determine what data is available might be account-specific

**What this means:**
- If Account 1 has no Thailand permissions, qualification might fail
- If Account 2 has Thailand permissions, qualification might succeed
- But the API doesn't let you explicitly "use Account 2 for this request"

**Workaround:**
- The API might use the **first account** or **default account** for permissions
- If accounts have different permissions, you might need to ensure the correct account is first
- Or contact IBKR to enable Thailand on the account you want to use

### Testing Script

Run: `python tests/test_thailand_all_accounts.py`

This will:
1. Show all your accounts
2. Test Thailand on each one
3. Tell you which account (if any) has access

### If One Account Has Access

**Option 1: Ensure Correct Account is First**
- Check IBKR TWS/Gateway account order
- The first account in `managedAccounts()` is used
- You might be able to reorder accounts in TWS settings

**Option 2: Modify Code to Use Specific Account**
- Update `IBKRProvider` to accept account parameter
- Use account-specific requests where possible
- Note: This might be limited by IBKR API capabilities

**Option 3: Enable Thailand on Desired Account**
- Contact IBKR support
- Enable Thailand permissions on the account you want to use
- May require market data subscription

### Current Code Location

**File:** `data/providers.py`
- Line 71: `await self.ib.connectAsync(...)` - connects but doesn't specify account
- Uses first account from `managedAccounts()` implicitly

**File:** `tests/check_thailand_permissions.py`
- Line 20: `account = ib.managedAccounts()[0]` - uses first account

### Next Steps

1. ✅ Run `test_thailand_all_accounts.py` to test all accounts
2. Check which account has Thailand access (if any)
3. If one account works:
   - Verify it's the account you want to use
   - Ensure it's first in the managedAccounts list
   - Or modify code to use that account specifically
4. If no accounts work:
   - Thailand might not be available on any account
   - Contact IBKR to enable Thailand permissions
   - Continue using YFinance fallback
