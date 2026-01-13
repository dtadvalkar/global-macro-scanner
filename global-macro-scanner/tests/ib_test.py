from ib_async import *
import math

def test_connection():
    ib = IB()
    print("Connecting to IBKR (TWS or Gateway)...")
    try:
        # TWS Paper Trading is 7497
        ib.connect('127.0.0.1', 7497, clientId=99)
        print("✅ Successfully connected to IBKR!")
        
        # Look up a sample contract and check for data
        print("\n🔍 Verifying contract lookup (AAPL)...")
        stock = Stock('AAPL', 'SMART', 'USD')
        details = ib.qualifyContracts(stock)
        print(f"Contract Details found for {stock.symbol}")
        
        print("\n📉 Requesting market data snapshot with 52w low/high...")
        # Tick type 165 = Misc Stats (includes 52w low/high)
        # We can also use specific generic tick tags: 165,456,461,462
        [ticker] = ib.reqTickers(stock)
        print(f"Ticker: {ticker.contract.symbol}")
        print(f"52w High (from ticker): {ticker.low13week}") # ib_insync maps these
        print(f"52w Low (from ticker): {ticker.low52week}")
        
        if math.isnan(ticker.low52week):
            print("⚠️ 52w Low is NaN. Trying reqHistoricalData backfill...")
            bars = ib.reqHistoricalData(stock, '', '1 Y', '1 day', 'MIDPOINT', True)
            if bars:
                 low = min(b.low for b in bars)
                 print(f"✅ Calculated 52w Low from history: {low}")
        
        ib.disconnect()
        print("\nDisconnected.")
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")

if __name__ == "__main__":
    test_connection()
