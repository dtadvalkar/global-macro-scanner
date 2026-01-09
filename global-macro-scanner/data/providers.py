import yfinance as yf
from ib_insync import *
import asyncio
import pandas as pd
from data.currency import usd_market_cap
from datetime import datetime

util.patchAsyncio()

class BaseProvider:
    def get_market_data(self, tickers, criteria):
        raise NotImplementedError

class YFinanceProvider(BaseProvider):
    def get_market_data(self, tickers, criteria):
        results = []
        for symbol in tickers:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period='1y')
                if not hist.empty and len(hist) > criteria.get('min_history_days', 0):
                    info = stock.info
                    usd_mcap = usd_market_cap(symbol, info.get('marketCap', 0))
                    
                    # 🚀 Use modular registry
                    from config.markets import get_min_market_cap
                    
                    # Determine exchange from suffix
                    exchange_map = {'.NS': 'NSE', '.TO': 'TSE', '.JK': 'IDX', '.BK': 'SET'}
                    exchange = 'SMART'
                    for suffix, ex in exchange_map.items():
                        if symbol.endswith(suffix):
                            exchange = ex
                            break
                    
                    min_cap = get_min_market_cap(exchange)
                    
                    # RVOL Calculation
                    current_vol = hist['Volume'].iloc[-1]
                    avg_vol_30d = hist['Volume'].tail(30).mean()
                    rvol = current_vol / avg_vol_30d if avg_vol_30d > 0 else 0
                    
                    # LOGIC: (Vol > Min) OR (RVOL > Min)
                    vol_ok = (current_vol >= criteria.get('min_volume', 100000))
                    rvol_ok = (rvol >= criteria.get('min_rvol', 2.0))
                    
                    if usd_mcap > min_cap and (vol_ok or rvol_ok):
                        low_52w = hist['Low'].min()
                        current = hist['Close'].iloc[-1]
                        pct_from_low = current / low_52w
                        
                        if pct_from_low <= criteria['price_52w_low_pct']:
                            results.append({
                                'symbol': symbol, 'price': current, 'low_52w': low_52w,
                                'usd_mcap': usd_mcap/1e9, 'pct_from_low': pct_from_low,
                                'rvol': rvol, 'time': datetime.now()
                            })
            except Exception as e:
                print(f"  ⚠️ {symbol} error (yfinance): {str(e)[:30]}")
        return results

