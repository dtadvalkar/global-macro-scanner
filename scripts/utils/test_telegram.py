import os
import requests

# === CONFIG ===
# Use environment variables for secrets; no hard-coded tokens.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

def send_test_alert():
    print("🚀 Sending test alert to Telegram...")
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ TELEGRAM_TOKEN or CHAT_ID not set in environment.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.get(url, 
                               params={
                                   'chat_id': CHAT_ID, 
                                   'text': "🔔 TEST ALERT: Your Stock Screener is connected!"
                               }, 
                               timeout=10)
        
        if response.status_code == 200:
            print("✅ SUCCESS! Check your Telegram phone app now.")
        else:
            print(f"❌ FAILED! Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == '__main__':
    send_test_alert()
