import psycopg2
import xml.etree.ElementTree as ET
from config import DB_CONFIG

def count_all_leaf_nodes():
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
    
    for ticker, xml_str in rows:
        root = ET.fromstring(xml_str)
        nodes = list(root.iter())
        leaf_nodes = [n for n in nodes if len(n) == 0]
        print(f"{ticker}: {len(nodes)} total nodes, {len(leaf_nodes)} leaf nodes.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    count_all_leaf_nodes()
