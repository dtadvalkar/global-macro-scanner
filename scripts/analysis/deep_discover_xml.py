import psycopg2
import xml.etree.ElementTree as ET
from config import DB_CONFIG

def deep_discover_xml():
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()
    cur.execute("SELECT ticker, xml_snapshot FROM raw_ibkr_nse WHERE xml_snapshot IS NOT NULL;")
    rows = cur.fetchall()
    
    all_paths = set()
    ratios = set()
    forecasts = set()

    def get_path(node, current_path=""):
        tag = node.tag
        path = f"{current_path}/{tag}" if current_path else tag
        
        # Capture attributes
        for attr in node.attrib:
            all_paths.add(f"{path}@{attr}")
            
        # Specific capture for our data blocks
        if tag == "Ratio":
            fname = node.attrib.get('FieldName')
            if fname:
                if "ForecastData" in path:
                    forecasts.add(fname)
                else:
                    ratios.add(fname)
        
        # Recurse
        for child in node:
            get_path(child, path)

    for ticker, xml_str in rows:
        root = ET.fromstring(xml_str)
        get_path(root)

    print(f"\nDiscovered {len(ratios)} Ratio FieldNames")
    print(f"Discovered {len(forecasts)} Forecast FieldNames")
    print(f"Discovered {len(all_paths)} Unique Tag/Attribute Paths")
    
    print("\n--- Top Level Tags ---")
    top_level = {p.split('/')[1] if '/' in p else p for p in all_paths}
    print(sorted(list(top_level)))

    # Let's see some interesting paths that describe company metadata
    print("\n--- Example Data Paths (First 50) ---")
    sorted_paths = sorted(list(all_paths))
    for p in sorted_paths[:50]:
        print(p)

    cur.close()
    conn.close()

if __name__ == "__main__":
    deep_discover_xml()
