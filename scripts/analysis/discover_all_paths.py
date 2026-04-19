import psycopg2
import xml.etree.ElementTree as ET
from config import DB_CONFIG

def get_all_paths(element, path=""):
    tag = element.tag
    current_path = f"{path}/{tag}" if path else tag
    paths = set()
    
    # Add path if it's a leaf node
    if len(element) == 0:
        if element.text and element.text.strip():
            paths.add(current_path)
    
    # Add paths for attributes
    for attr in element.attrib:
        paths.add(f"{current_path}@{attr}")
        
    for child in element:
        paths.update(get_all_paths(child, current_path))
        
    return paths

def discover():
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
    
    global_paths = set()
    for (xml_str,) in rows:
        root = ET.fromstring(xml_str)
        global_paths.update(get_all_paths(root))
        
    print(f"\nDiscovered {len(global_paths)} unique data points (tags/attributes).")
    for p in sorted(list(global_paths)):
        print(p)

    cur.close()
    conn.close()

if __name__ == "__main__":
    discover()
