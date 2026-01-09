#!/usr/bin/env python3
"""
Test Thailand SET Access on ALL IBKR Accounts
If you have multiple accounts (e.g., margin and RRSP), this tests each one separately.
"""
from ib_insync import *
import asyncio
from datetime import datetime

async def test_thailand_on_all_accounts():
    """Test Thailand SET access on each available account"""
    ib = IB()
    
    print("="*70)
    print("THAILAND SET - TEST ALL ACCOUNTS")
    print("="*70)
    print(f"Timestamp: {datetime.now()}\n")
    print("Testing if Thailand access is available on different accounts.\n")
    
    # Try to get port from config, or use defaults
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    port = int(os.getenv("IBKR_PORT", "7497"))  # Default to paper trading port
    host = os.getenv("IBKR_HOST", "127.0.0.1")
    
    try:
        print(f"Connecting to IBKR on {host}:{port}...")
        print("(Make sure IBKR TWS or IB Gateway is running with API enabled)")
        await ib.connectAsync(host, port, clientId=92)
        ib.reqMarketDataType(3)
        print("Connected successfully\n")
    except Exception as e:
        print(f"Connection failed: {e}")
        print("\nMake sure IBKR TWS or IB Gateway is running and API is enabled.")
        print("Check the port in config/settings.py (default: 7497 for paper, 7496 for live)")
        return
    
    # ============================================================
    # STEP 1: List ALL Managed Accounts
    # ============================================================
    print("="*70)
    print("STEP 1: Listing All Managed Accounts")
    print("="*70)
    
    try:
        accounts = ib.managedAccounts()
        
        if not accounts:
            print("ERROR: No managed accounts found")
            ib.disconnect()
            return
        
        print(f"Found {len(accounts)} account(s):\n")
        for i, account in enumerate(accounts, 1):
            print(f"  {i}. {account}")
        
        print("\n" + "="*70)
        print("STEP 2: Testing Thailand Access on Each Account")
        print("="*70)
        
        # Test Thailand on each account
        results = {}
        
        for account in accounts:
            print(f"\n{'='*70}")
            print(f"Testing Account: {account}")
            print(f"{'='*70}\n")
            
            # Test Thailand access for this account
            # Note: IBKR API contract qualification is not account-specific,
            # but account permissions may affect what data is available.
            # We'll test by checking if contracts qualify and if data is accessible.
            try:
                # Get account summary for this specific account to verify it's active
                summary = await ib.accountSummaryAsync(account)
                await asyncio.sleep(1)
                
                # Extract account type info
                account_type = "Unknown"
                account_currency = "Unknown"
                for item in summary:
                    if item.tag == 'AccountType':
                        account_type = item.value
                    elif item.tag == 'Currency':
                        account_currency = item.value
                
                print(f"Account Type: {account_type}")
                print(f"Currency: {account_currency}\n")
                
                # Test Thailand contract on this account
                print("Testing Thailand SET contract...")
                
                test_contracts = [
                    ('PTT', 'SET', 'THB', 'Standard SET'),
                    ('PTT', 'SMART', 'THB', 'SMART routing'),
                    ('PTT', 'SMART', 'THB', 'SMART with primaryExchange', True),
                ]
                
                account_works = False
                working_contract = None
                
                for symbol, exchange, currency, desc, *extra in test_contracts:
                    try:
                        if extra and extra[0]:
                            contract = Stock(symbol, 'SMART', currency, primaryExchange='SET')
                        else:
                            contract = Stock(symbol, exchange, currency)
                        
                        print(f"  Testing: {desc} ... ", end='', flush=True)
                        
                        qualified = await ib.qualifyContractsAsync(contract)
                        
                        if qualified:
                            q = qualified[0]
                            print(f"SUCCESS - QUALIFIED!")
                            print(f"     ConId: {q.conId}")
                            print(f"     Exchange: {q.exchange}")
                            print(f"     Primary: {q.primaryExchange}")
                            print(f"     Currency: {q.currency}")
                            
                            # Try historical data
                            try:
                                bars = await ib.reqHistoricalDataAsync(
                                    q, endDateTime='', durationStr='5 D',
                                    barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
                                )
                                if bars:
                                    print(f"     SUCCESS - Historical data: {len(bars)} bars")
                                    print(f"     Latest price: {bars[-1].close} THB")
                                    account_works = True
                                    working_contract = (symbol, exchange, currency, desc)
                                    break  # Found working method, no need to test others
                                else:
                                    print(f"     ⚠️ No historical data")
                            except Exception as he:
                                print(f"     ❌ Historical error: {str(he)[:50]}")
                        else:
                            print("FAILED - Could not qualify")
                    except Exception as e:
                        error_msg = str(e)
                        if "Invalid" in error_msg:
                            print("FAILED - Invalid destination")
                        else:
                            print(f"ERROR - {error_msg[:40]}")
                
                results[account] = {
                    'type': account_type,
                    'currency': account_currency,
                    'thailand_works': account_works,
                    'working_contract': working_contract
                }
                
                if account_works:
                    print(f"\n*** SUCCESS! Account {account} HAS Thailand access! ***")
                else:
                    print(f"\nAccount {account} does NOT have Thailand access")
                
            except Exception as e:
                print(f"ERROR testing account {account}: {e}")
                results[account] = {
                    'type': 'Error',
                    'currency': 'Error',
                    'thailand_works': False,
                    'working_contract': None,
                    'error': str(e)
                }
        
        # ============================================================
        # SUMMARY
        # ============================================================
        print("\n" + "="*70)
        print("SUMMARY - Thailand Access by Account")
        print("="*70)
        
        working_accounts = []
        non_working_accounts = []
        
        for account, result in results.items():
            if result['thailand_works']:
                working_accounts.append((account, result))
            else:
                non_working_accounts.append((account, result))
        
        if working_accounts:
            print("\n*** ACCOUNTS WITH THAILAND ACCESS ***")
            for account, result in working_accounts:
                print(f"\n  Account: {account}")
                print(f"    Type: {result['type']}")
                print(f"    Currency: {result['currency']}")
                if result['working_contract']:
                    print(f"    Working Contract: {result['working_contract'][3]}")
        else:
            print("\nNO ACCOUNTS HAVE THAILAND ACCESS")
        
        if non_working_accounts:
            print("\nACCOUNTS WITHOUT THAILAND ACCESS:")
            for account, result in non_working_accounts:
                print(f"\n  Account: {account}")
                print(f"    Type: {result['type']}")
                print(f"    Currency: {result['currency']}")
                if 'error' in result:
                    print(f"    Error: {result['error']}")
        
        # ============================================================
        # RECOMMENDATIONS
        # ============================================================
        print("\n" + "="*70)
        print("RECOMMENDATIONS")
        print("="*70)
        
        if working_accounts:
            working_account = working_accounts[0][0]
            print(f"""
*** FOUND THAILAND ACCESS! ***

Account with access: {working_account}
Working contract method: {working_accounts[0][1]['working_contract'][3] if working_accounts[0][1]['working_contract'] else 'N/A'}

NEXT STEPS:
1. Update your code to use account: {working_account}
2. Modify IBKRProvider to specify this account
3. Or ensure this account is the first in managedAccounts() list

HOW TO SPECIFY ACCOUNT:
- The IBKR API uses the first account by default
- You can reorder accounts or specify account in requests
- Check IBKR TWS/Gateway to see account order
            """)
        else:
            print("""
NO ACCOUNTS HAVE THAILAND ACCESS

This suggests:
1. Thailand SET is not available on any of your accounts
2. May need to enable Thailand in account settings
3. May need market data subscription
4. May need to contact IBKR support

Current workaround (YFinance) is working correctly.
            """)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        ib.disconnect()
        print("\nTest complete")

if __name__ == "__main__":
    asyncio.run(test_thailand_on_all_accounts())
