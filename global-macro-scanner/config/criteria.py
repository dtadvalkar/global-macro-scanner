# 🎯 STOCK SCREENING CRITERIA

# "Fishing Net" Rules
CRITERIA = {
    # 1. PRICE (The Anchor)
    'price_52w_low_pct': 1.01,          # Price must be within 1% of 52-week low
    'min_history_days': 250,            # Must have ~1 year of data to confirm reliable low
    
    # 2. VALIDATION (The "OR" Logic)
    # A stock must meet AT LEAST ONE of these to show it has "Life":
    'min_volume': 100000,               # Condition A: Good daily liquidity
    'min_rvol': 2.0,                    # Condition B: Volume Spike (2x 30-day Avg)
    
    # 3. SAMPLE SIZE
    'scan_sample_size': 5000,           # Max stocks to check per run
    'nse_top_limit': 200                # Limit for Deep Scan in India (Efficiency)
}
