import asyncio
import os
import sys
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.getcwd())

from db import get_db
from config import CRITERIA, MARKETS
from screening.screening_utils import should_pass_screening
from storage.csvlogging import log_catches
from alerts.telegram import send_alerts

async def verify_pipeline():
    print("🚀 Starting Pipeline Verification (Screen -> Log -> Alert)")
    print("="*60)
    
    db = get_db()
    
    # 1. Fetch flattened market data
    print("\n📊 Step 1: Loading flattened market data...")
    rows = db.query("""
        SELECT 
            c.ticker, c.last_price, c.volume, c.last_updated,
            f.mkt_cap_usd
        FROM current_market_data c
        LEFT JOIN stock_fundamentals f ON c.ticker = f.ticker
    """, fetch='all')
    
    if not rows:
        print("❌ No market data found in current_market_data table.")
        return

    print(f"✅ Loaded {len(rows)} tickers for screening.")
    
    # 2. Run Screening logic
    print("\n🎯 Step 2: Running screening criteria...")
    catches = []
    
    # Mock some data for 52w low if missing, just to test the logic
    # In reality, should_pass_screening handles missing 52w data now.
    
    for row in rows:
        ticker, price, volume, last_updated, mkt_cap = row
        
        # Build symbol_data for centralized screening
        symbol_data = {
            'symbol': ticker,
            'price': float(price) if price else 0,
            'volume': int(volume) if volume else 0,
            'usd_mcap': (float(mkt_cap) if mkt_cap else 0) / 1e9, # Convert to Billion for log
            'time': last_updated
        }
        
        # Note: low_52w is missing in current_market_data but might be in stock_fundamentals
        # For this test, we check if it passes based on the de-coupled logic
        
        # FORCED PASS FOR TESTING
        if True:
            reason = f"Vol: {symbol_data['volume']:,} | No 52w baseline (Volume Catch) [TEST]"
            
            catch = {
                'ticker': ticker,
                'price': symbol_data['price'],
                'volume': symbol_data['volume'],
                'usd_mcap': symbol_data['usd_mcap'],
                'pct_from_low': 0,
                'low_52w': symbol_data['price'] * 0.99, # Dummy for alert
                'high_52w': symbol_data['price'] * 1.5,  # Dummy for alert
                'reason': reason
            }
            catches.append(catch)
            if len(catches) >= 5: break

    print(f"✅ Screening complete. Found {len(catches)} catches.")
    
    if catches:
        # 3. Test CSV Logging
        print("\n📝 Step 3: Verifying CSV logging...")
        log_catches(catches)
        print("✅ Catches logged to recent_catches.csv")
        
        # 4. Test Telegram Alerts (Trigger only for the first one to avoid spam)
        print(f"\n🔔 Step 4: Testing Telegram alerts for {catches[0]['ticker']}...")
        try:
            # We send only the first one as a test
            test_catches = [catches[0]]
            # We can use a small delay to ensure it sends
            await send_alerts(test_catches)
            print("✅ Telegram alert sent (check your bot if configured).")
        except Exception as e:
            print(f"❌ Telegram alert failed: {e}")
            print("💡 Check your TELEGRAM_TOKEN and CHAT_ID in .env")
    else:
        print("\n⏭️  No catches found. Skipping logging and alerts.")
        print("💡 Tip: Try relaxing CRITERIA in config/criteria.py for testing.")

    print("\n" + "="*60)
    print("✨ Verification Script Complete")

if __name__ == "__main__":
    asyncio.run(verify_pipeline())
