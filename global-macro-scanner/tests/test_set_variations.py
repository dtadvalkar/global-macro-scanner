#!/usr/bin/env python3
"""Test more Thailand SET exchange variations"""
from ib_async import *
import asyncio

async def test_set_variations():
    ib = IB()
    
    print("Connecting to IBKR...")
    await ib.connectAsync('127.0.0.1', 7496, clientId=98)
    ib.reqMarketDataType(3)
    print("✅ Connected\n")
    
    # More comprehensive test cases based on IBKR exchange naming
    test_cases = [
        ('PTT', 'SET', 'THB'),          # Standard
        ('PTT', 'BKKSET', 'THB'),       # Bangkok SET
        ('PTT', 'SMART', 'THB'),        # Smart routing
        ('CPALL', 'SET', 'THB'),        # Different stock
        ('CPALL', 'BKKSET', 'THB'),     
        # Try without currency specification
        ('PTT', 'SET', ''),
        ('PTT', 'BKKSET', ''),
    ]
    
    for symbol, exchange, currency in test_cases:
        curr_str = currency if currency else 'None'
        print(f"Testing: {symbol:8} | {exchange:10} | {curr_str:5} ... ", end='')
        
        try:
            contract = Stock(symbol, exchange, currency) if currency else Stock(symbol, exchange)
            qualified = await ib.qualifyContractsAsync(contract)
            
            if qualified:
                q = qualified[0]
                print(f"✅ ConId:{q.conId} | PrimaryExch:{q.primaryExchange}")
            else:
                print("❌ No qualification")
                
        except Exception as e:
            error_msg = str(e)[:50]
            print(f"❌ {error_msg}")
    
    ib.disconnect()
    print("\nTest complete")

if __name__ == "__main__":
    asyncio.run(test_set_variations())
