#!/usr/bin/env python3
"""
Flatten raw IBKR fundamentals XML into the curated `stock_fundamentals` table.

Recovered in Task 11 from the canonical mega-schema flattener (commit
`b55b8de^`, scripts/etl/ibkr/flatten_ibkr_mega.py — the script that produced
the original 398 NSE rows). Adapted for multi-exchange + UPSERT semantics:

  - Reads from `ibkr_fundamentals` (current raw store, written by
    collect_ibkr_fundamentals.py), not the legacy `raw_ibkr_nse`.
  - `CREATE TABLE IF NOT EXISTS` + per-row `INSERT … ON CONFLICT (ticker)
    DO UPDATE SET …` — never DROPs (would have wiped existing exchanges).
  - Optional `--exchange` filter by yfinance suffix; optional `--replace`
    DELETE-by-suffix to handle delistings.
  - Per-row commit + rollback on error so one bad XML doesn't poison the rest.
  - `price_currency` falls back to MARKET_REGISTRY[exchange]['ibkr_currency']
    when the XML doesn't carry it (instead of the legacy hardcoded 'INR').

Source : `ibkr_fundamentals` (raw XML)
Target : `stock_fundamentals` (~80 columns, keyed by yf-format ticker)

USAGE:
    python -m scripts.etl.ibkr.flatten_ibkr_final
    python -m scripts.etl.ibkr.flatten_ibkr_final --exchange JSE
    python -m scripts.etl.ibkr.flatten_ibkr_final --exchange NSE --replace
"""
import argparse
import io
import json
import sys
import xml.etree.ElementTree as ET

import psycopg2

from config import DB_CONFIG
from config.markets import MARKET_REGISTRY, exchange_from_yf_ticker, get_yf_suffix

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


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
    'PDATE': 'xml_last_price_date',
}

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
    'ConsRecom': 'recommendation_score',
}


