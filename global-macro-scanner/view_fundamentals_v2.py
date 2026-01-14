import psycopg2
from config import DB_CONFIG

def view_high_fidelity():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                ticker, 
                company_name, 
                mkt_cap_usd, 
                pe_ratio, 
                target_price, 
                recommendation_score,
                xml_52w_low
            FROM stock_fundamentals;
        """)
        rows = cur.fetchall()
        
        print(f"\n--- stock_fundamentals High-Fidelity Audit ({len(rows)} rows) ---")
        cols = ['Ticker', 'Name', 'Mkt Cap (B)', 'PE', 'Target', 'Rec (1-5)', '52W Low']
        fmt = "{:<12} | {:<25} | {:<12} | {:<8} | {:<10} | {:<10} | {:<10}"
        print(fmt.format(*cols))
        print("-" * 105)
        
        for row in rows:
            ticker, name, mkt_cap, pe, target, rec, low_52w = row
            mkt_cap_str = f"{float(mkt_cap)/1e9:.2f}B" if mkt_cap else "None"
            pe_str = f"{float(pe):.2f}" if pe else "None"
            target_str = f"{float(target):.2f}" if target else "None"
            rec_str = f"{float(rec):.2f}" if rec else "None"
            low_str = f"{float(low_52w):.2f}" if low_52w else "None"
            
            print(fmt.format(
                ticker, name[:25], mkt_cap_str, pe_str, target_str, rec_str, low_str
            ))
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    view_high_fidelity()
