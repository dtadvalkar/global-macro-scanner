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
    print("   ✅ Schema Ready.")

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

async def ingest_multi_ohlcv(master_ids):
    sfx_map = {get_suffixes(mid)["yf"]: mid for mid in master_ids}
    yf_symbols = list(sfx_map.keys())
    print(f"\n[YF] Bulk Downloading OHLCV (1 month)...")
    df = yf.download(yf_symbols, period="1mo", interval="1d", auto_adjust=False, group_by='ticker')
    if df.empty: return
    batch_data = []
    for symbol in yf_symbols:
        master_id = sfx_map[symbol]
        try:
            ticker_df = df[symbol].dropna()
            for date, row in ticker_df.iterrows():
                batch_data.append((master_id, date.date(), float(row['Open']), float(row['High']), float(row['Low']), float(row['Close']), float(row['Adj Close']), int(row['Volume']), 'yf'))
        except: continue
    
    conn = psycopg2.connect(dbname=DB_CONFIG['db_name'], user=DB_CONFIG['db_user'], password=DB_CONFIG['db_pass'], host=DB_CONFIG['db_host'], port=DB_CONFIG['db_port'])
    cur = conn.cursor()
    execute_values(cur, f"INSERT INTO {TBL_DAILY} (ticker, trade_date, open, high, low, close, adj_close, volume, source) VALUES %s ON CONFLICT (ticker, trade_date, source) DO NOTHING", batch_data)
    conn.commit()
    cur.close()
    conn.close()
    print(f"   ✅ Ingested {len(batch_data)} OHLCV rows.")

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

if __name__ == "__main__":
    asyncio.run(run_data_audit())
