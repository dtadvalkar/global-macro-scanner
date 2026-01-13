#!/usr/bin/env python3
"""Deep dive: Find the actual IBKR exchange code for Thailand stocks"""
from ib_insync import *
import asyncio

async def find_thailand_exchange():
    ib = IB()
    
    print("Connecting to IBKR...")
    await ib.connectAsync('127.0.0.1', 7496, clientId=97)
    ib.reqMarketDataType(3)
    print("✅ Connected with delayed data (Type 3)\n")
    
    # Strategy 1: Try to search for PTT using contract details
    print("="*60)
    print("Strategy 1: Search for PTT contract details")
    print("="*60)
    
    try:
        # Use reqMatchingSymbols to find what IBKR knows about PTT
        contracts = await ib.reqMatchingSymbolsAsync('PTT')
        
        if contracts:
            print(f"Found {len(contracts)} matching contracts for 'PTT':")
            for i, cd in enumerate(contracts[:10], 1):  # Show first 10
                c = cd.contract
                print(f"\n{i}. {c.symbol}")
                print(f"   Exchange: {c.exchange}")
                print(f"   Primary Exchange: {c.primaryExchange}")
                print(f"   Currency: {c.currency}")
                print(f"   SecType: {c.secType}")
                print(f"   Description: {cd.derivativeSecTypes}")
        else:
            print("No matching symbols found")
    except Exception as e:
        print(f"Error in matching symbols: {e}")
    
    # Strategy 2: Try common Asian exchange codes
    print("\n" + "="*60)
    print("Strategy 2: Test common Asian exchange patterns")
    print("="*60)
    
    asian_exchanges = [
        'BKKSET',   # Bangkok SET
        'THAILAND', # Country name
        'BKK',      # Bangkok abbreviation
        'XBKK',     # MIC code format
        'XTHA',     # Thailand MIC
        'SMART',    # Smart routing
    ]
    
    for exch in asian_exchanges:
        print(f"\nTrying exchange code: {exch}")
        try:
            contract = Stock('PTT', exch, 'THB')
            qualified = await ib.qualifyContractsAsync(contract)
            
            if qualified:
                q = qualified[0]
                print(f"  ✅ SUCCESS!")
                print(f"     ConId: {q.conId}")
                print(f"     Exchange: {q.exchange}")
                print(f"     Primary: {q.primaryExchange}")
                print(f"     Currency: {q.currency}")
                
                # Try to get historical data
                try:
                    bars = await ib.reqHistoricalDataAsync(
                        q, endDateTime='', durationStr='5 D',
                        barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
                    )
                    if bars:
                        print(f"     Historical: {len(bars)} bars available")
                except Exception as he:
                    print(f"     Historical error: {he}")
            else:
                print(f"  ❌ No qualification")
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:60]}")
    
    # Strategy 3: Check if Thailand is even available
    print("\n" + "="*60)
    print("Strategy 3: Query available exchanges")
    print("="*60)
    
    try:
        # This might not work but worth trying
        print("Attempting to list available exchanges...")
        # Note: IBKR doesn't have a direct API for this, but we can check
        print("(IBKR doesn't provide a direct exchange list API)")
    except Exception as e:
        print(f"Error: {e}")
    
    ib.disconnect()
    print("\n" + "="*60)
    print("Diagnostic complete")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(find_thailand_exchange())
