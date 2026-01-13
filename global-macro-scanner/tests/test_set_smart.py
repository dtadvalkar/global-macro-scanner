#!/usr/bin/env python3
"""Test Thailand SET with SMART routing + primaryExchange"""
from ib_async import *
import asyncio

async def test_set_smart_routing():
    ib = IB()
    
    print("Connecting to IBKR...")
    await ib.connectAsync('127.0.0.1', 7496, clientId=95)
    ib.reqMarketDataType(3)
    print("✅ Connected with delayed data\n")
    
    # Test the correct pattern from documentation
    test_stocks = ['PTT', 'CPALL', 'AOT']  # Major Thai stocks
    
    for symbol in test_stocks:
        print("="*60)
        print(f"Testing: {symbol}")
        print("="*60)
        
        # Method 1: SMART routing with primaryExchange
        print("\n1. SMART routing + primaryExchange='SET'")
        try:
            contract = Stock(symbol, 'SMART', 'THB', primaryExchange='SET')
            print(f"   Contract: {contract}")
            
            qualified = await ib.qualifyContractsAsync(contract)
            if qualified:
                q = qualified[0]
                print(f"   ✅ QUALIFIED!")
                print(f"      ConId: {q.conId}")
                print(f"      Exchange: {q.exchange}")
                print(f"      Primary: {q.primaryExchange}")
                
                # Try historical data
                try:
                    bars = await ib.reqHistoricalDataAsync(
                        q, endDateTime='', durationStr='5 D',
                        barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
                    )
                    if bars:
                        print(f"      Historical: ✅ {len(bars)} bars")
                        print(f"      Latest: {bars[-1]}")
                    else:
                        print(f"      Historical: ⚠️ No data")
                except Exception as he:
                    print(f"      Historical: ❌ {he}")
            else:
                print(f"   ❌ Failed to qualify")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Method 2: Direct SET exchange (for comparison)
        print("\n2. Direct exchange='SET' (old method)")
        try:
            contract = Stock(symbol, 'SET', 'THB')
            qualified = await ib.qualifyContractsAsync(contract)
            if qualified:
                print(f"   ✅ Qualified")
            else:
                print(f"   ❌ Failed")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}")
        
        print()
    
    ib.disconnect()
    print("="*60)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test_set_smart_routing())
