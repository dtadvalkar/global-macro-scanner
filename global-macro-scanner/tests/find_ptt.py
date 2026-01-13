#!/usr/bin/env python3
"""Find all PTT contracts and save to file"""
from ib_async import *
import asyncio

async def find_ptt_contracts():
    ib = IB()
    
    print("Connecting to IBKR...")
    await ib.connectAsync('127.0.0.1', 7496, clientId=96)
    ib.reqMarketDataType(3)
    print("✅ Connected\n")
    
    print("Searching for all PTT contracts...")
    contracts = await ib.reqMatchingSymbolsAsync('PTT')
    
    with open('ptt_contracts.txt', 'w') as f:
        f.write(f"Found {len(contracts)} matching contracts for 'PTT':\n")
        f.write("="*80 + "\n\n")
        
        for i, cd in enumerate(contracts, 1):
            c = cd.contract
            f.write(f"{i}. Symbol: {c.symbol}\n")
            f.write(f"   Exchange: {c.exchange}\n")
            f.write(f"   Primary Exchange: {c.primaryExchange}\n")
            f.write(f"   Currency: {c.currency}\n")
            f.write(f"   SecType: {c.secType}\n")
            f.write(f"   ConId: {c.conId}\n")
            
            # Check if this is Thailand
            if c.currency == 'THB' or 'THAI' in str(c.exchange).upper() or 'BKK' in str(c.exchange).upper():
                f.write(f"   >>> THAILAND CANDIDATE <<<\n")
            
            f.write("\n")
    
    print(f"✅ Saved {len(contracts)} contracts to ptt_contracts.txt")
    
    # Now try to qualify the Thailand ones
    print("\nTesting Thailand-specific contracts...")
    thailand_contracts = [cd.contract for cd in contracts if cd.contract.currency == 'THB']
    
    if thailand_contracts:
        print(f"Found {len(thailand_contracts)} contracts with THB currency")
        for tc in thailand_contracts:
            print(f"\nTrying: {tc.symbol} | {tc.exchange} | {tc.primaryExchange} | {tc.currency}")
            try:
                qualified = await ib.qualifyContractsAsync(tc)
                if qualified:
                    print(f"  ✅ Qualified! ConId: {qualified[0].conId}")
                else:
                    print(f"  ❌ Failed to qualify")
            except Exception as e:
                print(f"  ❌ Error: {e}")
    else:
        print("No THB currency contracts found")
    
    ib.disconnect()
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(find_ptt_contracts())
