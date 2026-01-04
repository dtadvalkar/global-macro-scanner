import os
import requests

# === CONFIG ===
# Hardcoding for a quick test based on your main.py
TELEGRAM_TOKEN = "8422797197:AAFpQxUsKpvPlCc1MCi1DgbsRRCMVK8w4Wg"
CHAT_ID = "8095552564"

def send_test_alert():
    print(f"🚀 Sending test alert to Telegram...")
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
