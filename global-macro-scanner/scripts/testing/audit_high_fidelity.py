import psycopg2
from config import DB_CONFIG

def audit_final():
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
                mkt_cap_usd, 
                pe_ratio, 
                target_price, 
                roe_pct,
                proj_eps,
                xml_52w_low,
                left(business_summary, 50) || '...' as bio
            FROM stock_fundamentals;
        """)
        rows = cur.fetchall()
        
        print(f"\n--- 🧪 HIGH-FIDELITY DATA AUDIT ---")
        print(f"{'Ticker':<12} | {'Mkt Cap':<8} | {'PE':<6} | {'Target':<8} | {'ROE%':<6} | {'Pr EPS':<6} | {'Bio'}")
        print("-" * 90)
        
        for r in rows:
            ticker, mc, pe, tp, roe, peps, low, bio = r
            mc_s = f"{float(mc)/1e9:.1f}B" if mc else "n/a"
            pe_s = f"{float(pe):.1f}" if pe else "n/a"
            tp_s = f"{float(tp):.1f}" if tp else "n/a"
            roe_s = f"{float(roe):.1f}" if roe else "n/a"
            peps_s = f"{float(peps):.1f}" if peps else "n/a"
            
            print(f"{ticker:<12} | {mc_s:<8} | {pe_s:<6} | {tp_s:<8} | {roe_s:<6} | {peps_s:<6} | {bio}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    audit_final()
