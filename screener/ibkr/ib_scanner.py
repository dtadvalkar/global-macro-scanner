from ib_async import *
import pandas as pd

def get_ibkr_scanned_stocks():
    ib = IB()
    print("Connecting to IBKR...")
    try:
        print(f"Attempting to connect to 127.0.0.1:7496...")
        ib.connect('127.0.0.1', 7496, clientId=55)
        
        # Enable delayed data (3)
        print("Enabling delayed data (Type 3)...")
        ib.reqMarketDataType(3)
        
        # Define the Scanner Subscription
        # We look for:
        # - Instrument: STOCK
        # - Location: STK.US.MAJOR (Major US Exchanges) or STK.TSX (Canada)
        # - Scan Code: TOP_PERC_GAIN, HOT_BY_VOLUME, or 52W_LOW
        
        print("\n🎣 Fishing for MOST_ACTIVE stocks in Canada (TSE)...")
        subscription = ScannerSubscription(
            instrument='STOCK.NA', 
            locationCode='STK.NA.CANADA', 
            scanCode='MOST_ACTIVE'
        )
        
        # Get the scan results
        # filterOptions can include things like Market Cap if the server supports it
        scan_data = ib.reqScannerData(subscription)
        
        if not scan_data:
            print("⚠️ No scanner data returned. Check if IBKR has active scanners for this location.")
            return []

        results = []
        for item in scan_data:
            contract = item.contractDetails.contract
            results.append({
                'symbol': contract.symbol,
                'exchange': contract.exchange,
                'rank': item.rank
            })
            
        df = pd.DataFrame(results)
        print(f"\n✅ IBKR found {len(df)} candidates near 52w lows.")
        print(df.head(10))
        
        ib.disconnect()
        return results

    except Exception as e:
        print(f"❌ Error during scan: {e}")
        return []

if __name__ == "__main__":
    get_ibkr_scanned_stocks()
