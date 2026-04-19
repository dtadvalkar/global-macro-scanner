import requests
import asyncio
from config import TELEGRAM

async def send_alert(catch):
    """Send single catch alert asynchronously"""
    # Ensure all required keys have defaults to avoid KeyError
    symbol = catch.get('symbol', catch.get('ticker', 'UNKNOWN'))
    price = catch.get('price', 0)
    low_52w = catch.get('low_52w', 0)
    pct_from_low = catch.get('pct_from_low', 0)
    usd_mcap = catch.get('usd_mcap')
    reason = catch.get('reason', '')

    mcap_info = f"\n🏦 ${usd_mcap:.1f}B USD" if usd_mcap is not None else ""
    
    # Format the message nicely
    message = (
        f"🎣 *CAUGHT {symbol}*\n"
        f"💰 *${price:,.2f}* (52wL: ${low_52w:,.2f})\n"
        f"📊 {pct_from_low:.1%} from low\n"
        f"🎯 {reason}"
        f"{mcap_info}"
    )
    
    if not TELEGRAM['token'] or not TELEGRAM['chat_id']:
        print("⚠️ Telegram not configured (TOKEN or CHAT_ID missing). Skipping alert.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM['token']}/sendMessage"
    payload = {
        'chat_id': TELEGRAM['chat_id'],
        'text': message,
        'parse_mode': 'Markdown'
    }

    try:
        # Run synchronous requests in a thread to keep the event loop moving
        response = await asyncio.to_thread(requests.post, url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Telegram alert sent for {symbol}!")
        else:
            print(f"❌ Telegram API Error ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Telegram connection error: {e}")

async def send_alerts(catches):
    """Send all catches asynchronously"""
    if not catches:
        return
        
    print(f"🔔 Sending {len(catches)} Telegram alerts...")
    # Send sequentially to avoid triggering Telegram rate limits
    for catch in catches:
        await send_alert(catch)
        await asyncio.sleep(0.5) # Anti-spam delay
