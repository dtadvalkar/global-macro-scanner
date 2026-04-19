import pandas as pd
import os
from datetime import datetime

def log_catches(catches):
    """Save catches to CSV with a fixed schema and consistent formatting."""
    if not catches:
        return

    # Define standard columns to ensure consistency
    columns = ['timestamp', 'ticker', 'price', 'volume', 'usd_mcap', 'pct_from_low', 'reason']
    
    file_path = 'recent_catches.csv'
    
    # Prepare data
    rows = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for c in catches:
        row = {
            'timestamp': c.get('timestamp', timestamp),
            'ticker': c.get('ticker', c.get('symbol', 'UNKNOWN')),
            'price': round(float(c.get('price', 0)), 2),
            'volume': int(c.get('volume', 0)),
            'usd_mcap': round(float(c.get('usd_mcap', 0)), 2),
            'pct_from_low': round(float(c.get('pct_from_low', 0)), 4),
            'reason': c.get('reason', '')
        }
        rows.append(row)
    
    new_df = pd.DataFrame(rows, columns=columns)
    
    if os.path.exists(file_path):
        # Read existing to preserve headers and append
        try:
            old_df = pd.read_csv(file_path)
            # Filter to only standard columns
            old_df = old_df[columns]
            combined_df = pd.concat([old_df, new_df], ignore_index=True)
        except Exception:
            # If reading fails (mangled file), start fresh
            combined_df = new_df
    else:
        combined_df = new_df

    # Save finalized CSV
    try:
        combined_df.to_csv(file_path, index=False)
        for c in rows:
            print(f"📊 Logged {c['ticker']} to {file_path}")
    except PermissionError:
        print(f"\n❌ [PERMISSION ERROR] Could not save to '{file_path}'.")
        print("💡 Action: Please CLOSE the CSV file if it's open in Excel or another program.")
    except Exception as e:
        print(f"❌ Error saving CSV: {e}")
