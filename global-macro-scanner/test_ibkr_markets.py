#!/usr/bin/env python3
"""
Test IBKR market data access for all configured markets
"""
import asyncio
from data.providers import IBKRProvider
import os
from dotenv import load_dotenv
load_dotenv()

async def test_ibkr_markets():
    # Test IBKR connection and market access
    port = int(os.getenv('IBKR_PORT', '7496'))
    provider = IBKRProvider(host='127.0.0.1', port=port, client_id=90)

    # Test markets - using symbols that should work with IBKR
    test_stocks = {
        'US': 'AAPL',           # USA (SMART)
        'Canada': 'RY.TO',      # Canada (TSX)
        'India': 'RELIANCE.NS', # India (NSE)
        'Thailand': 'PTT.BK',   # Thailand (SET) - should fail
        'Indonesia': 'BBRI.JK'  # Indonesia (IDX) - should fail
    }

    print('Testing IBKR market data access for all configured markets:')
    print('=' * 60)

    for market, symbol in test_stocks.items():
        print(f'\nTesting {market} ({symbol}):')
        try:
            # Try to connect and get a quick sample
            if not provider.ib or not provider.ib.isConnected():
                print('  Connecting to IBKR...')
                success = await provider.connect()
                if not success:
                    print('  Connection failed')
                    continue

            # Try a quick historical data request (1 day)
            from ib_async import Stock

            # Map symbol to IBKR contract
            if symbol.endswith('.TO'):  # Canada
                contract = Stock(symbol[:-3], 'TSX', 'CAD')
            elif symbol.endswith('.NS'):  # India
                contract = Stock(symbol[:-3], 'NSE', 'INR')
            elif symbol.endswith('.BK'):  # Thailand
                print('  Note: Thailand SET not supported by IBKR (routes to YFinance)')
                continue
            elif symbol.endswith('.JK'):  # Indonesia
                print('  Note: Indonesia IDX not supported by IBKR (routes to YFinance)')
                continue
            else:  # US
                contract = Stock(symbol, 'SMART', 'USD')

            print(f'  Contract: {contract}')

            # Try to qualify
            qualified = await provider.ib.qualifyContractsAsync(contract)

            if qualified:
                print('  SUCCESS - Contract qualified')

                # Try a quick historical data request
                bars = await provider.ib.reqHistoricalDataAsync(
                    qualified[0], endDateTime='', durationStr='1 D',
                    barSizeSetting='1 day', whatToShow='TRADES', useRTH=True
                )

                if bars and len(bars) > 0:
                    print(f'  SUCCESS - Historical data available ({len(bars)} bars)')
                    print(f'  Latest: {bars[-1].close} {contract.currency}')
                else:
                    print('  Contract qualified but no historical data')
            else:
                print('  FAILED - Contract qualification failed')

        except Exception as e:
            print(f'  ERROR: {str(e)[:80]}...')

        print()

    # Clean up
    if provider.ib and provider.ib.isConnected():
        provider.ib.disconnect()
        print('IBKR connection closed.')

if __name__ == "__main__":
    asyncio.run(test_ibkr_markets())