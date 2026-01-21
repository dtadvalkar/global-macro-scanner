# 🎯 STOCK SCREENING CRITERIA
# Central repository for all stock screening filters and thresholds.
# This file serves as the single source of truth for screening logic.
#
# ARCHITECTURE OVERVIEW:
# - All screening criteria are defined here as a single CRITERIA dict
# - screening_utils.py provides should_pass_screening() function that applies these criteria
# - Data providers (YFinanceProvider, IBKRProvider) call should_pass_screening() after data fetch
# - This ensures consistent filtering across all data sources and simplifies future criteria additions
#
# WORKFLOW:
# 1. Provider fetches raw stock data (price, volume, history, etc.)
# 2. Provider calls should_pass_screening(raw_data, CRITERIA)
# 3. If stock passes all filters, it's included in results; otherwise discarded
# 4. Results are returned with consistent formatting for alerts/logging
#
# Filter Types:
# - PRICE & MOMENTUM: Core entry signal (52-week low proximity)
# - VOLUME & LIQUIDITY: Validate interest/activity
# - TECHNICAL INDICATORS: Quality and timing filters
# - FUNDAMENTAL FILTERS: Financial health (optional/slow)
# - PATTERN RECOGNITION: Price action patterns
# - RISK MANAGEMENT: Avoid obvious bad picks
# - MARKET CAP FILTERS: Size thresholds by market type
# - SAMPLE SIZE & PERFORMANCE: Operational limits
#
# Implementation Notes:
# - [IMPLEMENTED]: Active in current code via screening_utils.py
# - [SERVER-SIDE]: Enforced by data provider before data fetch (IBKR scanner, etc.)
# - [CLIENT-SIDE]: Enforced in Python after data fetch via screening_utils.should_pass_screening()
# - [PROVIDER-SKIP]: Stock skipped entirely by provider (e.g., unsupported exchanges)
# - [FUTURE]: Planned but not yet implemented (commented out)

