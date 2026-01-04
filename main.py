import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime
import schedule
import logging

# === CONFIG ===
TELEGRAM_TOKEN = "8422797197:AAFpQxUsKpvPlCc1MCi1DgbsRRCMVK8w4Wg"  # From @BotFather
CHAT_ID = "YOUR_CHAT_ID_HERE"  # From @userinfobot
TEST_MODE = True  # Set False for production
CRITERIA = {
    'price_52w_low_pct': 1.03,  # Within 3% of 52w low
    'min_market_cap': 5e9  # $5B+
}


# === CORE FUNCTIONS ===
def send_telegram(message):
    """Send alert to your phone"""
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(f"📱 TELEGRAM WOULD SEND: {message}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url,
                     params={
                         'chat_id': CHAT_ID,
                         'text': message
                     },
                     timeout=5)
        print("✅ Telegram sent!")
    except Exception as e:
        print(f"❌ Telegram error: {e}")


def get_nse_universe():
    """Get NSE stocks or fallback test list"""
    try:
        nse_df = pd.read_csv(
            'https://archives.nseindia.com/content/equities/EQUITY_L.csv')
        symbols = [f"{s}.NS"
                   for s in nse_df['SYMBOL'][:200]]  # Top 200 for speed
        print(f"✅ Loaded {len(symbols)} NSE stocks")
        return symbols
    except:
        print("⚠️ NSE list failed, using test stocks")
        return ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS']


def screen_universe():
    """Main screening logic - your fishing net"""
    print(f"\n🕐 {datetime.now()} | Scanning NSE/IDX/SET universe...")
    print(
        f"🎯 Criteria: 52w low ≤{CRITERIA['price_52w_low_pct']*100:.0f}%, mcap ≥${CRITERIA['min_market_cap']/1e9:.0f}B"
    )

    # Your target markets
    test_stocks = get_nse_universe()
    idx_stocks = ['BBCA.JK', 'BBRI.JK', 'TLKM.JK']
    set_stocks = ['PTT.BK', 'CPALL.BK', 'ADVANC.BK']

    all_tickers = test_stocks + idx_stocks + set_stocks
    sample_size = min(50, len(all_tickers))  # Fast for testing

    sample_tickers = pd.Series(all_tickers).sample(sample_size).tolist()
    caught = []

    print(f"🔍 Scanning {len(sample_tickers)} stocks...")

    for i, symbol in enumerate(sample_tickers, 1):
        try:
            print(f"  {i}/{len(sample_tickers)} {symbol}...", end=" ")
            stock = yf.Ticker(symbol)
            hist = stock.history(period='1y')
            info = stock.info

            if len(hist) > 250 and info.get('marketCap',
                                            0) > CRITERIA['min_market_cap']:
                low_52w = hist['Low'].min()
                current = hist['Close'][-1]
                pct_from_low = current / low_52w

                print(
                    f"mcap ${info['marketCap']/1e9:.1f}B, {pct_from_low:.1%} from 52wL"
                )

                if pct_from_low <= CRITERIA['price_52w_low_pct']:
                    catch = {
                        'symbol': symbol,
                        'price': current,
                        'low_52w': low_52w,
                        'mcap': info['marketCap'] / 1e9,
                        'pct_from_low': pct_from_low,
                        'time': datetime.now()
                    }
                    caught.append(catch)
                    print(f"🎣 **CAUGHT {symbol}!**")

                    # Log to CSV
                    log_catch(catch)

                    if not TEST_MODE:
                        send_telegram(
                            f"🎣 CAUGHT {symbol}\n💰 ${current:.2f} (52wL: ${low_52w:.2f})\n📊 {pct_from_low:.1%} from low"
                        )
            else:
                print("skipped (small cap/no data)")

        except Exception as e:
            print(f"error: {str(e)[:30]}")

    print(f"\n✅ Scan complete: {len(caught)}/{len(sample_tickers)} caught")
    return caught


def log_catch(catch):
    """Save to CSV for Excel analysis"""
    df = pd.DataFrame([catch])
    try:
        df.to_csv('recent_catches.csv',
                  mode='a',
                  header=not os.path.exists('recent_catches.csv'),
                  index=False)
    except:
        df.to_csv('recent_catches.csv', mode='w', index=False)
    print(f"   📊 Saved to recent_catches.csv")


# === MAIN EXECUTION ===
if __name__ == '__main__':
    print("🌍 Global Stock Screener - NSE/IDX/SET Fishing Net")
    print(
        f"📱 Token: {'✅ Set' if TELEGRAM_TOKEN != 'YOUR_BOT_TOKEN_HERE' else '❌ MISSING'}"
    )
    print(
        f"📱 ChatID: {'✅ Set' if CHAT_ID != 'YOUR_CHAT_ID_HERE' else '❌ MISSING'}"
    )
    print(f"🔍 TEST_MODE: {TEST_MODE}")
    print("-" * 60)

    # Single test run with full visibility
    results = screen_universe()

    if results:
        print(f"\n🎉 SUCCESS! Caught {len(results)} stocks:")
        for catch in results:
            print(
                f"  → {catch['symbol']}: ${catch['price']:.2f} ({catch['pct_from_low']:.1%} from 52wL)"
            )
    else:
        print(
            "\n⏳ No catches this scan. Criteria too tight? Edit CRITERIA above."
        )
        print(
            "💡 Try: CRITERIA['price_52w_low_pct'] = 1.10  # 10% from 52w low")

    print("\n📋 Check recent_catches.csv in Excel for full results")
    print(
        "🚀 Set TEST_MODE=False + valid Telegram credentials for 24/7 production"
    )
