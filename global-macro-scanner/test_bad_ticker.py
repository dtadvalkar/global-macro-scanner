
import asyncio
import os
from data.providers import IBKRProvider
from ib_async import Stock

async def test_bad_ticker():
    # Use a random client_id
    import random
    client_id = random.randint(5000, 9000)
    print(f"Connecting with Client ID: {client_id}")
    
    provider = IBKRProvider('127.0.0.1', 7496, client_id)
    
    if not await provider.connect():
        print("Failed to connect.")
        return

    # Test cases
    bad_tickers = [
        'INVALIDTEST.NS', # Definitely fake
        'RCOM.NS',        # Reliance Comm (Delisted/Suspended?)
        'DHFL.NS'         # Dewan Housing (Delisted)
    ]

    for symbol in bad_tickers:
        print(f"\n--- Testing {symbol} ---")
        try:
            contract = Stock(symbol.replace('.NS', ''), 'NSE', 'INR')
            print("Qualifying contract...")
            qualified = await provider.ib.qualifyContractsAsync(contract)
            if qualified:
                print(f"[OK] Qualified: {qualified}")
            else:
                print(f"[FAIL] Qualification Failed. (No exception raised, just False)")
        except Exception as e:
            print(f"[ERROR] Exception during Qualify: {type(e).__name__}: {e}")
            
    provider.disconnect_sync()

if __name__ == "__main__":
    asyncio.run(test_bad_ticker())
