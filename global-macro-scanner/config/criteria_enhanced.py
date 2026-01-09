# 🎯 ENHANCED STOCK SCREENING CRITERIA
# Based on research and best practices from quantitative trading screeners

# "Fishing Net" Rules - Enhanced Version
CRITERIA_ENHANCED = {
    # ============================================
    # 1. PRICE & MOMENTUM (The Anchor)
    # ============================================
    'price_52w_low_pct': 1.01,          # Price must be within 1% of 52-week low (mean reversion setup)
    'price_52w_high_pct': 0.50,         # NEW: Price must be at least 50% below 52-week high (avoid dead cats)
    'min_history_days': 250,             # Must have ~1 year of data to confirm reliable low
    
    # ============================================
    # 2. VOLUME & LIQUIDITY (The "Life" Signal)
    # ============================================
    'min_volume': 100000,                # Condition A: Good daily liquidity
    'min_rvol': 2.0,                     # Condition B: Volume Spike (2x 30-day Avg)
    'min_avg_volume_20d': 50000,         # NEW: Ensure consistent liquidity (20-day avg)
    'max_rvol': 20.0,                    # NEW: Filter out extreme anomalies (likely errors)
    
    # ============================================
    # 3. TECHNICAL INDICATORS (Quality Filters)
    # ============================================
    # RSI - Relative Strength Index
    'rsi_enabled': True,                 # NEW: Enable RSI filtering
    'rsi_min': 20,                       # NEW: RSI < 20 (oversold, but not dead)
    'rsi_max': 40,                       # NEW: RSI < 40 (avoid overbought)
    
    # Moving Averages - Trend Context
    'ma_enabled': True,                  # NEW: Enable MA filtering
    'price_vs_sma50_pct': 0.95,         # NEW: Price within 5% of 50-day SMA (not too far below)
    'sma50_vs_sma200_pct': 0.90,        # NEW: 50-day SMA within 10% of 200-day (avoid severe downtrends)
    
    # Volatility - ATR (Average True Range)
    'atr_enabled': True,                 # NEW: Enable ATR filtering
    'atr_min_pct': 0.02,                 # NEW: Min 2% daily volatility (some movement potential)
    'atr_max_pct': 0.10,                 # NEW: Max 10% daily volatility (avoid extreme risk)
    
    # ============================================
    # 4. FUNDAMENTAL FILTERS (Optional)
    # ============================================
    'fundamental_enabled': False,        # NEW: Enable fundamental checks (slower, requires API)
    'min_market_cap_multiplier': 1.0,   # NEW: Already handled by market registry, but can override
    'max_debt_to_equity': 2.0,           # NEW: Filter high debt companies (if data available)
    'min_current_ratio': 1.0,            # NEW: Basic liquidity check (if data available)
    
    # ============================================
    # 5. PRICE ACTION PATTERNS (Pattern Recognition)
    # ============================================
    'pattern_enabled': False,            # NEW: Enable pattern detection (requires more computation)
    'require_volume_confirmation': True, # NEW: Volume should confirm price movement
    'min_days_since_low': 1,             # NEW: At least 1 day since hitting low (avoid same-day noise)
    'max_days_since_low': 30,            # NEW: Not more than 30 days since low (still "fresh")
    
    # ============================================
    # 6. RISK MANAGEMENT FILTERS
    # ============================================
    'max_price': 1000.0,                 # NEW: Avoid penny stocks or extremely expensive stocks
    'min_price': 1.0,                    # NEW: Minimum price threshold (avoid micro-caps)
    'exclude_otc': True,                 # NEW: Exclude OTC/pink sheet stocks (if detectable)
    
    # ============================================
    # 7. SAMPLE SIZE & PERFORMANCE
    # ============================================
    'scan_sample_size': 5000,            # Max stocks to check per run
    'nse_top_limit': 200,                # Limit for Deep Scan in India (Efficiency)
    'priority_score_enabled': True,      # NEW: Rank results by composite score
}

# ============================================
# SCORING WEIGHTS (For Priority Ranking)
# ============================================
SCORING_WEIGHTS = {
    'rvol_weight': 0.30,                 # Higher RVOL = higher score
    'price_proximity_weight': 0.25,      # Closer to 52w low = higher score
    'volume_weight': 0.20,               # Higher absolute volume = higher score
    'rsi_weight': 0.15,                  # Lower RSI (but not too low) = higher score
    'momentum_weight': 0.10,             # Recent positive momentum = higher score
}

# ============================================
# QUICK PRESETS (Easy Toggle)
# ============================================
PRESETS = {
    'conservative': {
        'price_52w_low_pct': 1.005,      # Within 0.5% of low (very strict)
        'min_rvol': 3.0,                  # Higher volume spike required
        'rsi_max': 30,                    # More oversold
        'min_avg_volume_20d': 100000,     # Higher liquidity requirement
    },
    'aggressive': {
        'price_52w_low_pct': 1.05,       # Within 5% of low (wider net)
        'min_rvol': 1.5,                  # Lower volume spike
        'rsi_max': 50,                    # Less strict on RSI
        'min_avg_volume_20d': 25000,     # Lower liquidity requirement
    },
    'balanced': {
        # Default values from CRITERIA_ENHANCED
    }
}