CRITERIA = {
    # ============================================
    # 1. PRICE & MOMENTUM (The Anchor)
    # ============================================
    'price_52w_low_pct': 1.03,          # [IMPLEMENTED] Price must be within 3% of 52-week low (mean reversion setup)
    'price_52w_high_pct': 0.50,         # [CLIENT-SIDE] Price must be at least 50% below 52-week high (avoid dead cats)
    'min_history_days': 250,             # [CLIENT-SIDE] Must have ~1 year of data to confirm reliable low (checked in providers)

    # ============================================
    # 2. VOLUME & LIQUIDITY (The "Life" Signal)
    # ============================================
    # A stock must meet AT LEAST ONE of these to show it has "Life":
    'min_volume': 50000,                # [IMPLEMENTED] Condition A: Good daily liquidity (absolute volume threshold)
    'min_rvol': 2.0,                    # [IMPLEMENTED] Condition B: Volume Spike (2x 30-day Avg, calculated in providers)
    'min_avg_volume_20d': 50000,        # [CLIENT-SIDE] Ensure consistent liquidity (20-day avg, requires full history)
    'max_rvol': 20.0,                   # [CLIENT-SIDE] Filter out extreme anomalies (likely data errors)

    # ============================================
    # 3. TECHNICAL INDICATORS (Quality Filters)
    # ============================================
    # RSI - Relative Strength Index
    'rsi_enabled': True,                # [IMPLEMENTED] Enable RSI filtering for momentum confirmation
    'rsi_min': 20,                      # [IMPLEMENTED] RSI > 20 (oversold, but not dead)
    'rsi_max': 50,                      # [IMPLEMENTED] RSI < 50 (avoid neutral/overbought)

    # Moving Averages - Trend Context
    'ma_enabled': True,                 # [IMPLEMENTED] Enable MA filtering for trend support
    'price_vs_sma50_pct': 0.95,         # [IMPLEMENTED] Price within 5% of 50-day SMA (reasonable support)
    'sma50_vs_sma200_pct': 0.93,        # [IMPLEMENTED] 50-day SMA within 7% of 200-day (avoid downtrends)

    # Volatility - ATR (Average True Range)
    'atr_enabled': True,                # [IMPLEMENTED] Enable ATR filtering for volatility suitability
    'atr_min_pct': 0.015,               # [IMPLEMENTED] Min 1.5% daily volatility (some movement)
    'atr_max_pct': 0.08,                # [IMPLEMENTED] Max 8% daily volatility (manageable risk)

    # ============================================
    # 4. FUNDAMENTAL FILTERS (Optional)
    # ============================================
    'fundamental_enabled': False,        # [FUTURE] Enable fundamental checks (slower, requires API)
    'max_debt_to_equity': 2.0,           # [FUTURE] Filter high debt companies (if data available)
    'min_current_ratio': 1.0,            # [FUTURE] Basic liquidity check (if data available)

    # ============================================
    # 5. PRICE ACTION PATTERNS (Pattern Recognition)
    # ============================================
    'pattern_enabled': True,             # [IMPLEMENTED] Enable pattern detection for higher quality signals
    'double_bottom_enabled': True,       # [IMPLEMENTED] Detect double bottom patterns
    'breakout_enabled': True,            # [IMPLEMENTED] Detect breakouts near 52w lows
    'volume_confirmation_required': True, # [IMPLEMENTED] Require volume confirmation for patterns
    'min_volume_spike_ratio': 2.0,       # [IMPLEMENTED] Minimum volume spike for confirmation
    'require_volume_confirmation': True, # [CLIENT-SIDE] Volume should confirm price movement
    'min_days_since_low': 1,             # [CLIENT-SIDE] At least 1 day since hitting low (avoid same-day noise)
    'max_days_since_low': 30,            # [CLIENT-SIDE] Not more than 30 days since low (still "fresh")

    # ============================================
    # 6. RISK MANAGEMENT FILTERS
    # ============================================
    'max_price': 1000.0,                 # [CLIENT-SIDE] Avoid penny stocks or extremely expensive stocks
    'min_price': 1.0,                    # [CLIENT-SIDE] Minimum price threshold (avoid micro-caps)
    'exclude_otc': True,                 # [CLIENT-SIDE] Exclude OTC/pink sheet stocks (if detectable)

    # ============================================
    # 7. MARKET CAP FILTERS (Size Thresholds)
    # ============================================
    # Note: Primary enforcement via market registry in config/markets.py
    # These values serve as documentation and potential overrides
    'min_market_cap_major': 500_000_000,     # [CLIENT-SIDE] US, Canada ($500M) - enforced via get_min_market_cap()
    'min_market_cap_emerging': 150_000_000,  # [CLIENT-SIDE] India, Indonesia, Thailand ($150M) - enforced via get_min_market_cap()

    # ============================================
    # 8. SAMPLE SIZE & PERFORMANCE
    # ============================================
    'scan_sample_size': 5000,            # [SERVER-SIDE] Max stocks to check per run (passed to providers as ticker limit)
    'nse_top_limit': 200,                # [CLIENT-SIDE] Limit for Deep Scan in India (reduces NSE processing time)
    'priority_score_enabled': False,     # [FUTURE] Rank results by composite score (would modify result ordering)
}

# ============================================
# SCORING WEIGHTS (For Priority Ranking)
# ============================================
SCORING_WEIGHTS = {
    'rvol_weight': 0.30,                 # [FUTURE] Higher RVOL = higher score
    'price_proximity_weight': 0.25,      # [FUTURE] Closer to 52w low = higher score
    'volume_weight': 0.20,               # [FUTURE] Higher absolute volume = higher score
    'rsi_weight': 0.15,                  # [FUTURE] Lower RSI (but not too low) = higher score
    'momentum_weight': 0.10,             # [FUTURE] Recent positive momentum = higher score
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
        # Uses default values from CRITERIA
    }
}
