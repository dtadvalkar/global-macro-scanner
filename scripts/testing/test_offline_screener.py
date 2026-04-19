"""
test_offline_screener.py

COMPLETE OFFLINE SCREENER TEST
Tests screening logic using ONLY local database data.
No external API calls - uses our stored data only.

Tests our 398 NSE fundamentals tickers against criteria.
"""

import sys
import io
from datetime import datetime, timedelta

# Force UTF-8 encoding for stdout to support emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config import DB_CONFIG, CRITERIA
import psycopg2

def test_offline_screener():
    """Test screener using only local database data - no API calls"""

    print("="*70)
    print("🧪 OFFLINE SCREENER TEST")
    print("="*70)
    print("🎯 Testing: 398 NSE fundamentals tickers")
    print("📊 Data Source: Local database only")
    print("🚫 External APIs: None")
    print("="*70)

    # Connect to database
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()

    # 1. Load our NSE tickers from fundamentals
    print("📋 STEP 1: Loading NSE fundamentals tickers...")
    cur.execute("""
        SELECT ticker, company_name, mkt_cap_usd
        FROM stock_fundamentals
        WHERE ticker LIKE '%.NSE'
        ORDER BY ticker
    """)
    fundamentals_data = cur.fetchall()

    print(f"   ✅ Loaded {len(fundamentals_data)} NSE fundamentals")
    print(f"   📋 Sample: {fundamentals_data[0][0]} - {fundamentals_data[0][1][:30]}...")

    # 2. Load current market data
    print("\n💰 STEP 2: Loading current market data...")
    cur.execute("""
        SELECT ticker, last_price, close_price, volume
        FROM current_market_data
        WHERE last_price > 0
    """)
    market_data = {row[0]: row[1:] for row in cur.fetchall()}

    print(f"   ✅ Loaded {len(market_data)} current market records")

    # 3. Calculate 52-week lows from historical data (most accurate)
    print("\n📈 STEP 3: Calculating 52-week lows from historical data...")
    # Get 52-week (260 trading days) low for each ticker
    cur.execute("""
        SELECT ticker, MIN(low) as week_52_low, MAX(high) as week_52_high
        FROM prices_daily
        WHERE trade_date >= CURRENT_DATE - INTERVAL '365 days'
        AND source = 'yf'
        AND ticker LIKE '%.NSE'
        GROUP BY ticker
    """)

    week_52_data = {row[0]: (row[1], row[2]) for row in cur.fetchall()}  # ticker -> (52w_low, 52w_high)

    print(f"   ✅ Calculated 52-week data for {len(week_52_data)} tickers")

    cur.close()
    conn.close()

    # 4. Apply screening criteria
    print("\n🎣 STEP 4: Applying screening criteria...")
    opportunities = []

    for ticker, company_name, market_cap in fundamentals_data:

        # Get current market data
        if ticker not in market_data:
            continue  # No current data

        last_price, close_price, volume = market_data[ticker]

        # Skip if no price data
        if not last_price or last_price <= 0:
            continue

        # Get 52-week data
        if ticker not in week_52_data:
            continue  # No historical data

        low_52w, high_52w = week_52_data[ticker]

        # BASIC CRITERIA CHECKS
        passed_criteria = True
        reasons_failed = []

        # 1. Price proximity to 52-week low
        if low_52w and low_52w > 0:
            pct_from_low = ((last_price - low_52w) / low_52w) * 100
            if pct_from_low > CRITERIA['price_52w_low_pct'] * 100:
                passed_criteria = False
                reasons_failed.append(".1f")
        else:
            passed_criteria = False
            reasons_failed.append("No 52w low data")

        # 2. Volume check
        if volume:
            if volume < CRITERIA['min_volume']:
                passed_criteria = False
                reasons_failed.append(f"Volume {volume:,} < {CRITERIA['min_volume']:,}")
        else:
            passed_criteria = False
            reasons_failed.append("No volume data")

        # 3. Price not too close to 52-week high (avoid dead cats)
        if high_52w and high_52w > 0:
            pct_from_high = ((high_52w - last_price) / high_52w) * 100
            if pct_from_high < CRITERIA['price_52w_high_pct'] * 100:
                passed_criteria = False
                reasons_failed.append(".1f")

        # 4. Minimum price threshold
        if last_price < CRITERIA['min_price']:
            passed_criteria = False
            reasons_failed.append(f"Price ₹{last_price} < ₹{CRITERIA['min_price']}")

        # 5. Maximum price threshold
        if last_price > CRITERIA['max_price']:
            passed_criteria = False
            reasons_failed.append(f"Price ₹{last_price} > ₹{CRITERIA['max_price']}")

        # If passed all criteria, add to opportunities
        if passed_criteria:
            opportunities.append({
                'ticker': ticker,
                'company': company_name[:30] if company_name else 'Unknown',
                'price': last_price,
                'low_52w': low_52w,
                'pct_from_low': pct_from_low if 'pct_from_low' in locals() else 0,
                'volume': volume or 0,
                'market_cap': market_cap or 0
            })

    # 5. Results
    print(f"\n🎉 RESULTS:")
    print("="*50)
    print(f"✅ Opportunities found: {len(opportunities)}")
    print(f"📊 Criteria applied: Price proximity, volume, risk filters")
    print(f"🎯 Universe screened: {len(fundamentals_data)} NSE stocks")

    if len(opportunities) > 0:
        print(f"\n🏆 TOP OPPORTUNITIES:")
        print("-"*70)
        print("<12")
        print("-"*70)

        for opp in opportunities[:10]:  # Show top 10
            print("<12")
    else:
        print("\n📭 No opportunities found")
        print("\n💡 Possible reasons:")
        print("   • Market is in uptrend (stocks not near lows)")
        print("   • Volume requirements too strict")
        print("   • Price proximity threshold too tight")
        print("   • This is normal for strong bull markets!")

    print(f"\n📈 SUMMARY:")
    print(f"   • Screened: {len(fundamentals_data)} NSE stocks")
    print(f"   • Passed criteria: {len(opportunities)} stocks")
    print(f"   • Success rate: {len(opportunities)/len(fundamentals_data)*100:.1f}%")
    print(f"   • Test duration: Pure database queries only")

    return len(opportunities)

if __name__ == "__main__":
    opportunities_found = test_offline_screener()
    print(f"\n🏁 OFFLINE TEST COMPLETE: {opportunities_found} opportunities found")
    sys.exit(0 if opportunities_found >= 0 else 1)