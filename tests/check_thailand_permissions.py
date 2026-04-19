#!/usr/bin/env python3
"""Check IBKR account permissions for Thailand"""
from ib_async import *
import asyncio

async def check_account_permissions():
    ib = IB()
    
    print("Connecting to IBKR...")
    await ib.connectAsync('127.0.0.1', 7496, clientId=94)
    ib.reqMarketDataType(3)
    print("✅ Connected\n")
    
    # Get account summary
    print("="*60)
    print("Checking Account Information")
    print("="*60)
    
    try:
        account = ib.managedAccounts()[0]
        print(f"Account: {account}\n")
        
        # Request account summary
        summary = ib.accountSummary()
        await asyncio.sleep(2)  # Wait for data
        
        # Look for market data subscriptions
        print("Account Summary (relevant fields):")
        for item in summary:
            if any(keyword in item.tag.lower() for keyword in ['market', 'data', 'permission', 'subscription']):
                print(f"  {item.tag}: {item.value}")
        
    except Exception as e:
        print(f"Error getting account info: {e}")
    
    # Test if we can at least see the contract details
    print("\n" + "="*60)
    print("Testing Contract Details Request")
    print("="*60)
    
    try:
        # Try to get contract details for a known Thai stock
        contract = Stock('PTT', 'SMART', 'THB', primaryExchange='SET')
        print(f"\nRequesting details for: {contract}")
        
        details = await ib.reqContractDetailsAsync(contract)
        
        if details:
            print(f"✅ Found {len(details)} contract detail(s):")
            for d in details:
                c = d.contract
                print(f"\n  Symbol: {c.symbol}")
                print(f"  ConId: {c.conId}")
                print(f"  Exchange: {c.exchange}")
                print(f"  Primary: {c.primaryExchange}")
                print(f"  Currency: {c.currency}")
                print(f"  Trading Class: {c.tradingClass}")
                print(f"  Valid Exchanges: {d.validExchanges}")
        else:
            print("❌ No contract details found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Final test: Try with just symbol search
    print("\n" + "="*60)
    print("Searching for 'CPALL' (another major Thai stock)")
    print("="*60)
    
    try:
        contracts = await ib.reqMatchingSymbolsAsync('CPALL')
        
        if contracts:
            print(f"Found {len(contracts)} matches:")
            for cd in contracts[:5]:
                c = cd.contract
                if c.currency == 'THB':
                    print(f"  >>> THAILAND: {c.symbol} | {c.exchange} | {c.primaryExchange}")
                else:
                    print(f"  {c.symbol} | {c.currency} | {c.primaryExchange}")
        else:
            print("No matches found")
    except Exception as e:
        print(f"Error: {e}")
    
    ib.disconnect()
    print("\n" + "="*60)
    print("Diagnostic Complete")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(check_account_permissions())
