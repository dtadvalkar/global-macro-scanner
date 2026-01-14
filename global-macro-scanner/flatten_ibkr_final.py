import psycopg2
import xml.etree.ElementTree as ET
import json
from datetime import datetime
from config import DB_CONFIG

# Mapping of Reuters FieldNames to our Database Column Names
RATIO_MAP = {
    'MKTCAP': 'mkt_cap_usd',
    'APEEXCLXOR': 'pe_ratio',
    'APRICE2BK': 'price_to_book',
    'APR2REV': 'price_to_revenue',
    'EV': 'ev',
    'AEBITD': 'ebitda',
    'AREV': 'revenue_annual',
    'ANIAC': 'net_income_annual',
    'AROEPCT': 'roe_pct',
    'AGROSMGN': 'gross_margin_pct',
    'ADIVYIELD': 'dividend_yield_pct',
    'ADIVSHR': 'dividend_per_share',
    'AEPSXCLXOR': 'eps_basic',
    'AREVPS': 'revenue_per_share',
    'ABVPS': 'book_value_per_share',
    'ACSHPS': 'cash_per_share',
    'ACFSHR': 'cash_flow_per_share',
    'NLOW': 'xml_52w_low',
    'NHIG': 'xml_52w_high',
    'NPRICE': 'xml_last_price',
    'VOL10DAVG': 'xml_vol_10d_avg',
    'PDATE': 'xml_last_price_date'
}

FORECAST_MAP = {
    'TargetPrice': 'target_price',
    'ProjPE': 'proj_pe',
    'ProjEPS': 'proj_eps',
    'ProjEPSQ': 'proj_eps_q',
    'ProjSales': 'proj_sales',
    'ProjSalesQ': 'proj_sales_q',
    'ProjProfit': 'proj_profit',
    'ProjDPS': 'proj_dps',
    'ProjLTGrowthRate': 'proj_lt_growth',
    'ConsRecom': 'recommendation_score'
}

