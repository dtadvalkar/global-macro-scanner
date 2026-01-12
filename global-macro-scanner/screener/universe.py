import financedatabase as fd
import os
from config import CRITERIA, MARKETS, TEST_MODE
from storage.database import DatabaseManager

db = DatabaseManager()

def get_universe(markets):
    """Get stock universe based on market config with PG caching"""
    universe = []
    
    mapping = {
        # IBKR Supported Markets
        'nse': ('NSE', 'NSE'),           # India NSE (.NS)
        'tsx': ('TOR', 'TSE'),           # Canada TSE (.TO) - Fixed: TSE not TSX
        'asx': ('ASX', 'ASX'),           # Australia ASX (.AX)
        'sgx': ('SG', 'SGX'),            # Singapore SGX (.SI) - FD uses 'SG'
        'xetra': ('GER', 'XETRA'),       # Germany XETRA (.DE)
        'sbf': ('FRA', 'SBF'),           # France Euronext (.PA)

        # YFinance Only Markets
        'idx': ('JKT', 'IDX'),           # Indonesia IDX (.JK)
        'set': ('SET', 'SET')            # Thailand SET (.BK)
    }
    
    for m_key, (fd_key, db_key) in mapping.items():
        if not markets.get(m_key):
            continue
            
        # Try Cache First
        cached = db.get_cached_tickers(db_key)
        if cached:
            print(f"Loaded {len(cached)} {db_key} tickers from PostgreSQL cache.")
            universe.extend(cached)
            continue

        # Fetch from FinanceDatabase
        print(f"Loading {db_key} universe (financedatabase)...")
        try:
            equities = fd.Equities()
            selection = equities.search(exchange=fd_key)
            
            suffix = {
                # IBKR Supported Markets
                'NSE': '.NS',           # India
                'TSE': '.TO',           # Canada
                'ASX': '.AX',           # Australia
                'SGX': '.SI',           # Singapore
                'XETRA': '.DE',         # Germany
                'SBF': '.PA',           # France

                # YFinance Only Markets
                'IDX': '.JK',           # Indonesia
                'SET': '.BK'            # Thailand
            }.get(db_key, '')
            
            tickers = [f"{s}{suffix}" if not s.endswith(suffix) else s for s in selection.index]

            if TEST_MODE and m_key == 'nse':
                tickers = tickers[:CRITERIA.get('nse_top_limit', 200)]

            # Validate IBKR-supported markets by checking contract qualification
            ibkr_supported_exchanges = ['NSE', 'TSE', 'ASX', 'SGX', 'IBIS', 'SBF']
            if db_key in ibkr_supported_exchanges:
                print(f"  Validating {len(tickers)} {db_key} stocks with IBKR...")
                print(f"  Starting IBKR validation process...")
                validated_tickers = []

                # Import IBKR provider for validation
                from data.providers import IBKRProvider
                import asyncio

                # Create a temporary IBKR connection for validation
                provider = None
                try:
                    print(f"  Connecting to IBKR for validation...")
                    # Use a different client ID to avoid conflicts
                    provider = IBKRProvider(host='127.0.0.1', port=int(os.getenv('IBKR_PORT', '7496')), client_id=200)
                    connected = asyncio.run(provider.connect())
                    print(f"  IBKR connection result: {connected}")
                    if connected:
                        # Validate contracts (limit to first 200 for better NSE coverage)
                        validation_limit = min(200, len(tickers))
                        print(f"  Testing contract qualification for first {validation_limit} stocks...")

                        for i, ticker in enumerate(tickers[:validation_limit]):
                            try:
                                # Extract symbol without suffix for IBKR
                                symbol = ticker.split('.')[0]
                                currency_map = {
                                    'NSE': 'INR',
                                    'TSE': 'CAD',
                                    'ASX': 'AUD',
                                    'SGX': 'SGD',
                                    'IBIS': 'EUR',
                                    'SBF': 'EUR'
                                }
                                currency = currency_map.get(db_key, 'USD')

                                from ib_async import Stock
                                contract = Stock(symbol, db_key, currency)

                                # Try to qualify the contract
                                qualified = asyncio.run(provider.ib.qualifyContractsAsync(contract))

                                if qualified:
                                    # Additional validation: try to get historical data
                                    try:
                                        bars = asyncio.run(provider.ib.reqHistoricalDataAsync(
                                            qualified[0],
                                            endDateTime='',
                                            durationStr='1 D',
                                            barSizeSetting='1 day',
                                            whatToShow='MIDPOINT',
                                            useRTH=True
                                        ))
                                        if bars and len(bars) > 0:
                                            validated_tickers.append(ticker)
                                            if (len(validated_tickers)) % 2 == 0:
                                                print(f"  Validated {len(validated_tickers)} stocks so far...")
                                        else:
                                            print(f"  {ticker}: No historical data available")
                                        # If no bars or empty, skip this ticker
                                    except Exception as e:
                                        print(f"  {ticker}: Historical data failed - {str(e)[:50]}...")
                                else:
                                    print(f"  {ticker}: Contract not qualified")

                            except Exception as e:
                                print(f"  {ticker}: Qualification error - {str(e)[:50]}...")
                                continue

                        print(f"  IBKR validation complete: {len(validated_tickers)}/{validation_limit} stocks qualified")

                        # Only use stocks that actually qualified with IBKR
                        if validated_tickers:
                            # For now, only include the validated stocks to avoid Error 200
                            # TODO: In the future, we could validate all stocks or use a sampling approach
                            tickers = validated_tickers
                            print(f"  Using only validated stocks: {len(tickers)} stocks")
                        else:
                            print(f"  Warning: No stocks qualified validation, using empty list")
                            tickers = []
                    else:
                        print(f"  Warning: Could not connect to IBKR for validation, using original list")

                except Exception as e:
                    print(f"  Warning: IBKR validation failed ({e}), using original list")
                finally:
                    if provider and provider.ib and provider.ib.isConnected():
                        provider.ib.disconnect()

            db.save_tickers(db_key, tickers)
            universe.extend(tickers)
            print(f"  Found {len(tickers)} {db_key} stocks (Cached to DB)")
            
        except Exception as e:
            print(f"Warning: {db_key} load failed: {e}")
            fallback = {
                'TSX': ['RY.TO', 'TD.TO']
            }.get(db_key, [])
            universe.extend(fallback)
        
    print(f"Loaded {len(universe)} stocks total")
    return universe
