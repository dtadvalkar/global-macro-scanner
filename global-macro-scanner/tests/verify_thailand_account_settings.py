#!/usr/bin/env python3
"""
Verify Thailand SET Access - Account Settings & Permissions Check
The user is correct that IBKR should support delayed data for global markets.
This script checks if Thailand access needs to be enabled in account settings.
"""
from ib_async import *
import asyncio
from datetime import datetime

async def verify_thailand_account_settings():
    """Check account settings and permissions for Thailand access"""
    ib = IB()
    
    print("="*70)
    print("THAILAND SET - ACCOUNT SETTINGS & PERMISSIONS VERIFICATION")
    print("="*70)
    print(f"Timestamp: {datetime.now()}\n")
    print("Hypothesis: IBKR should support delayed data for Thailand SET")
    print("This script checks if access needs to be enabled in account settings.\n")
    
    try:
        print("Connecting to IBKR...")
        await ib.connectAsync('127.0.0.1', 7497, clientId=93)
        ib.reqMarketDataType(3)
        print("✅ Connected\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # ============================================================
    # CHECK 1: Account Summary - Trading Permissions
    # ============================================================
    print("="*70)
    print("CHECK 1: Account Trading Permissions")
    print("="*70)
    
    try:
        accounts = ib.managedAccounts()
        if accounts:
            account = accounts[0]
            print(f"Account: {account}\n")
            
            # Get account summary
            summary = ib.accountSummary()
            await asyncio.sleep(2)
            
            print("All Account Summary Fields (looking for permissions):")
            permission_keywords = ['permission', 'trading', 'market', 'data', 'subscription', 
                                 'region', 'country', 'asia', 'thailand', 'access']
            
            found_permissions = []
            for item in summary:
                tag_lower = item.tag.lower()
                if any(keyword in tag_lower for keyword in permission_keywords):
                    found_permissions.append((item.tag, item.value))
                    print(f"  {item.tag}: {item.value}")
            
            if not found_permissions:
                print("  ⚠️ No obvious permission fields found")
                print("  (This doesn't mean permissions don't exist - they may be in account settings)")
            
            # Also show some standard fields
            print("\nStandard Account Fields:")
            standard_fields = ['NetLiquidation', 'BuyingPower', 'AvailableFunds', 
                             'TotalCashValue', 'Currency']
            for item in summary:
                if item.tag in standard_fields:
                    print(f"  {item.tag}: {item.value}")
                    
        else:
            print("⚠️ No managed accounts found")
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    # ============================================================
    # CHECK 2: Market Data Subscriptions
    # ============================================================
    print("\n" + "="*70)
    print("CHECK 2: Market Data Subscriptions")
    print("="*70)
    print("Note: Market data subscriptions are typically managed in IBKR TWS/Gateway")
    print("      Account Settings > Market Data Subscriptions\n")
    
    # Try to get market data subscriptions via API
    # Note: IBKR API doesn't directly expose subscription list, but we can infer
    print("Testing if Thailand data is available (even if not subscribed):")
    
    # ============================================================
    # CHECK 3: Test Contract Qualification with Different Approaches
    # ============================================================
    print("\n" + "="*70)
    print("CHECK 3: Contract Qualification - Alternative Approaches")
    print("="*70)
    
    test_cases = [
        # Standard approaches
        ('PTT', 'SET', 'THB', 'Standard SET'),
        ('PTT', 'SMART', 'THB', 'SMART routing'),
        ('PTT', 'SMART', 'THB', 'SMART with primaryExchange', True),
        
        # Alternative exchange codes that might work
        ('PTT', 'IDX', 'THB', 'IDX (Indonesia code - test if shared)'),
        ('PTT', 'NSE', 'THB', 'NSE (India code - test if shared)'),
        
        # Try without currency
        ('PTT', 'SET', '', 'SET without currency'),
        ('PTT', 'SMART', '', 'SMART without currency'),
        
        # Try with different symbol formats
        ('PTT.BK', 'SMART', 'THB', 'Symbol with .BK suffix'),
        ('PTT', 'SET', 'USD', 'SET with USD currency'),
    ]
    
    for symbol, exchange, currency, desc, *extra in test_cases:
        try:
            if extra and extra[0]:  # primaryExchange
                contract = Stock(symbol, 'SMART', currency, primaryExchange='SET')
            else:
                if currency:
                    contract = Stock(symbol, exchange, currency)
                else:
                    contract = Stock(symbol, exchange)
            
            print(f"\n  Testing: {desc}")
            print(f"    Contract: {contract}")
            
            qualified = await ib.qualifyContractsAsync(contract)
            
            if qualified:
                q = qualified[0]
                print(f"    ✅ QUALIFIED!")
                print(f"       ConId: {q.conId}")
                print(f"       Exchange: {q.exchange}")
                print(f"       Primary: {q.primaryExchange}")
                print(f"       Currency: {q.currency}")
                print(f"       Trading Class: {q.tradingClass}")
                
                # Try historical data
                try:
                    bars = await ib.reqHistoricalDataAsync(
                        q, endDateTime='', durationStr='5 D',
                        barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
                    )
                    if bars:
                        print(f"       ✅ Historical data available: {len(bars)} bars")
                        print(f"       Latest price: {bars[-1].close}")
                    else:
                        print(f"       ⚠️ No historical data")
                except Exception as he:
                    print(f"       ❌ Historical error: {str(he)[:60]}")
            else:
                print(f"    ❌ Failed to qualify")
                
        except Exception as e:
            error_msg = str(e)
            if "Invalid" in error_msg:
                print(f"    ❌ Invalid destination/exchange")
            else:
                print(f"    ❌ Error: {error_msg[:50]}")
    
    # ============================================================
    # CHECK 4: Scanner API - Check Available Locations
    # ============================================================
    print("\n" + "="*70)
    print("CHECK 4: Scanner API - Available Asian Locations")
    print("="*70)
    print("Checking what Asian markets are available in scanner...\n")
    
    asian_locations = [
        'STK.ASIA',
        'STK.ASIA.THAILAND',
        'STK.ASIA.SET',
        'STK.ASIA.SOUTHEAST',
        'STK.THAILAND',
        'STK.SET',
        'STK.ASIA.INDONESIA',  # For comparison
        'STK.ASIA.INDIA',       # For comparison
    ]
    
    for loc in asian_locations:
        try:
            subscription = ScannerSubscription(
                instrument='STK',
                locationCode=loc,
                scanCode='MOST_ACTIVE'
            )
            
            scan_data = ib.reqScannerData(subscription)
            await asyncio.sleep(1)
            
            if scan_data:
                print(f"  ✅ {loc}: {len(scan_data)} results")
                # Show first result
                if scan_data:
                    c = scan_data[0].contractDetails.contract
                    print(f"     Example: {c.symbol} | {c.exchange} | {c.currency}")
            else:
                print(f"  ⚠️ {loc}: No results (location may not exist)")
        except Exception as e:
            error_msg = str(e)
            if "Invalid" in error_msg or "not found" in error_msg.lower():
                print(f"  ❌ {loc}: Not available")
            else:
                print(f"  ❌ {loc}: Error - {error_msg[:40]}")
    
    # ============================================================
    # CHECK 5: Compare with Working Markets
    # ============================================================
    print("\n" + "="*70)
    print("CHECK 5: Compare with Working Markets (Indonesia IDX)")
    print("="*70)
    print("Testing Indonesia IDX to see how it works (for comparison):\n")
    
    try:
        # Test Indonesia (which works)
        indo_contract = Stock('BBRI', 'IDX', 'IDR')
        print(f"Testing Indonesia: {indo_contract}")
        
        qualified = await ib.qualifyContractsAsync(indo_contract)
        if qualified:
            q = qualified[0]
            print(f"  ✅ Indonesia works!")
            print(f"     Exchange: {q.exchange}")
            print(f"     Primary: {q.primaryExchange}")
            print(f"     Currency: {q.currency}")
            
            # Try historical
            try:
                bars = await ib.reqHistoricalDataAsync(
                    q, endDateTime='', durationStr='5 D',
                    barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
                )
                if bars:
                    print(f"     ✅ Historical data: {len(bars)} bars")
            except Exception as he:
                print(f"     ⚠️ Historical: {he}")
        else:
            print(f"  ❌ Indonesia also failed (unexpected!)")
    except Exception as e:
        print(f"  ❌ Error testing Indonesia: {e}")
    
    # ============================================================
    # SUMMARY & RECOMMENDATIONS
    # ============================================================
    print("\n" + "="*70)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*70)
    print("""
FINDINGS:
1. If Thailand contracts qualified → Access is possible, may need data subscription
2. If Indonesia works but Thailand doesn't → Thailand not available via IBKR
3. If scanner shows Thailand locations → Access exists but may need enabling

NEXT STEPS IF THAILAND IS NOT AVAILABLE:
1. Check IBKR TWS/Gateway:
   - Account Settings > Market Data Subscriptions
   - Look for "Thailand" or "SET" in available subscriptions
   - Enable if found (may require subscription fee)

2. Contact IBKR Support:
   - Ask specifically about Thailand SET delayed data access
   - Verify if account type supports Thailand
   - Check if regional permissions need enabling

3. Alternative:
   - Current YFinance fallback is working correctly
   - Consider if IBKR access is critical vs. YFinance

4. Check IBKR Website:
   - Market Data Pricing page
   - Look for Thailand/SET in available markets
   - Verify subscription requirements
    """)
    
    ib.disconnect()
    print("✅ Verification complete")

if __name__ == "__main__":
    asyncio.run(verify_thailand_account_settings())
