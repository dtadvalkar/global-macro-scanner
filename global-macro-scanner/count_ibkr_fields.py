import xml.etree.ElementTree as ET
import psycopg2
from config import DB_CONFIG

def count_ibkr_fields():
    conn = psycopg2.connect(
        dbname=DB_CONFIG['db_name'],
        user=DB_CONFIG['db_user'],
        password=DB_CONFIG['db_pass'],
        host=DB_CONFIG['db_host'],
        port=DB_CONFIG['db_port']
    )
    cur = conn.cursor()
    cur.execute("SELECT xml_snapshot FROM raw_ibkr_nse WHERE ticker = 'RELIANCE.NSE';")
    row = cur.fetchone()
    if not row or not row[0]:
        print("XML not found.")
        return

    root = ET.fromstring(row[0])
    
    # We define a "field" as any leaf node that contains text or values
    fields = []
    for elem in root.iter():
        # Check text
        if elem.text and elem.text.strip():
            # For Ratio tags, the unique key is the FieldName attribute
            if elem.tag == 'Ratio' and 'FieldName' in elem.attrib:
                fields.append(f"Ratio.{elem.attrib['FieldName']}")
            elif elem.tag == 'Value' and 'Type' in elem.attrib:
                fields.append(f"Value.{elem.attrib['Type']}")
            else:
                fields.append(elem.tag)
        # Check attributes
        for attr in elem.attrib:
            fields.append(f"{elem.tag}.{attr}")

    unique_fields = set(fields)
    print(f"Unique Data Fields in IBKR XML: {len(unique_fields)}")
    
    # Just to be sure about the 'xml_ratios' column too
    cur.execute("SELECT xml_ratios FROM raw_ibkr_nse WHERE ticker = 'RELIANCE.NSE';")
    row_ratios = cur.fetchone()
    if row_ratios and row_ratios[0]:
        print(f"XML Ratios Length: {len(row_ratios[0])} bytes")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    count_ibkr_fields()
