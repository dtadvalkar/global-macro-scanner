#!/usr/bin/env python3
"""
Comprehensive IBKR Market Data Access Test
Tests all potentially available markets based on connected data farms
"""
import asyncio
from data.providers import IBKRProvider
import os
from dotenv import load_dotenv
load_dotenv()

async def test_comprehensive_markets():
    """
    Test IBKR access for all potentially available markets based on data farm connections.
    From the logs, we saw these data farms connected:
    - usfarm, usfuture, cashfarm (US)
    - hfarm, jfarm (likely Japan)
    - eufarmnj, euhmds (Europe)
    """
    port = int(os.getenv('IBKR_PORT', '7496'))
    provider = IBKRProvider(host='127.0.0.1', port=port, client_id=92)

    print("="*80)
    print("COMPREHENSIVE IBKR MARKET ACCESS TEST")
    print("="*80)
    print()
    print("Testing markets based on connected data farms from logs:")
    print("- usfarm, usfuture, cashfarm (US markets)")
    print("- hfarm, jfarm (potentially Japanese markets)")
    print("- eufarmnj, euhmds (European markets)")
    print()

    # Test potentially available markets based on data farm connections
    test_markets = {
        # Already confirmed working
        'US': ('AAPL', 'SMART', 'USD'),
        'Canada': ('RY', 'TSE', 'CAD'),  # Fixed: TSE not TSX
        'India': ('RELIANCE', 'NSE', 'INR'),

        # European markets (based on eufarmnj, euhmds connections)
        'UK': ('BP', 'LSE', 'GBP'),      # London Stock Exchange
        'Germany': ('BMW', 'IBIS', 'EUR'), # XETRA/IBIS
        'France': ('MC', 'SBF', 'EUR'),   # Euronext Paris

        # Japanese markets (based on hfarm, jfarm connections)
        'Japan': ('7203', 'TSE', 'JPY'),  # Toyota on Tokyo Stock Exchange

        # Other potential markets
        'Australia': ('CBA', 'ASX', 'AUD'),  # ASX
        'Hong Kong': ('0005', 'SEHK', 'HKD'), # HSBC on SEHK
        'Singapore': ('D05', 'SGX', 'SGD'),   # DBS on SGX

        # These will fail (as expected)
        'Thailand': ('PTT', 'SET', 'THB'),   # Not supported
        'Indonesia': ('BBRI', 'IDX', 'IDR')  # Not supported
    }

    successful_markets = []
    failed_markets = []

    for market, (symbol, exchange, currency) in test_markets.items():
        print(f"\nTesting {market} ({symbol}) - Exchange: {exchange}:")
        print("-" * 50)

        try:
            # Connect if not connected
            if not provider.ib or not provider.ib.isConnected():
                print("Connecting to IBKR...")
                success = await provider.connect()
                if not success:
                    print("Connection failed")
                    continue

            from ib_async import Stock

            contract = Stock(symbol, exchange, currency)
            print(f"Contract: {contract}")

            # Try to qualify contract
            qualified = await provider.ib.qualifyContractsAsync(contract)

            if qualified:
                print("SUCCESS - Contract qualified")
                print(f"  ConId: {qualified[0].conId}")

                # Try historical data (short period for quick test)
                bars = await provider.ib.reqHistoricalDataAsync(
                    qualified[0], endDateTime='', durationStr='1 D',
                    barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
                )

                if bars and len(bars) > 0:
                    print("SUCCESS - Historical data retrieved")
                    print(f"  Bars: {len(bars)}, Latest: {bars[-1].close} {currency}")
                    successful_markets.append(market)
                else:
                    print("WARNING - Contract qualified but no recent data")
                    successful_markets.append(f"{market} (no recent data)")

            else:
                print("FAILED - Contract qualification failed")
                failed_markets.append(market)

        except Exception as e:
            error_str = str(e)
            print(f"ERROR: {error_str[:80]}...")

            if "Invalid" in error_str and "destination" in error_str:
                print("  → Exchange/market not supported by IBKR")
            elif "No market data permissions" in error_str:
                print("  → Market data permissions not enabled")
            elif "subscription" in error_str:
                print("  → Requires specific market subscription")

            failed_markets.append(market)

    # Clean up
    if provider.ib and provider.ib.isConnected():
        provider.ib.disconnect()
        print("\nIBKR connection closed")

    # Summary
    print("\n" + "="*80)
    print("MARKET ACCESS SUMMARY")
    print("="*80)

    print(f"\nSUCCESSFUL MARKETS ({len(successful_markets)}):")
    for market in successful_markets:
        print(f"  - {market}")

    print(f"\nFAILED MARKETS ({len(failed_markets)}):")
    for market in failed_markets:
        print(f"  - {market}")

    print("\n" + "="*80)
    print("RECOMMENDATIONS FOR IBKR SUPPORT")
    print("="*80)

    recommendations = []
    if 'Canada' in failed_markets:
        recommendations.append("- Enable delayed data for Canadian markets (TSE)")
    if 'UK' in failed_markets:
        recommendations.append("- Enable delayed data for UK markets (LSE)")
    if 'Germany' in failed_markets:
        recommendations.append("- Enable delayed data for German markets (IBIS/XETRA)")
    if 'France' in failed_markets:
        recommendations.append("- Enable delayed data for French markets (SBF)")
    if 'Japan' in failed_markets:
        recommendations.append("- Enable delayed data for Japanese markets (TSE)")
    if 'Australia' in failed_markets:
        recommendations.append("- Enable delayed data for Australian markets (ASX)")
    if 'Hong Kong' in failed_markets:
        recommendations.append("- Enable delayed data for Hong Kong markets (SEHK)")
    if 'Singapore' in failed_markets:
        recommendations.append("- Enable delayed data for Singapore markets (SGX)")

    if recommendations:
        print("\nRequest IBKR to enable delayed data permissions for:")
        for rec in recommendations:
            print(f"  {rec}")
    else:
        print("\nAll tested markets are working! No additional permissions needed.")

    print(f"\nKey Fix Applied: Changed Canadian exchange from 'TSX' to 'TSE'")
    print(f"   This should resolve Canadian market access if permissions are enabled.")

if __name__ == "__main__":
    asyncio.run(test_comprehensive_markets())