class IBKRProvider(BaseProvider):
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()

    async def connect(self):
        try:
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
            # Tiered Data Access:
            # Type 1 = Real-time (User has enabled for free markets)
            # Type 3 = Delayed (Fallback to ensure zero-fee scanning elsewhere)
            self.ib.reqMarketDataType(3) 
            print(f"✅ Connected to IBKR on {self.host}:{self.port} (Hybrid Data Mode Active)")
            return True
        except Exception:
            return False

    async def get_market_data_async(self, tickers, criteria):
        try:
            if not self.ib.isConnected():
                if not await self.connect():
                    print("❌ IBKR Connection failed. Use fallback.")
                    return []
            
            print(f"🚀 IBKR Parallel Scan: {len(tickers)} stocks...")
            results = []
            batch_size = 50
            for i in range(0, len(tickers), batch_size):
                batch = tickers[i:i + batch_size]
                tasks = [self.process_stock(s, criteria) for s in batch]
                batch_results = await asyncio.gather(*tasks)
                results.extend([r for r in batch_results if r])
            
            return results
        finally:
            if self.ib.isConnected():
                self.ib.disconnect()
                await asyncio.sleep(0.1) # Give it a moment to clean up loops

    async def process_stock(self, symbol, criteria):
        try:
            # Map symbol to IBKR contract
            exchange = 'SMART'
            currency = 'USD'
            pure_symbol = symbol
            
            if symbol.endswith('.TO'):
                exchange = 'TSX'
                currency = 'CAD'
                pure_symbol = symbol[:-3]
            elif symbol.endswith('.NS'):
                exchange = 'NSE'
                currency = 'INR'
                pure_symbol = symbol[:-3]
            elif symbol.endswith('.JK'):
                # Indonesia IDX not supported by IBKR - skip to YFinance fallback
                # Tested: IDX exchange code fails with "Invalid destination or exchange"
                # Error: "The destination or exchange selected is Invalid"
                return None
            elif symbol.endswith('.BK'):
                # Thailand SET not supported by IBKR - skip to YFinance fallback
                # Tested: SMART routing, primaryExchange, direct SET all fail
                # Error: "The destination or exchange selected is Invalid"
                return None

            contract = Stock(pure_symbol, exchange, currency)
            qualified = await self.ib.qualifyContractsAsync(contract)
            if not qualified: return None

            # Attempt to fetch TRADES if possible for volume, otherwise MIDPOINT
            try:
                bars = await self.ib.reqHistoricalDataAsync(
                    contract, endDateTime='', durationStr='1 Y',
                    barSizeSetting='1 day', whatToShow='TRADES', useRTH=True
                )
            except Exception:
                bars = await self.ib.reqHistoricalDataAsync(
                    contract, endDateTime='', durationStr='1 Y',
                    barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True
                )
            
            if not bars: return None

            low_52w = min(b.low for b in bars)
            current = bars[-1].close
            pct_from_low = current / low_52w
            
            # RVOL Calculation
            # If TRADES worked, bars[i].volume is available. If MIDPOINT, it's 0/-1.
            current_vol = bars[-1].volume
            if current_vol > 0:
                avg_vol_30d = sum(b.volume for b in bars[-30:]) / 30
                rvol = current_vol / avg_vol_30d if avg_vol_30d > 0 else 0
            else:
                # Fallback to yfinance just for the RVOL if IBKR didn't give volume
                try:
                    yf_hist = yf.Ticker(symbol).history(period='1mo')
                    current_vol = yf_hist['Volume'].iloc[-1]
                    avg_vol_30d = yf_hist['Volume'].mean()
                    rvol = current_vol / avg_vol_30d if avg_vol_30d > 0 else 0
                except Exception:
                    rvol = 0
            
            # LOGIC: (Vol > Min) OR (RVOL > Min)
            vol_ok = (current_vol >= criteria.get('min_volume', 100000))
            rvol_ok = (rvol >= criteria.get('min_rvol', 2.0))

            if pct_from_low <= criteria['price_52w_low_pct'] and (vol_ok or rvol_ok):
                return {
                    'symbol': symbol, 'price': current, 'low_52w': low_52w,
                    'pct_from_low': pct_from_low, 'rvol': rvol, 'time': datetime.now()
                }
        except Exception:
            pass
        return None

    def get_market_data(self, tickers, criteria):
        # Synchronous wrapper for asyncio
        try:
            return asyncio.run(self.get_market_data_async(tickers, criteria))
        except Exception as e:
            print(f"  ❌ IBKR Async Error: {e}")
            return []

class IBKRScannerProvider(BaseProvider):
    def __init__(self, host='127.0.0.1', port=7496, client_id=1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()

    def get_scanner_results(self, instrument, location, scan_code):
        """Option B: Direct Server-Side Scan"""
        try:
            if not self.ib.isConnected():
                self.ib.connect(self.host, self.port, clientId=self.client_id)
                self.ib.reqMarketDataType(3)

            subscription = ScannerSubscription(
                instrument=instrument,
                locationCode=location,
                scanCode=scan_code
            )
            
            print(f"🔎 IBKR Server Scan: {location} ({scan_code})...")
            scan_data = self.ib.reqScannerData(subscription)
            
            results = []
            for item in scan_data:
                # We need historical data for the actual 52w low calculation
                # because the scanner just gives us the rank.
                results.append(item.contractDetails.contract.symbol + 
                              ('.TO' if 'CANADA' in location else ''))
            
            return results
        except Exception as e:
            print(f"  ⚠️ Scanner error: {e}")
            return []
        finally:
            self.ib.disconnect()
