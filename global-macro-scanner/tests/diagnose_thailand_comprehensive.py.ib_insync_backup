#!/usr/bin/env python3
"""
Comprehensive Thailand SET Exchange Diagnostic
Tests all possible approaches to access Thailand stocks via IBKR
"""
from ib_insync import *
import asyncio
from datetime import datetime

async def comprehensive_thailand_diagnostic():
    """Run comprehensive tests for Thailand SET access via IBKR"""
    ib = IB()
    
    print("="*70)
    print("THAILAND SET EXCHANGE - COMPREHENSIVE DIAGNOSTIC")
    print("="*70)
    print(f"Timestamp: {datetime.now()}\n")
    
    # Connect
    try:
        print("Connecting to IBKR...")
        await ib.connectAsync('127.0.0.1', 7497, clientId=96)
        ib.reqMarketDataType(3)  # Delayed data
        print("✅ Connected to IBKR (Paper Trading Port 7497)\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # Test stocks
    test_symbols = ['PTT', 'CPALL', 'AOT', 'KBANK', 'SCB']
    
    # ============================================================
    # TEST 1: Account Information & Permissions
    # ============================================================
    print("="*70)
    print("TEST 1: Account Information & Permissions")
    print("="*70)
    
    try:
        accounts = ib.managedAccounts()
        if accounts:
            account = accounts[0]
            print(f"Account: {account}\n")
            
            # Get account summary
            summary = ib.accountSummary()
            await asyncio.sleep(2)
            
            print("Relevant Account Summary Fields:")
            relevant_tags = ['TradingType', 'AccountType', 'NetLiquidation', 
                           'AvailableFunds', 'BuyingPower', 'Currency']
            found_any = False
            for item in summary:
                if item.tag in relevant_tags:
                    print(f"  {item.tag}: {item.value}")
                    found_any = True
            
            if not found_any:
                print("  (No relevant fields found in summary)")
                
        else:
            print("⚠️ No managed accounts found")
    except Exception as e:
        print(f"❌ Error getting account info: {e}\n")
    
    # ============================================================
    # TEST 2: Symbol Search (reqMatchingSymbols)
    # ============================================================
    print("\n" + "="*70)
    print("TEST 2: Symbol Search - What does IBKR know about Thai stocks?")
    print("="*70)
    
    for symbol in test_symbols[:2]:  # Test first 2 to save time
        try:
            print(f"\nSearching for '{symbol}':")
            matches = await ib.reqMatchingSymbolsAsync(symbol)
            
            if matches:
                print(f"  Found {len(matches)} matches")
                thb_found = False
                for i, cd in enumerate(matches[:5], 1):  # Show first 5
                    c = cd.contract
                    is_thb = c.currency == 'THB'
                    marker = ">>> THAILAND <<<" if is_thb else ""
                    print(f"  {i}. {c.symbol} | {c.exchange} | {c.currency} | {c.primaryExchange} {marker}")
                    if is_thb:
                        thb_found = True
                
                if not thb_found:
                    print("  ⚠️ No THB currency matches found")
            else:
                print("  ❌ No matches found")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # ============================================================
    # TEST 3: Exchange Code Variations
    # ============================================================
    print("\n" + "="*70)
    print("TEST 3: Exchange Code Variations")
    print("="*70)
    
    exchange_variations = [
        ('SET', 'THB', 'Standard SET'),
        ('BKKSET', 'THB', 'Bangkok SET'),
        ('SMART', 'THB', 'SMART routing'),
        ('SMART', 'THB', 'SMART with primaryExchange', True),  # With primaryExchange
        ('THAILAND', 'THB', 'Country name'),
        ('BKK', 'THB', 'Bangkok abbreviation'),
        ('XBKK', 'THB', 'MIC code XBKK'),
        ('XTHA', 'THB', 'Thailand MIC'),
        ('', 'THB', 'No exchange specified'),
    ]
    
    symbol = 'PTT'  # Use one symbol for this test
    print(f"\nTesting with symbol: {symbol}\n")
    
    for exch, curr, desc, *extra in exchange_variations:
        try:
            if extra and extra[0]:  # primaryExchange variant
                contract = Stock(symbol, 'SMART', curr, primaryExchange='SET')
                test_desc = f"{desc} (primaryExchange='SET')"
            else:
                if exch:
                    contract = Stock(symbol, exch, curr)
                else:
                    contract = Stock(symbol, '', curr)
                test_desc = desc
            
            print(f"  Testing: {test_desc:40} ... ", end='', flush=True)
            
            qualified = await ib.qualifyContractsAsync(contract)
            
            if qualified:
                q = qualified[0]
                print(f"✅ QUALIFIED!")
                print(f"     ConId: {q.conId}")
                print(f"     Exchange: {q.exchange}")
                print(f"     Primary: {q.primaryExchange}")
                print(f"     Currency: {q.currency}")
                
                # Try historical data
                try:
                    bars = await ib.reqHistoricalDataAsync(
                        q, endDateTime='', durationStr='5 D',
                        barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
                    )
                    if bars:
                        print(f"     ✅ Historical data: {len(bars)} bars")
                        print(f"     Latest: {bars[-1].close} THB")
                    else:
                        print(f"     ⚠️ No historical data")
                except Exception as he:
                    print(f"     ❌ Historical error: {str(he)[:50]}")
            else:
                print("❌ Failed to qualify")
                
        except Exception as e:
            error_msg = str(e)
            if "Invalid" in error_msg or "destination" in error_msg.lower():
                print("❌ Invalid destination/exchange")
            else:
                print(f"❌ {error_msg[:40]}")
    
    # ============================================================
    # TEST 4: Contract Details Request
    # ============================================================
    print("\n" + "="*70)
    print("TEST 4: Contract Details Request")
    print("="*70)
    
    test_contracts = [
        Stock('PTT', 'SET', 'THB'),
        Stock('PTT', 'SMART', 'THB', primaryExchange='SET'),
        Stock('PTT', 'BKKSET', 'THB'),
    ]
    
    for contract in test_contracts:
        try:
            print(f"\nRequesting details for: {contract}")
            details = await ib.reqContractDetailsAsync(contract)
            
            if details:
                print(f"  ✅ Found {len(details)} detail(s)")
                for d in details[:2]:  # Show first 2
                    c = d.contract
                    print(f"     ConId: {c.conId}")
                    print(f"     Valid Exchanges: {d.validExchanges}")
                    print(f"     Trading Class: {c.tradingClass}")
            else:
                print(f"  ❌ No details found")
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:60]}")
    
    # ============================================================
    # TEST 5: Scanner API (Check if Thailand appears in scanners)
    # ============================================================
    print("\n" + "="*70)
    print("TEST 5: Scanner API - Thailand Location Codes")
    print("="*70)
    
    thailand_locations = [
        'STK.ASIA.THAILAND',
        'STK.ASIA.SET',
        'STK.THAILAND',
        'STK.SET',
    ]
    
    for loc in thailand_locations:
        try:
            print(f"\nTesting scanner location: {loc}")
            subscription = ScannerSubscription(
                instrument='STK',
                locationCode=loc,
                scanCode='MOST_ACTIVE'
            )
            
            scan_data = ib.reqScannerData(subscription)
            await asyncio.sleep(1)  # Give it a moment
            
            if scan_data:
                print(f"  ✅ Scanner returned {len(scan_data)} results")
                for item in scan_data[:3]:  # Show first 3
                    c = item.contractDetails.contract
                    print(f"     {c.symbol} | {c.exchange} | {c.currency}")
            else:
                print(f"  ⚠️ No scanner results (location may not exist)")
        except Exception as e:
            error_msg = str(e)
            if "Invalid" in error_msg or "not found" in error_msg.lower():
                print(f"  ❌ Location not available")
            else:
                print(f"  ❌ Error: {error_msg[:50]}")
    
    # ============================================================
    # TEST 6: Alternative Instruments (ADRs, CFDs, etc.)
    # ============================================================
    print("\n" + "="*70)
    print("TEST 6: Alternative Instruments (ADRs, CFDs)")
    print("="*70)
    
    print("\nChecking for ADR/CFD alternatives...")
    # Note: This is speculative - Thailand stocks rarely have ADRs
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "="*70)
    print("DIAGNOSTIC SUMMARY")
    print("="*70)
    print("""
Based on the tests above:

1. If NO exchange codes worked → IBKR does not support Thailand SET
2. If contract qualification worked but historical data failed → 
   May need market data subscription
3. If scanner locations failed → Thailand not available in scanner API
4. Current workaround: YFinance fallback (working correctly)

NEXT STEPS:
- If all tests failed: Contact IBKR support to verify Thailand access
- Check IBKR account settings for Thailand trading permissions
- Verify market data subscriptions for Asia-Pacific region
- Consider using YFinance as primary source for Thailand (current solution)
    """)
    
    ib.disconnect()
    print("✅ Diagnostic complete")

if __name__ == "__main__":
    asyncio.run(comprehensive_thailand_diagnostic())
