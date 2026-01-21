import psycopg2
import xml.etree.ElementTree as ET
from datetime import datetime
from config import DB_CONFIG

def flatten_ibkr_data():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()

        # 1. Drop and Create the stock_fundamentals table
        print("[DB] Recreating stock_fundamentals table...")
        cur.execute("DROP TABLE IF EXISTS stock_fundamentals;")
        cur.execute("""
            CREATE TABLE stock_fundamentals (
                ticker                   TEXT PRIMARY KEY,
                company_name             TEXT,
                sector                   TEXT,
                industry                 TEXT,
                market_cap_usd           NUMERIC,
                pe_ratio                 NUMERIC,
                fifty_two_w_low          NUMERIC,
                fifty_two_w_high         NUMERIC,
                dividend_yield           NUMERIC,
                currency                 TEXT,
                last_fundamental_update  TIMESTAMP
            );
        """)
        conn.commit()

        # 2. Fetch all raw IBKR data
        cur.execute("SELECT ticker, xml_snapshot, last_updated FROM raw_ibkr_nse WHERE xml_snapshot IS NOT NULL;")
        rows = cur.fetchall()
        print(f"[ETL] Found {len(rows)} raw XML records to process.")

        for ticker, xml_str, last_updated in rows:
            try:
                root = ET.fromstring(xml_str)
                
                # Helper to find text in XML using XPath-like find
                def get_val(path, attr=None):
                    node = root.find(path)
                    if node is not None:
                        return node.text.strip() if node.text else None
                    return None

                # Extract Fields
                # Company Name
                name = get_val(".//CoID[@Type='CompanyName']")
                
                # Sector/Industry (TRBC code or text)
                industry = get_val(".//Industry[@type='TRBC']")
                
                # Ratios (These use FieldName attributes)
                # Map our target codes
                ratios = {}
                for ratio in root.findall(".//Ratio"):
                    fname = ratio.attrib.get('FieldName')
                    if fname:
                        ratios[fname] = ratio.text

                # Extract specific mapped values
                mkt_cap = ratios.get('MKTCAP')
                pe = ratios.get('APEEXCLXOR')
                low_52w = ratios.get('NLOW')
                high_52w = ratios.get('NHIG')
                div_yield = ratios.get('ADIVYIELD') # Check if exists
                
                currency = root.find(".//Ratios").attrib.get('PriceCurrency') if root.find(".//Ratios") is not None else 'INR'

                # 3. Insert into stock_fundamentals
                cur.execute("""
                    INSERT INTO stock_fundamentals (
                        ticker, company_name, industry, market_cap_usd, 
                        pe_ratio, fifty_two_w_low, fifty_two_w_high, 
                        dividend_yield, currency, last_fundamental_update
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        market_cap_usd = EXCLUDED.market_cap_usd,
                        pe_ratio = EXCLUDED.pe_ratio,
                        fifty_two_w_low = EXCLUDED.fifty_two_w_low,
                        fifty_two_w_high = EXCLUDED.fifty_two_w_high,
                        last_fundamental_update = EXCLUDED.last_fundamental_update;
                """, (
                    ticker, name, industry, mkt_cap, pe, low_52w, high_52w, div_yield, currency, last_updated
                ))
                print(f"   ✅ Processed: {ticker} ({name})")

            except Exception as e:
                print(f"   ❌ Error parsing {ticker}: {e}")

        conn.commit()
        cur.close()
        conn.close()
        print("\n[SUCCESS] stock_fundamentals table is now populated.")

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    flatten_ibkr_data()
