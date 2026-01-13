from ib_insync import *
import pandas as pd
import math
import asyncio
from config import MARKETS, CRITERIA
from screener.universe import get_universe

async def scan_bulk_ibkr(tickers, criteria):
    ib = IB()
    print("Connecting to IBKR (Paper Trading Port 7497)...")
    await ib.connectAsync('127.0.0.1', 7497, clientId=30)

    print(f"🔍 Screening {len(tickers)} stocks via IBKR History Backfill...")
    
    caught = []
    
    # We'll batch requests to avoid overwhelming the API
    # IBKR handles concurrency well, but we should be respectful.
    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        tasks = []
        
        for symbol in batch:
            # Prepare contract
            # We need to map suffixes (.TO, .NS, .JK, .BK) to IBKR exchanges
            exchange = 'SMART'
            currency = 'USD'
            pure_symbol = symbol
            
            if symbol.endswith('.TO'):
                exchange = 'TSX'
                currency = 'CAD'
                pure_symbol = symbol[:-3]
            elif symbol.endswith('.NS'):
                exchange = 'NSE'
                currency = 'INR'
                pure_symbol = symbol[:-3]
            # ... add more mappings as needed
            
            contract = Stock(pure_symbol, exchange, currency)
            tasks.append(process_stock(ib, contract, symbol, criteria))
            
        # Run batch concurrently
        results = await asyncio.gather(*tasks)
        caught.extend([r for r in results if r])
        
        print(f"  Progress: {min(i + batch_size, len(tickers))}/{len(tickers)} | Catches: {len(caught)}")

    ib.disconnect()
    return caught

async def process_stock(ib, contract, full_symbol, criteria):
    try:
        # Qualify contract to get conId
        qualified = await ib.qualifyContractsAsync(contract)
        if not qualified:
            return None
        
        # Request 1 year of daily bars
        bars = await ib.reqHistoricalDataAsync(
            contract, endDateTime='', durationStr='1 Y',
            barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
        )
        
        if not bars:
            return None
            
        low_52w = min(b.low for b in bars)
        current = bars[-1].close
        pct_from_low = current / low_52w
        
        if pct_from_low <= criteria['price_52w_low_pct']:
            return {
                'symbol': full_symbol,
                'price': current,
                'low_52w': low_52w,
                'pct_from_low': pct_from_low
            }
            
    except Exception:
        pass
    return None

if __name__ == "__main__":
    # Test with a small subset of the universe
    universe = get_universe(MARKETS)
    # Take 100 random from universe for a speed test
    import random
    test_sample = random.sample(universe, min(100, len(universe)))
    
    # Relax criteria for the benchmark run
    local_criteria = CRITERIA.copy()
    local_criteria['price_52w_low_pct'] = 1.10
    
    results = asyncio.run(scan_bulk_ibkr(test_sample, local_criteria))
    
    print("\n🎣 --- IBKR BULK SCAN RESULTS ---")
    for r in results:
        print(f"CATCH: {r['symbol']} | Price: {r['price']} | {r['pct_from_low']:.1%} from 52w low")
