import psycopg2
import xml.etree.ElementTree as ET
from config import DB_CONFIG

def debug_tcs():
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()
    cur.execute("SELECT xml_snapshot FROM raw_ibkr_nse WHERE ticker = 'TCS.NSE'")
    xml_str = cur.fetchone()[0]
    
    root = ET.fromstring(xml_str)
    ratios = {r.attrib.get('FieldName'): r.text for r in root.findall(".//Ratio")}
    
    print("--- TCS.NSE Ratios ---")
    for k, v in ratios.items():
        if 'CAP' in k or 'VAL' in k or 'PRICE' in k:
            print(f"{k}: {v}")
            
    print("\nFull Ratios:")
    import pprint
    pprint.pprint(ratios)
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    debug_tcs()
