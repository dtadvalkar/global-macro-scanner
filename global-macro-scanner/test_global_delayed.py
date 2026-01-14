import asyncio
from ib_insync import IB, Stock
import json

async def test_exchange_data(port, exchange_configs):
    ib = IB()
    results = []
    
    print(f"\n--- Testing Port {port} ---")
    try:
        await ib.connectAsync('127.0.0.1', port, clientId=99)
        ib.reqMarketDataType(3) # Delayed
        
        for config in exchange_configs:
            symbol = config['symbol']
            exch = config['exch']
            curr = config['curr']
            
            print(f"Testing {symbol} on {exch} ({curr})...")
            contract = Stock(symbol, exch, curr)
            qualified = await ib.qualifyContractsAsync(contract)
            
            status = {
                "ticker": f"{symbol}:{exch}",
                "qualified": len(qualified) > 0,
                "fundamental_data": False,
                "snapshot_data": False,
                "error": None
            }
            
            if qualified:
                # 1. Test Fundamental Data
                try:
                    fund = await ib.reqFundamentalDataAsync(qualified[0], reportType='ReportSnapshot')
                    status["fundamental_data"] = len(fund) > 0
                except Exception as e:
                    status["error"] = str(e)
                
                # 2. Test Market Data Snapshot
                try:
                    ticker = ib.reqMktData(qualified[0], "", snapshot=True)
                    await asyncio.sleep(2) # Give it time to arrive
                    # Check for bid/ask or last price
                    status["snapshot_data"] = ticker.last > 0 or ticker.close > 0
                except Exception as e:
                    status["error"] = f"{status['error']} | {str(e)}" if status["error"] else str(e)
            
            results.append(status)
            print(f"  Qualified: {status['qualified']}, Fundamentals: {status['fundamental_data']}, Price: {status['snapshot_data']}")
            
        ib.disconnect()
    except Exception as e:
        print(f"Connection failed for port {port}: {e}")
        
    return results

async def main():
    # representative set of global exchanges
    exchange_configs = [
        {"symbol": "RELIANCE", "exch": "NSE", "curr": "INR"}, # India
        {"symbol": "TD", "exch": "TSE", "curr": "CAD"},       # Canada (TSE/TSX)
        {"symbol": "SHOP", "exch": "TSE", "curr": "CAD"},     # Canada (TSE/TSX)
        {"symbol": "CBA", "exch": "ASX", "curr": "AUD"},      # Australia
        {"symbol": "VOD", "exch": "LSE", "curr": "GBP"},      # UK
        {"symbol": "BP", "exch": "LSE", "curr": "GBP"},       # UK
        {"symbol": "Z74", "exch": "SGX", "curr": "SGD"}       # Singapore
    ]
    
    # Test Paper (7497)
    paper_results = await test_exchange_data(7497, exchange_configs)
    
    # Test Live (7496)
    live_results = await test_exchange_data(7496, exchange_configs)
    
    print("\n\n===== FINAL SUMMARY =====")
    print(f"{'Ticker':<20} | {'Paper (7497)':<20} | {'Live (7496)':<20}")
    print("-" * 65)
    
    for i in range(len(exchange_configs)):
        t = f"{exchange_configs[i]['symbol']}:{exchange_configs[i]['exch']}"
        p = paper_results[i] if i < len(paper_results) else None
        l = live_results[i] if i < len(live_results) else None
        
        p_str = f"F:{p['fundamental_data']} P:{p['snapshot_data']}" if p else "N/A"
        l_str = f"F:{l['fundamental_data']} P:{l['snapshot_data']}" if l else "N/A"
        
        print(f"{t:<20} | {p_str:<20} | {l_str:<20}")

if __name__ == "__main__":
    asyncio.run(main())