def flatten_final():
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
                
                -- Valuation
                mkt_cap_usd              NUMERIC,
                pe_ratio                 NUMERIC,
                price_to_book            NUMERIC,
                price_to_revenue         NUMERIC,
                ev                       NUMERIC,
                ebitda                   NUMERIC,
                revenue_annual           NUMERIC,
                net_income_annual        NUMERIC,
                
                -- Performance
                roe_pct                  NUMERIC,
                gross_margin_pct         NUMERIC,
                dividend_yield_pct       NUMERIC,
                dividend_per_share       NUMERIC,
                
                -- Per Share
                eps_basic                NUMERIC,
                revenue_per_share        NUMERIC,
                book_value_per_share     NUMERIC,
                cash_per_share           NUMERIC,
                cash_flow_per_share      NUMERIC,
                
                -- Forecasts
                target_price             NUMERIC,
                proj_pe                  NUMERIC,
                proj_eps                 NUMERIC,
                proj_eps_q               NUMERIC,
                proj_sales               NUMERIC,
                proj_sales_q             NUMERIC,
                proj_profit              NUMERIC,
                proj_dps                 NUMERIC,
                proj_lt_growth           NUMERIC,
                recommendation_score     NUMERIC,
                
                -- Technical
                xml_52w_low              NUMERIC,
                xml_52w_high             NUMERIC,
                xml_last_price           NUMERIC,
                xml_vol_10d_avg          NUMERIC,
                xml_last_price_date      DATE,
                
                -- Profile
                sector                   TEXT,
                industry                 TEXT,
                employees                INTEGER,
                business_summary         TEXT,
                financial_summary        TEXT,
                officers_json            JSONB,
                
                -- Meta
                currency                 TEXT,
                last_fundamental_update  TIMESTAMP
            );
        """)
        conn.commit()

        cur.execute("SELECT ticker, xml_snapshot, last_updated FROM raw_ibkr_nse WHERE xml_snapshot IS NOT NULL;")
        rows = cur.fetchall()
        print(f"[ETL] Flattening {len(rows)} records with 50+ fields...")

        for ticker, xml_str, last_updated in rows:
            try:
                root = ET.fromstring(xml_str)
                # Helpers
                def get_t(p):
                    n = root.find(p)
                    val = n.text.strip() if n is not None and n.text else None
                    if val is not None and len(val) == 0: return None
                    return val

                def clean_num(val):
                    if val is None: return None
                    val = val.strip()
                    if not val: return None
                    try:
                        return float(val)
                    except: return None

                # Initialize data
                data = {col: None for col in [
                    'ticker', 'company_name', 'mkt_cap_usd', 'pe_ratio', 'price_to_book',
                    'price_to_revenue', 'ev', 'ebitda', 'revenue_annual', 'net_income_annual',
                    'roe_pct', 'gross_margin_pct', 'dividend_yield_pct', 'dividend_per_share',
                    'eps_basic', 'revenue_per_share', 'book_value_per_share', 'cash_per_share',
                    'cash_flow_per_share', 'target_price', 'proj_pe', 'proj_eps', 'proj_eps_q',
                    'proj_sales', 'proj_sales_q', 'proj_profit', 'proj_dps', 'proj_lt_growth',
                    'recommendation_score', 'xml_52w_low', 'xml_52w_high', 'xml_last_price',
                    'xml_vol_10d_avg', 'xml_last_price_date', 'sector', 'industry', 'employees',
                    'business_summary', 'financial_summary', 'officers_json', 'currency',
                    'last_fundamental_update'
                ]}

                data['ticker'] = ticker
                data['company_name'] = get_t(".//CoID[@Type='CompanyName']")
                
                # 1. Map Ratios
                for r in root.findall(".//Ratio"):
                    fname = r.attrib.get('FieldName')
                    if fname in RATIO_MAP:
                        data[RATIO_MAP[fname]] = clean_num(r.text)

                # 2. Map Forecasts (Mean Forecast - Consensus)
                for fv in root.findall(".//ForecastData/Ratio"):
                    fname = fv.attrib.get('FieldName')
                    # Look for Mean Value in CURR period
                    mean_val = fv.find("./Value[@PeriodType='CURR']") # Some use Mean, some use Value
                    if mean_val is None:
                        mean_val = fv.find("./Mean")
                    
                    if fname in FORECAST_MAP and mean_val is not None:
                        data[FORECAST_MAP[fname]] = clean_num(mean_val.text)

                # 3. Text Info
                for txt in root.findall(".//TextInfo/Text"):
                    t_type = txt.attrib.get('Type')
                    if t_type == "Business Summary": data['business_summary'] = txt.text
                    elif t_type == "Financial Summary": data['financial_summary'] = txt.text

                # 4. Profile
                data['industry'] = get_t(".//Industry[@type='TRBC']")
                data['employees'] = clean_num(get_t(".//CoGeneralInfo/Employees"))
                data['currency'] = root.find(".//Ratios").attrib.get('PriceCurrency') if root.find(".//Ratios") is not None else 'INR'
                data['last_fundamental_update'] = last_updated

                # 5. Officers
                offs = []
                for o in root.findall(".//officers/officer"):
                    fn = o.find("firstName").text if o.find("firstName") is not None else ""
                    ln = o.find("lastName").text if o.find("lastName") is not None else ""
                    tit = o.find("title").text if o.find("title") is not None else ""
                    offs.append({"n": f"{fn} {ln}".strip(), "t": tit})
                data['officers_json'] = json.dumps(offs)

                # SQL
                cols = ", ".join(data.keys())
                placeholders = ", ".join(["%s"] * len(data))
                cur.execute(f"INSERT INTO stock_fundamentals ({cols}) VALUES ({placeholders})", list(data.values()))
                print(f"   ✅ {ticker} flattened (High-Fidelity).")

            except Exception as e:
                print(f"   ❌ Error {ticker}: {e}")

        conn.commit()
        cur.close()
        conn.close()
        print("\n🚀 SUCCESS: stock_fundamentals is now High-Fidelity.")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    flatten_final()
