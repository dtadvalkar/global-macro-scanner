import psycopg2
import xml.etree.ElementTree as ET
from config import DB_CONFIG

def scan_xml_fields():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        cur.execute("SELECT ticker, xml_snapshot FROM raw_ibkr_nse WHERE ticker = 'RELIANCE.NSE';")
        row = cur.fetchone()
        
        if not row or not row[1]:
            print("No XML found for RELIANCE.NSE")
            return

        ticker = row[0]
        xml_str = row[1]
        
        print(f"\n--- Deep XML Scan for {ticker} ({len(xml_str)} bytes) ---")
        
        root = ET.fromstring(xml_str)
        
        # Count all elements with text or attributes
        all_tags = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                all_tags.append((elem.tag, elem.text.strip()))
            for attr, val in elem.attrib.items():
                all_tags.append((f"{elem.tag}[{attr}]", val))

        print(f"Total data-bearing nodes found: {len(all_tags)}")
        
        # Group by major sections
        sections = ['CoIDs', 'Issues', 'PeerGroup', 'Performance', 'Ratios', 'FinancialSummary']
        for sec in sections:
            found = root.find(f".//{sec}")
            if found is not None:
                # Count children
                count = len(list(found.iter()))
                print(f"  Section <{sec}>: Found {count} data fields.")
            else:
                print(f"  Section <{sec}>: Not found in this snapshot.")

        # Show some specific "Juicy" fields
        print("\n--- Sample Fundamental Fields Found ---")
        targets = [
            ".//Ratio[@Type='PricetoEarnings']",
            ".//Ratio[@Type='QuickRatio']",
            ".//Ratio[@Type='CurrentRatio']",
            ".//Ratio[@Type='DividendYield']",
            ".//Value[@Type='MarketCapitalization']",
            ".//Value[@Type='PriceHigh52Weeks']",
            ".//Value[@Type='PriceLow52Weeks']"
        ]
        
        for t in targets:
            node = root.find(t)
            if node is not None:
                print(f"  {t.split('=')[-1].strip(']')}: {node.text}")
            else:
                # Try finding by looking for any Value or Ratio
                pass

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scan_xml_fields()
