import yfinance as yf
from datetime import datetime

def verify_ticker(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period='1y')
        if hist.empty:
            print(f"{symbol}: No data found.")
            return

        low_52w = hist['Low'].min()
        current = hist['Close'].iloc[-1]
        pct_from_low = (current / low_52w) - 1
        
        print(f"Ticker: {symbol}")
        print(f"  Current Price: {current:.2f}")
        print(f"  52w Low:       {low_52w:.2f}")
        print(f"  Proximity:     {pct_from_low*100:.2f}% from low")
        
        if pct_from_low <= 0.01:
            print("  ✅ Match! Within 1% of 52w low.")
        else:
            print("  ❌ No match. Outside 1% range.")
            
    except Exception as e:
        print(f"Error checking {symbol}: {e}")

if __name__ == "__main__":
    # DHARAN.NS was found in the previous run
    verify_ticker("DHARAN.NS")
