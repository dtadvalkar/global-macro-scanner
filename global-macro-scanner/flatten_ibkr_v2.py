import psycopg2
import xml.etree.ElementTree as ET
import json
from datetime import datetime
from config import DB_CONFIG

def flatten_ibkr_high_fidelity():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()

        print("[DB] Recreating High-Fidelity stock_fundamentals table...")
        cur.execute("DROP TABLE IF EXISTS stock_fundamentals;")
        cur.execute("""
            CREATE TABLE stock_fundamentals (
                ticker                   TEXT PRIMARY KEY,
                company_name             TEXT,
                
                -- 📊 Valuation Ratios
                mkt_cap_usd              NUMERIC,
                pe_ratio                 NUMERIC,
                price_to_book            NUMERIC,
                price_to_revenue         NUMERIC,
                ev_ebitda                NUMERIC,
                
                -- 📈 Performance & Returns
                roe_pct                  NUMERIC,
                gross_margin_pct         NUMERIC,
                dividend_yield           NUMERIC,
                dividend_per_share       NUMERIC,
                
                -- 💵 Per Share Data
                eps                      NUMERIC,
                revenue_per_share        NUMERIC,
                book_value_per_share     NUMERIC,
                cash_per_share           NUMERIC,
                
                -- 🔭 Analyst Forecasts (Mean Consensus)
                target_price             NUMERIC,
                proj_pe                  NUMERIC,
                proj_eps                 NUMERIC,
                proj_sales               NUMERIC,
                proj_profit              NUMERIC,
                recommendation_score     NUMERIC,
                
                -- 📉 Technical Baselines (From XML)
                xml_52w_low              NUMERIC,
                xml_52w_high             NUMERIC,
                xml_last_price           NUMERIC,
                xml_vol_10d_avg          NUMERIC,
                
                -- 🏢 Company Profile
                sector                   TEXT,
                industry                 TEXT,
                employees                INTEGER,
                business_summary         TEXT,
                financial_summary        TEXT,
                officers_json            JSONB,
                
                -- 🕒 Metadata
                currency                 TEXT,
                last_fundamental_update  TIMESTAMP,
                last_price_update        TIMESTAMP
            );
        """)
        conn.commit()

        cur.execute("SELECT ticker, xml_snapshot, last_updated FROM raw_ibkr_nse WHERE xml_snapshot IS NOT NULL;")
        rows = cur.fetchall()
        print(f"[ETL] Processing {len(rows)} records...")

        for ticker, xml_str, last_updated in rows:
            try:
                root = ET.fromstring(xml_str)
                
                # Helpers
                def get_text(path):
                    node = root.find(path)
                    return node.text.strip() if node is not None and node.text else None

                # 1. Ratios Map
                ratios = {r.attrib.get('FieldName'): r.text for r in root.findall(".//Ratio")}
                
                # 2. Forecast Map (Mean CURR)
                forecasts = {}
                for fv in root.findall(".//ForecastData/Ratio"):
                    fname = fv.attrib.get('FieldName')
                    curr_val = fv.find("./Value[@PeriodType='CURR']")
                    if curr_val is not None:
                        forecasts[fname] = curr_val.text

                # 3. Officers JSON
                officers = []
                for off in root.findall(".//officers/officer"):
                    fname = get_text(".//firstName") or ""
                    lname = get_text(".//lastName") or ""
                    title = get_text(".//title") or ""
                    officers.append({"name": f"{fname} {lname}".strip(), "title": title})

                # 4. Profile Text
                biz_sum = ""
                fin_sum = ""
                for txt in root.findall(".//TextInfo/Text"):
                    t_type = txt.attrib.get('Type')
                    if t_type == "Business Summary": biz_sum = txt.text
                    elif t_type == "Financial Summary": fin_sum = txt.text

                # Extraction
                data = {
                    "ticker": ticker,
                    "company_name": get_text(".//CoID[@Type='CompanyName']"),
                    "mkt_cap_usd": ratios.get('MKTCAP'),
                    "pe_ratio": ratios.get('APEEXCLXOR'),
                    "price_to_book": ratios.get('APRICE2BK'),
                    "price_to_revenue": ratios.get('APR2REV'),
                    "ev_ebitda": ratios.get('EV_AEBITD'), # Note: Corrected code from inspection
                    "roe_pct": ratios.get('AROEPCT'),
                    "gross_margin_pct": ratios.get('AGROSMGN'),
                    "dividend_yield": ratios.get('ADIVYIELD'),
                    "dividend_per_share": ratios.get('ADIVSHR'),
                    "eps": ratios.get('AEPSXCLXOR'),
                    "revenue_per_share": ratios.get('AREVPS'),
                    "book_value_per_share": ratios.get('ABVPS'),
                    "cash_per_share": ratios.get('ACSHPS'),
                    "target_price": forecasts.get('TargetPrice'),
                    "proj_pe": forecasts.get('ProjPE'),
                    "proj_eps": forecasts.get('ProjEPS'),
                    "proj_sales": forecasts.get('ProjSales'),
                    "proj_profit": forecasts.get('ProjProfit'),
                    "recommendation_score": forecasts.get('ConsRecom'),
                    "xml_52w_low": ratios.get('NLOW'),
                    "xml_52w_high": ratios.get('NHIG'),
                    "xml_last_price": ratios.get('NPRICE'),
                    "xml_vol_10d_avg": ratios.get('VOL10DAVG'),
                    "sector": None, # Will populate later
                    "industry": get_text(".//Industry[@type='TRBC']"),
                    "employees": get_text(".//CoGeneralInfo/Employees"),
                    "business_summary": biz_sum,
                    "financial_summary": fin_sum,
                    "officers_json": json.dumps(officers),
                    "currency": root.find(".//Ratios").attrib.get('PriceCurrency') if root.find(".//Ratios") is not None else 'INR',
                    "last_fundamental_update": last_updated
                }

                # Try to find EV/EBITDA again - some XMLs use EV and AEBITD separately
                if not data["ev_ebitda"] and ratios.get('EV') and ratios.get('AEBITD'):
                    try:
                        data["ev_ebitda"] = float(ratios.get('EV')) / float(ratios.get('AEBITD'))
                    except: pass

                # SQL Execution
                cols = ", ".join(data.keys())
                placeholders = ", ".join(["%s"] * len(data))
                cur.execute(f"INSERT INTO stock_fundamentals ({cols}) VALUES ({placeholders})", list(data.values()))
                print(f"   ✅ Flattened: {ticker}")

            except Exception as e:
                print(f"   ❌ Error at {ticker}: {e}")

        conn.commit()
        cur.close()
        conn.close()
        print("\n[SUCCESS] High-Fidelity ETL Complete.")

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    flatten_ibkr_high_fidelity()
