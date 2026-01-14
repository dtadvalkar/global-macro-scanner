import psycopg2
from config import DB_CONFIG

def view_fundamentals():
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM stock_fundamentals;")
        rows = cur.fetchall()
        
        print(f"\n--- stock_fundamentals ({len(rows)} rows) ---")
        cols = [
            'Ticker', 'Name', 'Industry', 'Mkt Cap', 
            'PE', '52W L', '52W H', 'Div %', 'Curr', 'Updated'
        ]
        
        # Format header
        fmt = "{:<12} | {:<25} | {:<20} | {:<12} | {:<8} | {:<8} | {:<8} | {:<6} | {:<4} | {:<20}"
        print(fmt.format(*cols))
        print("-" * 140)
        
        for row in rows:
            # row: ticker, name, sector, industry, mkt_cap, pe, low, high, div, curr, update
            # Note: My SQL select order might differ slightly, let's just map it.
            # ticker, name, sector, industry, mkt_cap, pe, low, high, div, curr, update
            # Wait, let's get the specific columns to be safe.
            pass

        # Better to query by name
        cur.execute("""
            SELECT ticker, company_name, industry, market_cap_usd, pe_ratio, 
                   fifty_two_w_low, fifty_two_w_high, dividend_yield, currency, last_fundamental_update 
            FROM stock_fundamentals;
        """)
        rows = cur.fetchall()
        for row in rows:
            # Format numbers to be readable
            ticker, name, industry, mkt_cap, pe, low, high, div, curr, updated = row
            mkt_cap_str = f"{float(mkt_cap)/1e9:.2f}B" if mkt_cap else "None"
            pe_str = f"{float(pe):.2f}" if pe else "None"
            low_str = str(low) if low else "None"
            high_str = str(high) if high else "None"
            div_str = f"{float(div):.2f}" if div else "None"
            
            print(fmt.format(
                ticker, name[:25], str(industry)[:20], 
                mkt_cap_str, pe_str, low_str, high_str, div_str, curr, str(updated)[:19]
            ))
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    view_fundamentals()