# Order matters: matches the live stock_fundamentals schema.
SCHEMA_COLUMNS = [
    'ticker', 'company_name',
    # Identifiers
    'rep_no', 'org_perm_id', 'isin', 'ric',
    'exchange_code', 'exchange_country',
    'most_recent_split_date', 'most_recent_split_factor',
    # Ratios (Fundamentals)
    'mkt_cap_usd', 'pe_ratio', 'price_to_book', 'price_to_revenue',
    'ev', 'ebitda', 'revenue_annual', 'net_income_annual',
    'roe_pct', 'gross_margin_pct', 'dividend_yield_pct',
    'dividend_per_share', 'eps_basic', 'revenue_per_share',
    'book_value_per_share', 'cash_per_share', 'cash_flow_per_share',
    # Forecasts
    'target_price', 'proj_pe', 'proj_eps', 'proj_eps_q',
    'proj_sales', 'proj_sales_q', 'proj_profit', 'proj_dps',
    'proj_lt_growth', 'recommendation_score',
    # Technical
    'xml_52w_low', 'xml_52w_high', 'xml_last_price',
    'xml_vol_10d_avg', 'xml_last_price_date',
    # General Info
    'co_status', 'co_type', 'latest_annual_date', 'latest_interim_date',
    'employees', 'shares_out', 'shares_out_date', 'total_float',
    'reporting_currency', 'most_recent_exch_date', 'most_recent_exch_val',
    # Industry Classification
    'industry_trbc', 'industry_trbc_code', 'industry_naics',
    'industry_naics_code', 'industry_sic', 'industry_sic_code',
    # Contact
    'address', 'city', 'postal_code', 'country_code',
    'phone', 'website', 'email',
    # Narratives
    'business_summary', 'financial_summary',
    # Officers
    'officer_1_name', 'officer_1_title',
    'officer_2_name', 'officer_2_title',
    'officer_3_name', 'officer_3_title',
    'officer_4_name', 'officer_4_title',
    'officer_5_name', 'officer_5_title',
    'officers_json',
    # Meta
    'price_currency', 'last_fundamental_update',
]


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS stock_fundamentals (
    ticker                   TEXT PRIMARY KEY,
    company_name             TEXT,

    rep_no                   TEXT,
    org_perm_id              TEXT,
    isin                     TEXT,
    ric                      TEXT,
    exchange_code            TEXT,
    exchange_country         TEXT,
    most_recent_split_date   DATE,
    most_recent_split_factor NUMERIC,

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

    xml_52w_low              NUMERIC,
    xml_52w_high             NUMERIC,
    xml_last_price           NUMERIC,
    xml_vol_10d_avg          NUMERIC,
    xml_last_price_date      DATE,

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

    industry_trbc            TEXT,
    industry_trbc_code       TEXT,
    industry_naics           TEXT,
    industry_naics_code      TEXT,
    industry_sic             TEXT,
    industry_sic_code        TEXT,

    address                  TEXT,
    city                     TEXT,
    postal_code              TEXT,
    country_code             TEXT,
    phone                    TEXT,
    website                  TEXT,
    email                    TEXT,

    business_summary         TEXT,
    financial_summary        TEXT,

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

    price_currency           TEXT,
    last_fundamental_update  TIMESTAMP
);
"""


def _parse_xml_to_record(ticker, xml_str, last_updated):
    """Parse one IBKR ReportSnapshot XML into a SCHEMA_COLUMNS-shaped dict."""
    root = ET.fromstring(xml_str)

    def get_t(p):
        n = root.find(p)
        val = n.text.strip() if n is not None and n.text else None
        return val if val else None

    def clean_num(val):
        if val is None:
            return None
        val = val.strip()
        if not val:
            return None
        try:
            return float(val)
        except ValueError:
            return None

    rec = {col: None for col in SCHEMA_COLUMNS}
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

        rep_cur = root.find(".//ReportingCurrency")
        if rep_cur is not None:
            rec['reporting_currency'] = rep_cur.attrib.get('Code')

        mrx = co_info.find(".//MostRecentExchange")
        if mrx is not None:
            rec['most_recent_exch_date'] = mrx.attrib.get('Date')
            rec['most_recent_exch_val'] = clean_num(mrx.text)

    # Narratives
    for txt in root.findall(".//TextInfo/Text"):
        t_type = txt.attrib.get('Type')
        if t_type == "Business Summary":
            rec['business_summary'] = txt.text
        elif t_type == "Financial Summary":
            rec['financial_summary'] = txt.text

    # Contact
    addr = root.find(".//contactInfo")
    if addr is not None:
        lines = [get_t(f".//streetAddress[@line='{i}']") for i in [1, 2, 3]]
        joined = ", ".join([l for l in lines if l])
        rec['address'] = joined or None
        rec['city'] = get_t(".//city")
        rec['postal_code'] = get_t(".//postalCode")
        ctry = addr.find(".//country")
        if ctry is not None:
            rec['country_code'] = ctry.attrib.get('code')

        phone = addr.find(".//phone/phone[@type='mainphone']")
        if phone is not None:
            c_code = get_t(".//countryPhoneCode") or ""
            a_code = get_t(".//city-areacode") or ""
            num = get_t(".//number") or ""
            rec['phone'] = f"+{c_code} {a_code} {num}".strip()

    rec['website'] = get_t(".//webSite")
    rec['email'] = get_t(".//eMail")

    # Industry Classification
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

    # Officers — top 5 named slots + full JSON list
    officers = root.findall(".//officers/officer")
    for idx, off in enumerate(officers[:5]):
        fn = off.find("firstName").text if off.find("firstName") is not None else ""
        ln = off.find("lastName").text if off.find("lastName") is not None else ""
        tit = off.find("title").text if off.find("title") is not None else ""
        rec[f'officer_{idx + 1}_name'] = f"{fn} {ln}".strip()
        rec[f'officer_{idx + 1}_title'] = tit
    offs_data = []
    for off in officers:
        fn = off.find("firstName").text if off.find("firstName") is not None else ""
        ln = off.find("lastName").text if off.find("lastName") is not None else ""
        tit = off.find("title").text if off.find("title") is not None else ""
        offs_data.append({"n": f"{fn} {ln}".strip(), "t": tit})
    rec['officers_json'] = json.dumps(offs_data)

    # Ratios
    for r in root.findall(".//Ratios/Group/Ratio"):
        fname = r.attrib.get('FieldName')
        if fname in RATIO_FIELDS:
            rec[RATIO_FIELDS[fname]] = clean_num(r.text)

    # price_currency: prefer XML's Ratios/@PriceCurrency, fall back to MARKET_REGISTRY
    ratios_box = root.find(".//Ratios")
    xml_currency = ratios_box.attrib.get('PriceCurrency') if ratios_box is not None else None
    if xml_currency:
        rec['price_currency'] = xml_currency
    else:
        ex = exchange_from_yf_ticker(ticker)
        rec['price_currency'] = MARKET_REGISTRY.get(ex, {}).get('ibkr_currency')

    # Forecasts (consensus)
    for fv in root.findall(".//ForecastData/Ratio"):
        fname = fv.attrib.get('FieldName')
        m_val = fv.find("./Value[@PeriodType='CURR']")
        if m_val is None:
            m_val = fv.find("./Mean")
        if fname in FORECAST_FIELDS and m_val is not None:
            rec[FORECAST_FIELDS[fname]] = clean_num(m_val.text)

    rec['last_fundamental_update'] = last_updated
    return rec


def flatten_final(exchange=None, replace=False):
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port'],
    )
    cur = conn.cursor()

    print("[DB] Ensuring stock_fundamentals exists (CREATE IF NOT EXISTS, no DROP)...")
    cur.execute(CREATE_SQL)
    conn.commit()

    if exchange is not None:
        suffix = get_yf_suffix(exchange)
        if not suffix:
            raise ValueError(f"No yf_suffix for exchange {exchange}")
        like_pat = '%' + suffix
        if replace:
            cur.execute(
                "DELETE FROM stock_fundamentals WHERE ticker LIKE %s",
                (like_pat,),
            )
            print(f"[DB] --replace: deleted {cur.rowcount} existing {exchange} ({suffix}) rows")
            conn.commit()
        cur.execute(
            "SELECT ticker, xml_snapshot, last_updated FROM ibkr_fundamentals "
            "WHERE xml_snapshot IS NOT NULL AND ticker LIKE %s ORDER BY ticker",
            (like_pat,),
        )
    else:
        cur.execute(
            "SELECT ticker, xml_snapshot, last_updated FROM ibkr_fundamentals "
            "WHERE xml_snapshot IS NOT NULL ORDER BY ticker"
        )

    rows = cur.fetchall()
    scope = f"exchange={exchange}" if exchange else "all exchanges"
    print(f"[ETL] Flattening {len(rows)} records ({scope})...")

    insert_cols = ", ".join(SCHEMA_COLUMNS)
    placeholders = ", ".join(["%s"] * len(SCHEMA_COLUMNS))
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in SCHEMA_COLUMNS if c != 'ticker')
    upsert_sql = (
        f"INSERT INTO stock_fundamentals ({insert_cols}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT (ticker) DO UPDATE SET {update_set}"
    )

    upserted = 0
    errors = 0
    for ticker, xml_str, last_updated in rows:
        try:
            rec = _parse_xml_to_record(ticker, xml_str, last_updated)
            cur.execute(upsert_sql, [rec[c] for c in SCHEMA_COLUMNS])
            conn.commit()
            upserted += 1
            print(f"   ✅ {ticker} upserted.")
        except Exception as e:
            conn.rollback()
            print(f"   ❌ {ticker}: {e}")
            errors += 1

    cur.close()
    conn.close()
    print(f"\n🚀 Done. Upserted: {upserted}  Errors: {errors}")


def parse_args():
    p = argparse.ArgumentParser(
        description="Flatten ibkr_fundamentals XML into stock_fundamentals (mega-schema, UPSERT).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        '--exchange', default=None,
        choices=sorted(MARKET_REGISTRY.keys()),
        help='Restrict to one exchange (filtered by yfinance suffix). Default: all.',
    )
    p.add_argument(
        '--replace', action='store_true',
        help='With --exchange, DELETE existing rows for that suffix before flattening '
             '(covers delistings). Without --replace, behavior is pure UPSERT.',
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    flatten_final(
        exchange=args.exchange.upper() if args.exchange else None,
        replace=args.replace,
    )
