import requests
from config import TELEGRAM

def send_alert(catch):
    """Send single catch alert"""
    mcap_info = f"\n🏦 ${catch['usd_mcap']:.1f}B USD" if 'usd_mcap' in catch else ""
    message = (f"🎣 CAUGHT {catch['symbol']}\n"
              f"💰 ${catch['price']:.2f} (52wL: ${catch['low_52w']:.2f})\n"
              f"📊 {catch['pct_from_low']:.1%} from low"
              f"{mcap_info}")
    
    url = f"https://api.telegram.org/bot{TELEGRAM['token']}/sendMessage"
    try:
        requests.get(url, params={'chat_id': TELEGRAM['chat_id'], 'text': message}, timeout=5)
        print("✅ Telegram alert sent!")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def send_alerts(catches):
    """Send all catches"""
    for catch in catches:
        send_alert(catch)
