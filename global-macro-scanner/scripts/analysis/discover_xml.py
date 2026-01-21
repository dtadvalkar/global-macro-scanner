import psycopg2
import xml.etree.ElementTree as ET
from config import DB_CONFIG

def discover_all_xml_fields():
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()
    cur.execute("SELECT xml_snapshot FROM raw_ibkr_nse WHERE xml_snapshot IS NOT NULL;")
    rows = cur.fetchall()
    
    ratio_fields = set()
    forecast_fields = set()
    other_tags = set()
    
    for (xml_str,) in rows:
        root = ET.fromstring(xml_str)
        # Scan Ratios
        for r in root.findall(".//Ratio"):
            fname = r.attrib.get('FieldName')
            if fname: ratio_fields.add(fname)
            
        # Scan Forecasts
        for f in root.findall(".//ForecastData/Ratio"):
            fname = f.attrib.get('FieldName')
            if fname: forecast_fields.add(fname)
            
        # Scan General Tags
        for elem in root.iter():
            other_tags.add(elem.tag)

    print("\n--- Discovered Ratio Fields ---")
    print(sorted(list(ratio_fields)))
    print(f"Total: {len(ratio_fields)}")
    
    print("\n--- Discovered Forecast Fields ---")
    print(sorted(list(forecast_fields)))
    print(f"Total: {len(forecast_fields)}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    discover_all_xml_fields()
