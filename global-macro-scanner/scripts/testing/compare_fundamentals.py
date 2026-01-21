import financedatabase as fd
from ib_insync import IB, Stock
import asyncio
import pandas as pd
import json
import re
import sys

def get_fd_data(symbol_ns):
    print(f"DEBUG: Fetching FinanceDatabase data for {symbol_ns}...", flush=True)
    equities = fd.Equities()
    try:
        # Narrow by country to speed up search
        fd_data = equities.search(country='India')
        if symbol_ns in fd_data.index:
            record = fd_data.loc[symbol_ns].to_dict()
            return {k: record.get(k) for k in ['name', 'market_cap', 'sector', 'industry', 'country']}
        return {"error": "Symbol not found in FD"}
    except Exception as e:
        return {"error": f"FD Error: {e}"}

async def get_ibkr_data(symbol_ns):
    print(f"DEBUG: Connecting to IBKR for {symbol_ns}...", flush=True)
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', 7496, clientId=8888)
        symbol_only = symbol_ns.split('.')[0]
        contract = Stock(symbol_only, 'NSE', 'INR')
        qualified = await ib.qualifyContractsAsync(contract)
        
        ib_fundamental = ""
        if qualified:
            print(f"DEBUG: Requesting Fundamental Data for {symbol_ns}...", flush=True)
            ib_fundamental = await ib.reqFundamentalDataAsync(qualified[0], reportType='ReportSnapshot')
        
        ib.disconnect()
        return ib_fundamental
    except Exception as e:
        if ib.isConnected():
            ib.disconnect()
        return f"IBKR Error: {e}"

async def main():
    tickers = ['RELIANCE.NS', 'TCS.NS', '20MICRONS.NS']
    all_fd_data = {}
    
    for t in tickers:
        print(f"\nProcessing {t}...", flush=True)
        # 1. Full FinanceDatabase Dump
        equities = fd.Equities()
        fd_all = equities.search(country='India')
        if t in fd_all.index:
            all_fd_data[t] = fd_all.loc[t].to_dict()
        
        # 2. Full IBKR XML Dump
        ib_xml = await get_ibkr_data(t)
        filename = f"ibkr_raw_{t.replace('.','_')}.xml"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(ib_xml if ib_xml else "No data received")
        print(f"  - Saved IBKR XML to {filename}", flush=True)

    with open("full_fd_data.json", "w", encoding="utf-8") as f:
        json.dump(all_fd_data, f, indent=2, default=str)
    print("\n  - Saved all FinanceDatabase records to full_fd_data.json", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
