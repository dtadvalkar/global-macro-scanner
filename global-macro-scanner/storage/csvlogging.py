import pandas as pd
import os

def log_catches(catches):
    """Save to CSV"""
    """Save to CSV"""
    from datetime import datetime
    
    # If catches is empty, nothing to do
    if not catches:
        return

    for catch in catches:
        # Ensure timestamp exists at the moment of logging
        if 'timestamp' not in catch:
            catch['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        df = pd.DataFrame([catch])
        mode = 'a' if os.path.exists('recent_catches.csv') else 'w'
        header = not os.path.exists('recent_catches.csv')
        df.to_csv('recent_catches.csv', mode=mode, header=header, index=False)
        print(f"📊 Saved {catch['symbol']} to recent_catches.csv")
