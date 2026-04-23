#!/usr/bin/env python3
"""
IBKR Market Data Access Test — confirms which exchanges deliver free delayed data via API.

Usage:
    python test_ibkr_market_access_final.py                         # Test all markets
    python test_ibkr_market_access_final.py --exchanges NSE         # Test only NSE
    python test_ibkr_market_access_final.py --exchanges NSE,ASX     # Test multiple

Free via IBKR (no subscription): NSE, BSE, ASX, SGX, SEHK, LSE, JSE, TADAWUL
Needs paid subscription:         SMART (US), TSE (Canada), IBIS (Germany), SBF (France), TSEJ (Japan)
Not in IBKR (yfinance-only):     KSE (Korea), TWSE (Taiwan), BOVESPA (Brazil), Bursa (Malaysia),
                                  SET (Thailand), IDX (Indonesia)

Symbol format notes:
  SEHK: strip leading zeros  — 0005 -> 5
  LSE:  trailing period       — BP   -> BP.
  TSEJ: Tokyo Stock Exchange  — NOT TSE (that is Toronto/Canada)

Last verified: 2026-04-22 via live TWS diagnostics.
"""
import asyncio
from datetime import datetime
import os
import argparse
from dotenv import load_dotenv
from data.providers import IBKRProvider

load_dotenv()

