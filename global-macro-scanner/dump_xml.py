import psycopg2
from config import DB_CONFIG

def dump_xml():
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
    if row and row[0]:
        with open('reliance_full.xml', 'w', encoding='utf-8') as f:
            f.write(row[0])
        print("Dumped RELIANCE.NSE XML to reliance_full.xml")
    else:
        print("XML not found.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    dump_xml()
