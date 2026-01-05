from ib_insync import *
import asyncio

async def test_qualify():
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 7496, clientId=70)
        
        tickers = [
            ('TD', 'TSE', 'CAD'),
            ('RY', 'TSE', 'CAD'),
            ('TD', 'TSX', 'CAD'),
            ('RY', 'TSX', 'CAD'),
            ('RELIANCE', 'NSE', 'INR'),
        ]
        
        for sym, exch, curr in tickers:
            c = Stock(sym, exch, curr)
            q = await ib.qualifyContractsAsync(c)
            print(f"{sym}@{exch}: {'SUCCESS' if q else 'FAILED'}")
            if q:
                print(f"  Qualified: {q[0].conId} on {q[0].exchange}")
                
    finally:
        ib.disconnect()

if __name__ == "__main__":
    asyncio.run(test_qualify())
