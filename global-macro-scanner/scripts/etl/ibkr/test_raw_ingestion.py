"""
test_raw_ingestion.py (v2 - Database Integrated)

Diagnostic tool to verify 'Full Fidelity' data capture across:
1. FinanceDatabase (Jerma Bouma)
2. IBKR (Reuters XML + Price Snapshot)
3. YFinance (.info + OHLCV Download)

STORES: Verbatim Raw Data + Unified Daily Prices in PostgreSQL.
"""

import asyncio
import json
import psycopg2
from psycopg2.extras import execute_values
import yfinance as yf
import financedatabase as fd
from ib_insync import IB, Stock, util
from config import DB_CONFIG
import math
import sys
import io

# Force UTF-8 encoding for stdout to support emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def clean_dict(obj):
    """Recursively converts NaN values to None for JSON compatibility."""
    if isinstance(obj, dict):
        return {k: clean_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_dict(x) for x in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

# --- CONFIGURATION ---
MASTER_IDS = ["RELIANCE.NSE", "INFY.NSE", "TCS.NSE"]
IBKR_PORT = 7496 # Switched to 7496 for Live Account testing

# --- DATABASE TABLENAMES ---
TBL_RAW_FD = "raw_fd_nse"
TBL_RAW_IBKR = "raw_ibkr_nse"
TBL_RAW_YF = "raw_yf_nse"
TBL_DAILY = "prices_daily"

def get_suffixes(master_id: str):
    base = master_id.split('.')[0]
    return {
        "master": master_id,
        "ibkr": base,
        "yf": f"{base}.NS",
        "fd": f"{base}.NS" # FinanceDatabase NSE stocks use .NS suffix
    }

def init_db():
    """Creates the raw-fidelity and price-series tables if they don't exist."""
    print("\n[DB] Initializing database schema...")
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()
    
    # 1. Raw FinanceDatabase Table
    cur.execute(f"CREATE TABLE IF NOT EXISTS {TBL_RAW_FD} (ticker TEXT PRIMARY KEY, raw_data JSONB, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
    
    # 2. Raw IBKR Table
    cur.execute(f"CREATE TABLE IF NOT EXISTS {TBL_RAW_IBKR} (ticker TEXT PRIMARY KEY, xml_snapshot TEXT, xml_ratios TEXT, mkt_data JSONB, contract_details JSONB, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
    
    # 3. Raw YFinance Table
    cur.execute(f"CREATE TABLE IF NOT EXISTS {TBL_RAW_YF} (ticker TEXT PRIMARY KEY, raw_info JSONB, raw_fast_info JSONB, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
    
    # 4. Unified Daily Prices
    cur.execute(f"CREATE TABLE IF NOT EXISTS {TBL_DAILY} (ticker TEXT, trade_date DATE, open NUMERIC, high NUMERIC, low NUMERIC, close NUMERIC, adj_close NUMERIC, volume BIGINT, source TEXT NOT NULL, PRIMARY KEY (ticker, trade_date, source));")
    
    conn.commit()
    cur.close()
    conn.close()
    print("   Schema Ready.")

async def fetch_financedatabase_raw(symbol: str):
    print(f"\n[FD] Fetching FinanceDatabase for: {symbol}...")
    try:
        equities = fd.Equities()
        # Filtering by exchange='NSE' narrows the search space significantly
        data = equities.select(exchange='NSE')
        if symbol in data.index:
            return data.loc[[symbol]].to_dict(orient='index')
        else:
            print(f"   ! Symbol {symbol} not found in FinanceDatabase.")
            return {}
    except Exception as e:
        print(f"   ! FD Fetch failed: {e}")
        return {"error": str(e)}

async def fetch_all_financedatabase_nse():
    """Fetch all NSE stocks data from FinanceDatabase in one bulk call."""
    print("\n[FD] Fetching ALL NSE stocks from FinanceDatabase...")
    try:
        equities = fd.Equities()
        data = equities.select(exchange='NSE')
        print(f"   Retrieved {len(data)} NSE stocks from FinanceDatabase")
        return data.to_dict(orient='index')
    except Exception as e:
        print(f"   ! FD Bulk fetch failed: {e}")
        return {}

import random # Added for clientId randomization

async def fetch_ibkr_raw(symbol: str, port: int):
    # Using a random clientId between 1000-9999 to avoid "already in use" errors
    client_id = random.randint(1000, 9999)
    print(f"\n[IBKR] Connecting to Port {port} (ID: {client_id}) for: {symbol}...")
    ib = IB()
    results = {"xml_snapshot": None, "xml_ratios": None, "mkt_data": None, "contract_details": None, "error": None}
    try:
        print("   -> Attempting connection...")
        await asyncio.wait_for(ib.connectAsync('127.0.0.1', port, clientId=client_id), timeout=10)
        print("   -> Connected. Qualifying contract...")
        
        contract = Stock(symbol, 'NSE', 'INR')
        try:
            # Added timeout to qualification which can sometimes hang on poor connection
            qualified = await asyncio.wait_for(ib.qualifyContractsAsync(contract), timeout=15)
        except asyncio.TimeoutError:
            print("   ! Contract qualification timed out.")
            return results

        if not qualified:
            results["error"] = "Contract not qualified"
            return results
        
        print(f"   -> Contract qualified. Symbol: {qualified[0].localSymbol}")
        
        # Fundamental Data (One-Time)
        print("   -> Requesting ReportSnapshot...")
        try:
            results["xml_snapshot"] = await asyncio.wait_for(
                ib.reqFundamentalDataAsync(qualified[0], reportType='ReportSnapshot'), 
                timeout=20
            )
            print(f"   -> Snapshot received ({len(results['xml_snapshot'])} bytes)")
        except Exception as e:
            print(f"   ! ReportSnapshot failed: {e}")

        print("   -> Requesting ReportRatios...")
        try:
            results["xml_ratios"] = await asyncio.wait_for(
                ib.reqFundamentalDataAsync(qualified[0], reportType='ReportRatios'), 
                timeout=20
            )
            print(f"   -> Ratios received ({len(results['xml_ratios'])} bytes)")
        except Exception as e:
            print(f"   ! ReportRatios failed: {e}")

        # Market Data (Recurring)
        ib.reqMarketDataType(3)
        print("   -> Requesting MktData Snapshot...")
        ticker = ib.reqMktData(qualified[0], "", snapshot=True)
        
        # Explicitly wait for market data to arrive
        for i in range(12):
            await asyncio.sleep(0.5)
            if ticker.last > 0: 
                print(f"   -> MktData populated: Last={ticker.last}")
                break
            if i % 4 == 0: print("      ... waiting for price ...")
            
        results["mkt_data"] = util.tree(ticker)
        
        # Contract Details
        print("   -> Fetching Contract Details...")
        cds = await asyncio.wait_for(ib.reqContractDetailsAsync(qualified[0]), timeout=10)
        if cds:
            results["contract_details"] = util.tree(cds[0])
            print("   -> Contract details captured.")

    except asyncio.TimeoutError:
        print(f"   ! IBKR Connection or request timed out.")
        results["error"] = "Timeout"
    except Exception as e:
        print(f"   ! IBKR Error: {e}")
        results["error"] = str(e)
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("   -> Disconnected from IBKR.")
    return results

async def fetch_yfinance_raw(symbol: str):
    print(f"\n[YF] Fetching .info for: {symbol}...")
    try:
        t = yf.Ticker(symbol)
        return {"info": t.info, "fast_info": dict(t.fast_info)}
    except Exception as e:
        print(f"   ! YF Error: {e}")
        return {"error": str(e)}

async def save_to_db(master_id, fd_raw, ibkr_raw, yf_raw):
    print(f"[DB] Ingesting {master_id}...")
    conn = psycopg2.connect(dbname=DB_CONFIG['db_name'], user=DB_CONFIG['db_user'], password=DB_CONFIG['db_pass'], host=DB_CONFIG['db_host'], port=DB_CONFIG['db_port'])
    cur = conn.cursor()

    # 1. FD
    cur.execute(f"INSERT INTO {TBL_RAW_FD} (ticker, raw_data) VALUES (%s, %s) ON CONFLICT (ticker) DO UPDATE SET raw_data = EXCLUDED.raw_data, last_updated = CURRENT_TIMESTAMP",
                (master_id, json.dumps(clean_dict(fd_raw))))

    # 2. IBKR
    cur.execute(f"INSERT INTO {TBL_RAW_IBKR} (ticker, xml_snapshot, xml_ratios, mkt_data, contract_details) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (ticker) DO UPDATE SET xml_snapshot = EXCLUDED.xml_snapshot, xml_ratios = EXCLUDED.xml_ratios, mkt_data = EXCLUDED.mkt_data, contract_details = EXCLUDED.contract_details, last_updated = CURRENT_TIMESTAMP",
                (master_id, ibkr_raw.get('xml_snapshot'), ibkr_raw.get('xml_ratios'), json.dumps(clean_dict(ibkr_raw.get('mkt_data'))), json.dumps(clean_dict(ibkr_raw.get('contract_details')))))

    # 3. YF
    cur.execute(f"INSERT INTO {TBL_RAW_YF} (ticker, raw_info, raw_fast_info) VALUES (%s, %s, %s) ON CONFLICT (ticker) DO UPDATE SET raw_info = EXCLUDED.raw_info, raw_fast_info = EXCLUDED.raw_fast_info, last_updated = CURRENT_TIMESTAMP",
                (master_id, json.dumps(clean_dict(yf_raw.get('info'))), json.dumps(clean_dict(yf_raw.get('fast_info')))))

    conn.commit()
    cur.close()
    conn.close()

async def ingest_all_fd_nse():
    """Ingest all NSE stocks from FinanceDatabase into raw_fd_nse table."""
    init_db()
    fd_data = await fetch_all_financedatabase_nse()

    if not fd_data:
        print("No FD data retrieved, aborting ingestion.")
        return

    conn = psycopg2.connect(dbname=DB_CONFIG['db_name'], user=DB_CONFIG['db_user'], password=DB_CONFIG['db_pass'], host=DB_CONFIG['db_host'], port=DB_CONFIG['db_port'])
    cur = conn.cursor()

    batch_data = []
    for ticker, data in fd_data.items():
        # Convert ticker to .NS format (standard NSE format for IBKR/YFinance compatibility)
        master_ticker = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        batch_data.append((master_ticker, json.dumps(clean_dict(data))))

    print(f"[DB] Bulk inserting {len(batch_data)} NSE stocks into {TBL_RAW_FD}...")
    execute_values(cur, f"INSERT INTO {TBL_RAW_FD} (ticker, raw_data) VALUES %s ON CONFLICT (ticker) DO UPDATE SET raw_data = EXCLUDED.raw_data, last_updated = CURRENT_TIMESTAMP", batch_data)

    conn.commit()
    cur.close()
    conn.close()
    print(f"Successfully ingested {len(batch_data)} NSE stocks from FinanceDatabase.")

async def ingest_multi_ohlcv(master_ids, period="2y"):
    """Download OHLCV data for multiple tickers using bulk YFinance download."""
    # Convert master tickers to YFinance format (.NSE -> base symbol only)
    yf_symbols = []
    master_to_yf_map = {}

    for master_id in master_ids:
        # Convert RELIANCE.NSE -> RELIANCE.NS for YFinance (NSE stocks use .NS suffix)
        base = master_id.split('.')[0]
        yf_symbol = f"{base}.NS"  # NSE stocks need .NS suffix on Yahoo Finance
        yf_symbols.append(yf_symbol)
        master_to_yf_map[yf_symbol] = master_id

    print(f"\n[YF] Bulk Downloading OHLCV ({period}) for {len(yf_symbols)} tickers...")
    print(f"   Sample conversions: {list(master_to_yf_map.items())[:3]}")

    try:
        # Use bulk download with threading to avoid rate limits - ONE SHOT APPROACH
        data_hist = yf.download(
            tickers=" ".join(yf_symbols),
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception as e:
        print(f"   ❌ Bulk download failed: {e}")
        return

    if data_hist.empty:
        print("   ❌ No data downloaded from YFinance")
        return

    batch_data = []
    successful_tickers = 0

    for yf_symbol in yf_symbols:
        master_id = master_to_yf_map[yf_symbol]
        try:
            # Check if this symbol has data in the result
            if hasattr(data_hist, 'columns') and len(data_hist.columns) > 0:
                # MultiIndex columns case - yfinance puts tickers in level 1
                if data_hist.columns.nlevels > 1 and yf_symbol in data_hist.columns.levels[1]:
                    ticker_df = data_hist.xs(yf_symbol, axis=1, level=1).dropna()
                    if not ticker_df.empty:
                        for date, row in ticker_df.iterrows():
                            batch_data.append((
                                master_id, date.date(),
                                float(row['Open']), float(row['High']), float(row['Low']),
                                float(row['Close']), float(row['Adj Close']), int(row['Volume']),
                                'yf'
                            ))
                        successful_tickers += 1
                        print(f"   OK {yf_symbol} -> {len(ticker_df)} days")
                    else:
                        print(f"   WARNING {yf_symbol} -> Empty data")
                else:
                    print(f"   ERROR {yf_symbol} -> Not found in results")
            else:
                print(f"   ERROR {yf_symbol} -> Invalid data structure")

        except Exception as e:
            print(f"   ERROR processing {yf_symbol}: {e}")
            continue

    if batch_data:
        try:
            conn = psycopg2.connect(
                dbname=DB_CONFIG['db_name'],
                user=DB_CONFIG['db_user'],
                password=DB_CONFIG['db_pass'],
                host=DB_CONFIG['db_host'],
                port=DB_CONFIG['db_port']
            )
            cur = conn.cursor()
            execute_values(cur, f"INSERT INTO {TBL_DAILY} (ticker, trade_date, open, high, low, close, adj_close, volume, source) VALUES %s ON CONFLICT (ticker, trade_date, source) DO NOTHING", batch_data)
            conn.commit()
            cur.close()
            conn.close()
            print(f"\n   SUCCESS: Ingested {len(batch_data)} OHLCV rows from {successful_tickers}/{len(yf_symbols)} tickers")
            print(f"   Average {len(batch_data)/successful_tickers:.0f} days per ticker")
        except Exception as e:
            print(f"   ❌ Database error: {e}")
    else:
        print("   No valid OHLCV data to ingest")

def get_fundamentals_tickers():
    """Get all tickers from stock_fundamentals table."""
    conn = psycopg2.connect(dbname=DB_CONFIG['db_name'], user=DB_CONFIG['db_user'], password=DB_CONFIG['db_pass'], host=DB_CONFIG['db_host'], port=DB_CONFIG['db_port'])
    cur = conn.cursor()
    cur.execute("SELECT ticker FROM stock_fundamentals ORDER BY ticker")
    tickers = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tickers

async def main_fd_only():
    """Modular function to ingest only FinanceDatabase NSE data."""
    await ingest_all_fd_nse()


async def main_ibkr_only(master_ids=None):
    """Modular function to ingest only IBKR data for given tickers."""
    if master_ids is None:
        master_ids = MASTER_IDS
    init_db()
    for mid in master_ids:
        sfx = get_suffixes(mid)
        # Only fetch IBKR data
        ibkr_raw = await fetch_ibkr_raw(sfx["ibkr"], IBKR_PORT)
        # Save only IBKR data (pass empty dicts for others)
        await save_to_db(mid, {}, ibkr_raw, {})
    print(f"\n[IBKR COMPLETE] Raw IBKR data ingested for {len(master_ids)} tickers.")

async def run_data_audit():
    init_db()
    for mid in MASTER_IDS:
        sfx = get_suffixes(mid)
        fd_raw = await fetch_financedatabase_raw(sfx["fd"])
        ibkr_raw = await fetch_ibkr_raw(sfx["ibkr"], IBKR_PORT)
        yf_raw = await fetch_yfinance_raw(sfx["yf"])
        await save_to_db(mid, fd_raw, ibkr_raw, yf_raw)
    await ingest_multi_ohlcv(MASTER_IDS)
    print("\n[COMPLETE] All data successfully stored in PostgreSQL.")

async def collect_yfinance_for_fundamentals_tickers(period="2y"):
    """Collect YFinance OHLCV data for all tickers in stock_fundamentals table."""
    print("\n[YFINANCE COLLECTION] Starting for all fundamentals tickers...")
    print("="*60)

    # Get tickers from fundamentals table
    fundamentals_tickers = get_fundamentals_tickers()
    total_tickers = len(fundamentals_tickers)
    print(f"Found {total_tickers} tickers in stock_fundamentals")

    if total_tickers == 0:
        print("No tickers found in stock_fundamentals table!")
        return

    # Collect YFinance data (bulk download)
    print(f"\nDownloading {period} of OHLCV data...")
    await ingest_multi_ohlcv(fundamentals_tickers, period=period)

    print("\n" + "="*60)
    print(f"[COMPLETE] YFinance data collected for {total_tickers} tickers")
    print("Data stored in: prices_daily table with source='yf'")

async def collect_yfinance_for_ticker_list(ticker_list, period="2y"):
    """Collect YFinance OHLCV data for a custom list of tickers."""
    print(f"\n[YFINANCE COLLECTION] Starting for {len(ticker_list)} custom tickers...")
    print("="*60)

    if not ticker_list:
        print("No tickers provided!")
        return

    # Collect YFinance data (bulk download)
    print(f"Downloading {period} of OHLCV data...")
    await ingest_multi_ohlcv(ticker_list, period=period)

    print("\n" + "="*60)
    print(f"[COMPLETE] YFinance data collected for {len(ticker_list)} tickers")
    print("Data stored in: prices_daily table with source='yf'")

if __name__ == "__main__":
    # Default behavior: test with 3 tickers
    asyncio.run(run_data_audit())