class MarketAccessTester:
    def __init__(self):
        self.provider = None
        self.results = {}

    async def initialize(self):
        """Initialize IBKR connection"""
        port = int(os.getenv('IBKR_PORT', '7496'))
        self.provider = IBKRProvider(host='127.0.0.1', port=port, client_id=95)

    async def test_market(self, market_name, symbol, exchange, currency, expected_suffix):
        """Test a specific market and return definitive results"""
        print(f"\n{'='*60}")
        print(f"TESTING: {market_name} ({symbol})")
        print(f"{'='*60}")

        result = {
            'market': market_name,
            'symbol': symbol,
            'exchange': exchange,
            'currency': currency,
            'timestamp': datetime.now().isoformat(),
            'contract_qualified': False,
            'historical_data_available': False,
            'latest_price': None,
            'bars_count': 0,
            'error_message': None,
            'status': 'UNKNOWN'
        }

        try:
            # Test contract qualification
            print(f"Testing contract qualification...")
            from ib_async import Stock

            contract = Stock(symbol, exchange, currency)
            print(f"  Contract: {contract}")

            qualified = await self.provider.ib.qualifyContractsAsync(contract)

            if qualified:
                result['contract_qualified'] = True
                result['status'] = 'CONTRACT_QUALIFIED'
                print(f"  SUCCESS: Contract qualified (ConId: {qualified[0].conId})")

                # Test historical data
                print(f"Testing historical data retrieval...")
                try:
                    # For delayed frozen data (Type 4), limit to 16 minutes ago to avoid permission issues
                    from datetime import timedelta
                    end_time = datetime.utcnow() - timedelta(minutes=16)
                    end_datetime_str = end_time.strftime('%Y%m%d %H:%M:%S')

                    bars = await self.provider.ib.reqHistoricalDataAsync(
                        qualified[0], endDateTime=end_datetime_str, durationStr='1 D',
                        barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
                    )

                    if bars and len(bars) > 0:
                        result['historical_data_available'] = True
                        result['latest_price'] = bars[-1].close
                        result['bars_count'] = len(bars)
                        result['status'] = 'FULL_ACCESS'
                        print(f"  SUCCESS: Historical data available ({len(bars)} bars)")
                        print(f"  Latest price: {bars[-1].close} {currency}")
                    else:
                        result['status'] = 'NO_RECENT_DATA'
                        print(f"  WARNING: Contract qualified but no recent historical data")
                        print(f"  This may indicate market is closed or permissions issue")

                except Exception as hist_error:
                    error_str = str(hist_error)
                    result['error_message'] = error_str
                    result['status'] = 'HISTORICAL_DATA_FAILED'
                    print(f"  ERROR: Historical data failed - {error_str[:100]}...")

                    # Check for specific permission errors
                    if "No market data permissions" in error_str:
                        result['status'] = 'PERMISSIONS_NEEDED'
                        print(f"  DIAGNOSIS: Market data permissions not enabled for {exchange}")
                    elif "subscription" in error_str.lower():
                        result['status'] = 'SUBSCRIPTION_NEEDED'
                        print(f"  DIAGNOSIS: Requires specific market subscription")

            else:
                result['status'] = 'CONTRACT_FAILED'
                result['error_message'] = "Contract qualification failed"
                print(f"  FAILED: Contract qualification failed")
                print(f"  DIAGNOSIS: {exchange} exchange not supported or symbol not found")

        except Exception as e:
            error_str = str(e)
            result['error_message'] = error_str
            result['status'] = 'EXCEPTION_OCCURRED'
            print(f"  EXCEPTION: {error_str[:100]}...")

            # Check for specific errors
            if "Invalid" in error_str and "destination" in error_str:
                result['status'] = 'EXCHANGE_NOT_SUPPORTED'
                print(f"  DIAGNOSIS: {exchange} exchange not supported by IBKR")
            elif "No security definition" in error_str:
                result['status'] = 'SYMBOL_NOT_FOUND'
                print(f"  DIAGNOSIS: Symbol {symbol} not found on {exchange}")

        self.results[market_name] = result
        return result

    def print_final_report(self):
        """Print comprehensive final report"""
        print(f"\n{'='*100}")
        print("FINAL IBKR MARKET ACCESS REPORT")
        print(f"{'='*100}")
        print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"IBKR Account: U11571501")
        print()

        # Group results by status
        status_groups = {
            'FULL_ACCESS': [],
            'CONTRACT_QUALIFIED': [],
            'PERMISSIONS_NEEDED': [],
            'EXCHANGE_NOT_SUPPORTED': [],
            'CONTRACT_FAILED': [],
            'NO_RECENT_DATA': [],
            'EXCEPTION_OCCURRED': [],
            'UNKNOWN': []
        }

        for market, result in self.results.items():
            status_groups[result['status']].append((market, result))

        # Print summary
        print("SUMMARY BY STATUS:")
        print("-" * 50)
        for status, markets in status_groups.items():
            if markets:
                print(f"{status}: {len(markets)} markets")
                for market, result in markets:
                    price_info = f" (Latest: {result['latest_price']} {result['currency']})" if result['latest_price'] else ""
                    print(f"  - {market}{price_info}")

        print(f"\n{'='*100}")
        print("DETAILED RESULTS:")
        print(f"{'='*100}")

        for market, result in self.results.items():
            print(f"\n{market}:")
            print(f"  Status: {result['status']}")
            print(f"  Symbol: {result['symbol']}")
            print(f"  Exchange: {result['exchange']}")
            print(f"  Contract Qualified: {result['contract_qualified']}")
            print(f"  Historical Data: {result['historical_data_available']}")
            if result['latest_price']:
                print(f"  Latest Price: {result['latest_price']} {result['currency']}")
            if result['error_message']:
                print(f"  Error: {result['error_message'][:100]}...")
            print(f"  Tested: {result['timestamp']}")

        # Generate IBKR support recommendations
        print(f"\n{'='*100}")
        print("IBKR SUPPORT RECOMMENDATIONS:")
        print(f"{'='*100}")

        permissions_needed = [m for m, r in self.results.items() if r['status'] == 'PERMISSIONS_NEEDED']
        exchange_not_supported = [m for m, r in self.results.items() if r['status'] == 'EXCHANGE_NOT_SUPPORTED']

        if permissions_needed:
            print("\nMARKETS NEEDING PERMISSION ENABLEMENT:")
            for market in permissions_needed:
                result = self.results[market]
                print(f"  - {market} ({result['exchange']}) - Contract qualifies, permissions needed")

        if exchange_not_supported:
            print("\nMARKETS NOT SUPPORTED BY IBKR:")
            for market in exchange_not_supported:
                result = self.results[market]
                print(f"  - {market} ({result['exchange']}) - Exchange not supported")

        if not permissions_needed and not exchange_not_supported:
            print("\nCONCLUSION: All tested markets are either working or have contract qualification issues.")
            print("No definitive permission issues found that require IBKR support intervention.")

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test IBKR market access for specific exchanges')
    parser.add_argument('--exchanges', type=str,
                       help='Comma-separated list of exchanges to test (e.g., NSE,SMART,ASX). If not provided, tests all exchanges.')
    args = parser.parse_args()

    # Initialize tester
    tester = MarketAccessTester()
    await tester.initialize()

    # Connect to IBKR
    print("Connecting to IBKR...")
    success = await tester.provider.connect()
    if not success:
        print("FAILED to connect to IBKR. Cannot proceed with testing.")
        return

    print("Connected successfully. Starting comprehensive market access tests...")
    print("This test will provide CONCLUSIVE evidence for IBKR support calls.")

    # Market list — updated 2026-04-22 after live TWS diagnostics.
    # Symbol format rules:
    #   SEHK: strip leading zeros (0005 -> 5, 0700 -> 700)
    #   LSE:  add trailing period (BP -> BP., HSBA -> HSBA.)
    #   TSEJ: Tokyo Stock Exchange Japan (NOT TSE which is Toronto/Canada)
    markets_to_test = [
        # --- FREE via IBKR Type 3 Delayed (confirmed 2026-04-22) ---
        ("India NSE",        "RELIANCE", "NSE",     "INR"),
        ("India BSE",        "HDFCBANK", "BSE",     "INR"),
        ("Australia",        "CBA",      "ASX",     "AUD"),
        ("Singapore",        "D05",      "SGX",     "SGD"),
        ("Hong Kong",        "5",        "SEHK",    "HKD"),   # HSBC; strip leading zero
        ("UK",               "BP.",      "LSE",     "GBP"),   # trailing period required
        ("South Africa",     "NPN",      "JSE",     "ZAR"),
        ("Saudi Arabia",     "2222",     "TADAWUL", "SAR"),   # Aramco; Vision 2030 mandate

        # --- IBKR subscription required (contracts qualify, Error 162 on data) ---
        ("US",               "AAPL",    "SMART",   "USD"),
        ("Canada",           "RY",      "TSE",     "CAD"),
        ("Germany",          "BMW",     "IBIS",    "EUR"),
        ("France",           "MC",      "SBF",     "EUR"),
        ("Japan",            "7203",    "TSEJ",    "JPY"),    # TSEJ = Tokyo; TSE = Toronto

        # --- Not available in IBKR; use yfinance bulk (.KS/.TW/.SA/.KL/.BK/.JK) ---
        # Korea (KSE/KRX), Taiwan (TWSE), Brazil (BOVESPA), Malaysia (Bursa),
        # Thailand (SET), Indonesia (IDX) — exchange codes not recognised by IBKR API.
    ]

    # Filter markets based on command line arguments
    if args.exchanges:
        requested_exchanges = [e.strip().upper() for e in args.exchanges.split(',')]
        print(f"Testing only exchanges: {', '.join(requested_exchanges)}")
        markets_to_test = [market for market in markets_to_test if market[2].upper() in requested_exchanges]

        if not markets_to_test:
            print("No matching exchanges found. Available IBKR exchanges:")
            all_exchanges = set(market[2] for market in markets_to_test)
            print(", ".join(sorted(all_exchanges)))
            print("\nNote: Korea (KSE), Taiwan (TWSE), Brazil (BOVESPA), Malaysia (Bursa),")
            print("      Thailand (SET), Indonesia (IDX) are yfinance-only — not in IBKR.")
            return
    else:
        print("Testing all exchanges...")

    for market_name, symbol, exchange, currency in markets_to_test:
        await tester.test_market(market_name, symbol, exchange, currency, "")

    # Generate final report
    tester.print_final_report()

    # Cleanup
    if tester.provider.ib and tester.provider.ib.isConnected():
        tester.provider.ib.disconnect()
        print("\nIBKR connection closed.")

if __name__ == "__main__":
    asyncio.run(main())