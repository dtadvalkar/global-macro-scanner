from ib_async import *
import asyncio

async def debug_historical():
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 7496, clientId=50)
        ib.reqMarketDataType(3) # Delayed
        
        # Test RY
        c = Stock('RY', 'TSE', 'CAD')
        await ib.qualifyContractsAsync(c)
        print(f"Qualified RY: {c}")
        
        # Try different whatToShow
        for wts in ['MIDPOINT', 'TRADES', 'BID_ASK']:
            try:
                print(f"Requesting {wts} for RY...")
                bars = await ib.reqHistoricalDataAsync(
                    c, endDateTime='', durationStr='1 M',
                    barSizeSetting='1 day', whatToShow=wts, useRTH=True
                )
                print(f"  {wts} Success: {len(bars)} bars")
            except Exception as e:
                print(f"  {wts} Failed: {e}")

        # Test AAPL
        c2 = Stock('AAPL', 'SMART', 'USD')
        await ib.qualifyContractsAsync(c2)
        print(f"Qualified AAPL: {c2}")
        
        for wts in ['MIDPOINT', 'TRADES', 'BID_ASK']:
            try:
                print(f"Requesting {wts} for AAPL...")
                bars = await ib.reqHistoricalDataAsync(
                    c2, endDateTime='', durationStr='1 M',
                    barSizeSetting='1 day', whatToShow=wts, useRTH=True
                )
                print(f"  {wts} Success: {len(bars)} bars")
            except Exception as e:
                print(f"  {wts} Failed: {e}")

    finally:
        ib.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_historical())
