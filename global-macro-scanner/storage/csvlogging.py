import pandas as pd
import os

def log_catches(catches):
    """Save to CSV"""
    for catch in catches:
        df = pd.DataFrame([catch])
        mode = 'a' if os.path.exists('recent_catches.csv') else 'w'
        header = not os.path.exists('recent_catches.csv')
        df.to_csv('recent_catches.csv', mode=mode, header=header, index=False)
        print(f"📊 Saved {catch['symbol']} to recent_catches.csv")
