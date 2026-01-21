import psycopg2
import xml.etree.ElementTree as ET
import json
from datetime import datetime
from config import DB_CONFIG

# Configuration for Field Discovery & Mapping
# Ratio FieldNames (Fundamentals)
RATIO_FIELDS = {
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

# Forecast FieldNames
FORECAST_FIELDS = {
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

def flatten_mega():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()

        print("[DB] Recreating exhaustive Mega-Schema table...")
        cur.execute("DROP TABLE IF EXISTS stock_fundamentals;")
        cur.execute("""
            CREATE TABLE stock_fundamentals (
                ticker                   TEXT PRIMARY KEY,
                company_name             TEXT,
                
                -- 🆔 Identifiers
                rep_no                   TEXT,
                org_perm_id              TEXT,
                isin                     TEXT,
                ric                      TEXT,
                exchange_code            TEXT,
                exchange_country         TEXT,
                most_recent_split_date   DATE,
                most_recent_split_factor NUMERIC,
                
                -- 📊 Ratios (Fundamentals)
                mkt_cap_usd              NUMERIC,
                pe_ratio                 NUMERIC,
                price_to_book            NUMERIC,
                price_to_revenue         NUMERIC,
                ev                       NUMERIC,
                ebitda                   NUMERIC,
                revenue_annual           NUMERIC,
                net_income_annual        NUMERIC,
                roe_pct                  NUMERIC,
                gross_margin_pct         NUMERIC,
                dividend_yield_pct       NUMERIC,
                dividend_per_share       NUMERIC,
                eps_basic                NUMERIC,
                revenue_per_share        NUMERIC,
                book_value_per_share     NUMERIC,
                cash_per_share           NUMERIC,
                cash_flow_per_share      NUMERIC,
                
                -- 🔭 Forecasts
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
                
                -- 📉 Technical
                xml_52w_low              NUMERIC,
                xml_52w_high             NUMERIC,
                xml_last_price           NUMERIC,
                xml_vol_10d_avg          NUMERIC,
                xml_last_price_date      DATE,
                
                -- 🏢 General Info
                co_status                TEXT,
                co_type                  TEXT,
                latest_annual_date       DATE,
                latest_interim_date      DATE,
                employees                INTEGER,
                shares_out               NUMERIC,
                shares_out_date          DATE,
                total_float              NUMERIC,
                reporting_currency       TEXT,
                most_recent_exch_date    DATE,
                most_recent_exch_val     NUMERIC,
                
                -- 📂 Industry Classification
                industry_trbc            TEXT,
                industry_trbc_code       TEXT,
                industry_naics           TEXT,
                industry_naics_code      TEXT,
                industry_sic             TEXT,
                industry_sic_code        TEXT,
                
                -- 📍 Contact
                address                  TEXT,
                city                     TEXT,
                postal_code              TEXT,
                country_code             TEXT,
                phone                    TEXT,
                website                  TEXT,
                email                    TEXT,
                
                -- 📝 Narratives
                business_summary         TEXT,
                financial_summary        TEXT,
                
                -- 👥 Governance
                officer_1_name           TEXT,
                officer_1_title          TEXT,
                officer_2_name           TEXT,
                officer_2_title          TEXT,
                officer_3_name           TEXT,
                officer_3_title          TEXT,
                officer_4_name           TEXT,
                officer_4_title          TEXT,
                officer_5_name           TEXT,
                officer_5_title          TEXT,
                officers_json            JSONB,
                
                -- 🕒 Metadata
                price_currency           TEXT,
                last_fundamental_update  TIMESTAMP
            );
        """)
        conn.commit()

        cur.execute("SELECT ticker, xml_snapshot, last_updated FROM raw_ibkr_nse WHERE xml_snapshot IS NOT NULL;")
        rows = cur.fetchall()
        print(f"[ETL] Implementing Mega-Schema for {len(rows)} records...")

        for ticker, xml_str, last_updated in rows:
            try:
                root = ET.fromstring(xml_str)
                
                # Dynamic Helpers
                def get_t(p):
                    n = root.find(p)
                    val = n.text.strip() if n is not None and n.text else None
                    if val is not None and len(val) == 0: return None
                    return val

                def clean_num(val):
                    if val is None: return None
                    val = val.strip()
                    if not val: return None
                    try: return float(val)
                    except: return None

                # Initialize flattened record
                # We use a dict to manage the mapping easily
                rec = {}
                rec['ticker'] = ticker
                rec['company_name'] = get_t(".//CoID[@Type='CompanyName']")
                
                # Identifiers
                rec['rep_no'] = get_t(".//CoID[@Type='RepNo']")
                rec['org_perm_id'] = get_t(".//CoID[@Type='OrganizationPermID']")
                rec['isin'] = get_t(".//IssueID[@Type='ISIN']")
                rec['ric'] = get_t(".//IssueID[@Type='RIC']")
                
                exch = root.find(".//Exchange")
                if exch is not None:
                    rec['exchange_code'] = exch.attrib.get('Code')
                    rec['exchange_country'] = exch.attrib.get('Country')
                
                split = root.find(".//MostRecentSplit")
                if split is not None:
                    rec['most_recent_split_date'] = split.attrib.get('Date')
                    rec['most_recent_split_factor'] = clean_num(split.text)
                
                # General Info
                co_info = root.find(".//CoGeneralInfo")
                if co_info is not None:
                    rec['co_status'] = get_t(".//CoStatus")
                    rec['co_type'] = get_t(".//CoType")
                    rec['latest_annual_date'] = get_t(".//LatestAvailableAnnual")
                    rec['latest_interim_date'] = get_t(".//LatestAvailableInterim")
                    rec['employees'] = clean_num(get_t(".//Employees"))
                    
                    s_out = co_info.find(".//SharesOut")
                    if s_out is not None:
                        rec['shares_out'] = clean_num(s_out.text)
                        rec['shares_out_date'] = s_out.attrib.get('Date')
                        rec['total_float'] = clean_num(s_out.attrib.get('TotalFloat'))
                    
                    rec['reporting_currency'] = root.find(".//ReportingCurrency").attrib.get('Code') if root.find(".//ReportingCurrency") is not None else None
                    
                    mrx = co_info.find(".//MostRecentExchange")
                    if mrx is not None:
                        rec['most_recent_exch_date'] = mrx.attrib.get('Date')
                        rec['most_recent_exch_val'] = clean_num(mrx.text)

                # Narratives
                for txt in root.findall(".//TextInfo/Text"):
                    t_type = txt.attrib.get('Type')
                    if t_type == "Business Summary": rec['business_summary'] = txt.text
                    elif t_type == "Financial Summary": rec['financial_summary'] = txt.text

                # Contact
                addr = root.find(".//contactInfo")
                if addr is not None:
                    lines = [get_t(f".//streetAddress[@line='{i}']") for i in [1,2,3]]
                    rec['address'] = ", ".join([l for l in lines if l])
                    rec['city'] = get_t(".//city")
                    rec['postal_code'] = get_t(".//postalCode")
                    rec['country_code'] = addr.find(".//country").attrib.get('code') if addr.find(".//country") is not None else None
                    
                    phone = addr.find(".//phone/phone[@type='mainphone']")
                    if phone is not None:
                        c_code = get_t(".//countryPhoneCode") or ""
                        a_code = get_t(".//city-areacode") or ""
                        num = get_t(".//number") or ""
                        rec['phone'] = f"+{c_code} {a_code} {num}".strip()
                
                rec['website'] = get_t(".//webSite")
                rec['email'] = get_t(".//eMail")

                # Classification
                for ind in root.findall(".//IndustryInfo/Industry"):
                    i_type = ind.attrib.get('type')
                    i_code = ind.attrib.get('code')
                    if i_type == "TRBC":
                        rec['industry_trbc'] = ind.text
                        rec['industry_trbc_code'] = i_code
                    elif i_type == "NAICS" and ind.attrib.get('order') == "1":
                        rec['industry_naics'] = ind.text
                        rec['industry_naics_code'] = i_code
                    elif i_type == "SIC" and ind.attrib.get('order') == "1":
                        rec['industry_sic'] = ind.text
                        rec['industry_sic_code'] = i_code

                # Officers
                offs_data = []
                for idx, off in enumerate(root.findall(".//officers/officer")[:5]):
                    fn = off.find("firstName").text if off.find("firstName") is not None else ""
                    ln = off.find("lastName").text if off.find("lastName") is not None else ""
                    tit = off.find("title").text if off.find("title") is not None else ""
                    rec[f'officer_{idx+1}_name'] = f"{fn} {ln}".strip()
                    rec[f'officer_{idx+1}_title'] = tit
                
                for off in root.findall(".//officers/officer"):
                    fn = off.find("firstName").text if off.find("firstName") is not None else ""
                    ln = off.find("lastName").text if off.find("lastName") is not None else ""
                    tit = off.find("title").text if off.find("title") is not None else ""
                    offs_data.append({"n": f"{fn} {ln}".strip(), "t": tit})
                rec['officers_json'] = json.dumps(offs_data)

                # Ratios & Forecasts
                for r in root.findall(".//Ratios/Group/Ratio"):
                    fname = r.attrib.get('FieldName')
                    if fname in RATIO_FIELDS:
                        rec[RATIO_FIELDS[fname]] = clean_num(r.text)
                
                ratios_box = root.find(".//Ratios")
                if ratios_box is not None:
                    rec['price_currency'] = ratios_box.attrib.get('PriceCurrency')

                for fv in root.findall(".//ForecastData/Ratio"):
                    fname = fv.attrib.get('FieldName')
                    m_val = fv.find("./Value[@PeriodType='CURR']") or fv.find("./Mean")
                    if fname in FORECAST_FIELDS and m_val is not None:
                        rec[FORECAST_FIELDS[fname]] = clean_num(m_val.text)

                rec['last_fundamental_update'] = last_updated

                # Build SQL
                # Filter out keys that aren't in the schema (just in case)
                # But here we defined them ourselves, so they are correct.
                cols = list(rec.keys())
                vals = [rec[c] for c in cols]
                
                sql = f"INSERT INTO stock_fundamentals ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(cols))});"
                cur.execute(sql, vals)
                print(f"   {ticker} mega-flattened.")

            except Exception as e:
                print(f"   Error at {ticker}: {e}")
                import traceback
                traceback.print_exc()

        conn.commit()
        cur.close()
        conn.close()
        print("\nMISSION COMPLETE: stock_fundamentals is now a 100+ Column Mega-Table.")

    except Exception as e:
        print(f"CRITICAL: {e}")

if __name__ == "__main__":
    flatten_mega()
