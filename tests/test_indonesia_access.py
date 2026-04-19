#!/usr/bin/env python3
"""Quick test to verify Indonesia IDX access via IBKR"""
from ib_async import *
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_indonesia():
    ib = IB()
    
    port = int(os.getenv("IBKR_PORT", "7497"))
    host = os.getenv("IBKR_HOST", "127.0.0.1")
    
    print("="*70)
    print("TESTING INDONESIA IDX ACCESS")
    print("="*70)
    
    try:
        print(f"Connecting to IBKR on {host}:{port}...")
        await ib.connectAsync(host, port, clientId=91)
        ib.reqMarketDataType(3)
        print("Connected successfully\n")
    except Exception as e:
        print(f"Connection failed: {e}")
        return
    
    # Test Indonesia stocks
    test_symbols = [
        ('BBRI', 'IDX', 'IDR', 'Bank Rakyat Indonesia'),
        ('BBCA', 'IDX', 'IDR', 'Bank Central Asia'),
        ('TLKM', 'IDX', 'IDR', 'Telkom Indonesia'),
    ]
    
    print("Testing Indonesia IDX contracts...\n")
    
    for symbol, exchange, currency, name in test_symbols:
        print(f"Testing: {symbol} ({name})")
        print(f"  Contract: Stock('{symbol}', '{exchange}', '{currency}')")
        
        try:
            contract = Stock(symbol, exchange, currency)
            qualified = await ib.qualifyContractsAsync(contract)
            
            if qualified:
                q = qualified[0]
                print(f"  SUCCESS - QUALIFIED!")
                print(f"    ConId: {q.conId}")
                print(f"    Exchange: {q.exchange}")
                print(f"    Primary: {q.primaryExchange}")
                print(f"    Currency: {q.currency}")
                
                # Try historical data
                try:
                    bars = await ib.reqHistoricalDataAsync(
                        q, endDateTime='', durationStr='5 D',
                        barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
                    )
                    if bars:
                        print(f"    SUCCESS - Historical data: {len(bars)} bars")
                        print(f"    Latest price: {bars[-1].close} {currency}")
                    else:
                        print(f"    WARNING - No historical data")
                except Exception as he:
                    print(f"    ERROR - Historical data failed: {str(he)[:60]}")
            else:
                print(f"  FAILED - Could not qualify")
                
        except Exception as e:
            error_msg = str(e)
            if "Invalid" in error_msg:
                print(f"  FAILED - Invalid destination/exchange")
            elif "No security definition" in error_msg:
                print(f"  FAILED - No security definition found")
            else:
                print(f"  ERROR - {error_msg[:60]}")
        
        print()
    
    ib.disconnect()
    print("Test complete")

if __name__ == "__main__":
    asyncio.run(test_indonesia())
