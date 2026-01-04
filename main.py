import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime
import schedule
import logging

# === CONFIG ===
TELEGRAM_TOKEN = "8422797197:AAFpQxUsKpvPlCc1MCi1DgbsRRCMVK8w4Wg"
CHAT_ID = "YOUR_CHAT_ID"
TEST_MODE = True
CRITERIA = {'price_52w_low_pct': 1.03, 'min_market_cap': 5e9}

# === CORE FUNCTIONS ===
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.get(url, params={'chat_id': CHAT_ID, 'text': message})

def get_nse_universe():
    # NSE full list or sample top 500
    try:
        nse_df = pd.read_csv('https://archives.nseindia.com/content/equities/EQUITY_L.csv')
        return [f"{s}.NS" for s in nse_df['SYMBOL'][:500]]
    except:
        return ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']

def screen_universe():
    print(f"🕐 {datetime.now()} | Scanning NSE/IDX/SET...")
    tickers = get_nse_universe() + ['BBCA.JK', 'PTT.BK']
    sample = pd.Series(tickers).sample(min(100, len(tickers)))

    caught = []
    for symbol in sample:
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period='1y')
            info = stock.info

            if len(hist) > 250 and info.get('marketCap', 0) > CRITERIA['min_market_cap']:
                low_52w = hist['Low'].min()
                current = hist['Close'][-1]

                if current <= low_52w * CRITERIA['price_52w_low_pct']:
                    catch = {
                        'symbol': symbol, 'price': current, 
                        'low_52w': low_52w, 'mcap': info['marketCap']/1e9,
                        'time': datetime.now()
                    }
                    caught.append(catch)
                    log_catch(catch)

        except Exception as e:
            if TEST_MODE: print(f"Skip {symbol}: {e}")

    if caught and not TEST_MODE:
        message = "🎣 NET HAUL:\n" + "\n".join([f"{c['symbol']}: ${c['price']:.2f}" for c in caught])
        send_telegram(message)

    return caught

# === STORAGE ===
def log_catch(catch):
    df = pd.DataFrame([catch])
    df.to_csv('recent_catches.csv', mode='a', header=False, index=False)
    print(f"🎣 CAUGHT {catch['symbol']}: ${catch['price']:.2f}")

# === SCHEDULING ===
schedule.every(30).minutes.do(screen_universe)

if TEST_MODE:
    print("🔍 TEST MODE: Detailed output")
    results = screen_universe()
    print(f"Caught {len(results)} stocks")
else:
    while True:
        schedule.run_pending()
        time.sleep(60)
