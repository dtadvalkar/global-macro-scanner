#!/usr/bin/env python3
"""Test Thailand SET exchange with IBKR"""
from ib_insync import *
import asyncio

async def test_set_exchange():
    ib = IB()
    
    # Connect to IBKR
    print("Connecting to IBKR...")
    await ib.connectAsync('127.0.0.1', 7496, clientId=99)
    
    # Set delayed data
    ib.reqMarketDataType(3)
    print("✅ Connected. Market data type set to 3 (Delayed)")
    
    # Test different exchange codes for Thailand stocks
    test_cases = [
        ('PTT', 'SET', 'THB'),      # Standard SET exchange code
        ('PTT', 'SMART', 'THB'),    # SMART routing with THB
        ('PTT', 'BKKSET', 'THB'),   # Bangkok SET alternative
        ('PTT', 'THAILAND', 'THB'), # Country name
    ]
    
    for symbol, exchange, currency in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {symbol} | Exchange: {exchange} | Currency: {currency}")
        print(f"{'='*60}")
        
        try:
            contract = Stock(symbol, exchange, currency)
            print(f"Contract created: {contract}")
            
            # Try to qualify
            qualified = await ib.qualifyContractsAsync(contract)
            
            if qualified:
                print(f"✅ QUALIFIED: {qualified[0]}")
                print(f"   ConId: {qualified[0].conId}")
                print(f"   Exchange: {qualified[0].exchange}")
                print(f"   Primary Exchange: {qualified[0].primaryExchange}")
                
                # Try to get historical data
                try:
                    bars = await ib.reqHistoricalDataAsync(
                        qualified[0], 
                        endDateTime='', 
                        durationStr='1 M',
                        barSizeSetting='1 day', 
                        whatToShow='MIDPOINT', 
                        useRTH=True
                    )
                    
                    if bars:
                        print(f"✅ HISTORICAL DATA: Got {len(bars)} bars")
                        print(f"   Latest: {bars[-1]}")
                    else:
                        print("⚠️ No historical data returned")
                        
                except Exception as e:
                    print(f"❌ Historical data error: {e}")
            else:
                print("❌ Contract qualification failed - no results")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    ib.disconnect()
    print("\n" + "="*60)
    print("Test complete")

if __name__ == "__main__":
    asyncio.run(test_set_exchange())
