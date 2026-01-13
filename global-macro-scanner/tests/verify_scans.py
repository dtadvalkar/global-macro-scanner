from ib_async import *
import asyncio

async def test_scans():
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 7496, clientId=30)
        
        scans = [
            ('STK', 'STK.US.MAJOR', 'MOST_ACTIVE', "US Major"),
            ('STK', 'STK.NA.CANADA', 'MOST_ACTIVE', "Canada STK"),
            ('STOCK.NA', 'STK.NA.CANADA', 'MOST_ACTIVE', "Canada STOCK.NA"),
            ('STOCK.HK', 'STK.HK.NSE', 'MOST_ACTIVE', "India NSE"),
        ]
        
        for inst, loc, code, label in scans:
            try:
                print(f"Testing {label} ({loc})...")
                sub = ScannerSubscription(instrument=inst, locationCode=loc, scanCode=code)
                data = await ib.reqScannerDataAsync(sub)
                print(f"  Result: {len(data)} tickers found.")
                if data:
                    c = data[0].contractDetails.contract
                    print(f"  Example: {c.symbol} ({c.exchange})")
            except Exception as e:
                print(f"  FAILED {label}: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ib.disconnect()

if __name__ == "__main__":
    asyncio.run(test_scans())
