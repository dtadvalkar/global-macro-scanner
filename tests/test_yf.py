from data.providers import YFinanceProvider
import asyncio

async def test_yfinance():
    provider = YFinanceProvider()
    tickers = ['TD.TO', 'RY.TO', 'RELIANCE.NS', 'AAPL']
    criteria = {'price_52w_low_pct': 1.1}
    
    print(f"Testing yfinance for {tickers}...")
    results = provider.get_market_data(tickers, criteria)
    
    print(f"Results: {len(results)} matches found.")
    for r in results:
        print(f"  {r['symbol']}: Price {r['price']}, 52wLow {r['low_52w']}, Pct {r['pct_from_low']:.2f}")

if __name__ == "__main__":
    asyncio.run(test_yfinance())
