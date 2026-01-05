from ib_insync import *
from data.providers import IBKRProvider
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_mapping():
    host = os.getenv("IBKR_HOST", "127.0.0.1")
    port = int(os.getenv("IBKR_PORT", "7496"))
    client_id = 40
    
    ib_provider = IBKRProvider(host, port, client_id)
    
    tickers = ['TD.TO', 'RY.TO', 'IDEA.NS', 'AAPL']
    criteria = {'price_52w_low_pct': 1.1} # 10% from low
    
    print(f"Testing mapping for {tickers}...")
    results = await ib_provider.get_market_data_async(tickers, criteria)
    
    print(f"Results: {len(results)} matches found.")
    for r in results:
        print(f"  {r['symbol']}: Price {r['price']}, 52wLow {r['low_52w']}, Pct {r['pct_from_low']:.2f}")

if __name__ == "__main__":
    asyncio.run(test_mapping())
