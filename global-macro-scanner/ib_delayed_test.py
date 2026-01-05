from ib_insync import *

def test_delayed_tsx():
    ib = IB()
    print("Connecting to IBKR...")
    try:
        ib.connect('127.0.0.1', 7497, clientId=66)
        
        # Requesting Delayed Data
        print("Switching to Market Data Type 3 (Delayed)...")
        ib.reqMarketDataType(3)

        # Define Royal Bank of Canada (RY) on TSE (Major Canadian Exchange)
        contract = Stock('RY', 'TSE', 'CAD')
        print(f"Qualifying contract for {contract.symbol}...")
        ib.qualifyContracts(contract)

        print(f"Requesting market data for {contract.symbol}...")
        ticker = ib.reqMktData(contract, '', False, False)
        
        # Wait for data to arrive
        print("Waiting for data...")
        for i in range(15):
            ib.sleep(1)
            print(f"[{i}] Ticker: Last={ticker.last}, Close={ticker.close}, Bid={ticker.bid}, Ask={ticker.ask}")
            if ticker.last > 0 or ticker.close > 0:
                print(f"✅ SUCCESS! Found data for {contract.symbol}")
                break
        else:
            print("❌ TIMEOUT: Could not fetch any price. Ticker state:")
            print(ticker)

        ib.disconnect()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_delayed_tsx()
