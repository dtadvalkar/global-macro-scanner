import yfinance as yf
from ib_async import *
import asyncio

async def verify_suffixes():
    print("--- YFINANCE TEST ---")
    # Test TD (Ambiguous: Toronto or NYSE?)
    td_raw = yf.Ticker("TD")
    td_to = yf.Ticker("TD.TO")
    
    print(f"yf 'TD' industry: {td_raw.info.get('industry', 'N/A')}")
    print(f"yf 'TD.TO' industry: {td_to.info.get('industry', 'N/A')}")
    
    # Test Reliance (Definitely needs .NS)
    rel_raw = yf.Ticker("RELIANCE")
    rel_ns = yf.Ticker("RELIANCE.NS")
    
    # yfinance often returns empty for international without suffix
    print(f"yf 'RELIANCE' history empty: {rel_raw.history(period='1d').empty}")
    print(f"yf 'RELIANCE.NS' history empty: {rel_ns.history(period='1d').empty}")

    print("\n--- IBKR TEST ---")
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 7496, clientId=85)
        # IBKR works with separate Symbol and Exchange fields
        c = Stock('TD', 'TSE', 'CAD')
        q = await ib.qualifyContractsAsync(c)
        print(f"IBKR 'TD' @ 'TSE' Qualified: {'SUCCESS' if q else 'FAILED'}")
        if q: print(f"  Qualified symbol: {q[0].symbol}, Exchange: {q[0].exchange}")
    except Exception as e:
        print(f"IBKR Error: {e}")
    finally:
        ib.disconnect()

if __name__ == "__main__":
    asyncio.run(verify_suffixes())
