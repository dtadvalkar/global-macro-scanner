# 🎣 Fishing Criteria Improvements

## Overview
This document outlines suggested improvements to the stock screening criteria based on research from quantitative trading screeners and best practices.

## Current Criteria (Baseline)
- ✅ Price within 1% of 52-week low
- ✅ Volume > 100k OR RVOL > 2.0x
- ✅ Market cap filtering (by exchange type)

## Suggested Enhancements

### 1. **Price & Momentum Filters** ⭐ HIGH PRIORITY
**Why:** Current criteria only checks proximity to 52w low, but doesn't consider:
- How far from 52w high (avoid stocks that were never good)
- Recent momentum (is it still falling or showing signs of recovery?)

**Additions:**
- `price_52w_high_pct`: Ensure stock is at least 50% below 52w high (filters out stocks that were always low)
- `min_days_since_low`: At least 1 day since hitting low (avoids same-day noise)
- `max_days_since_low`: Not more than 30 days since low (still "fresh" opportunity)

### 2. **Technical Indicators** ⭐ HIGH PRIORITY
**Why:** RSI and Moving Averages add context to price action:
- RSI helps identify oversold conditions (but not dead stocks)
- Moving averages show trend context (avoid severe downtrends)

**Additions:**
- **RSI (Relative Strength Index)**: Filter for RSI 20-40 (oversold but not dead)
- **Moving Averages**: 
  - Price within 5% of 50-day SMA (not too far below)
  - 50-day SMA within 10% of 200-day (avoid severe downtrends)
- **ATR (Average True Range)**: Filter for 2-10% daily volatility (some movement potential, not extreme risk)

### 3. **Enhanced Volume Filters** ⭐ MEDIUM PRIORITY
**Why:** Current volume check is basic - can be improved:
- Check average volume over 20 days (consistency)
- Cap extreme RVOL values (likely data errors)

**Additions:**
- `min_avg_volume_20d`: Ensure consistent liquidity
- `max_rvol`: Filter out extreme anomalies (>20x is likely an error)

### 4. **Risk Management Filters** ⭐ MEDIUM PRIORITY
**Why:** Avoid obvious bad picks:
- Penny stocks or extremely expensive stocks
- OTC/pink sheet stocks (if detectable)

**Additions:**
- `min_price`: $1.00 minimum
- `max_price`: $1000.00 maximum
- `exclude_otc`: Skip OTC markets

### 5. **Priority Scoring System** ⭐ LOW PRIORITY (Nice to Have)
**Why:** Rank results by quality, not just pass/fail:
- Composite score based on multiple factors
- Helps prioritize which catches to investigate first

**Scoring Factors:**
- RVOL (30% weight)
- Price proximity to 52w low (25% weight)
- Absolute volume (20% weight)
- RSI level (15% weight)
- Recent momentum (10% weight)

## Implementation Priority

### Phase 1: Quick Wins (Easy to implement)
1. ✅ Price vs 52w high filter
2. ✅ Enhanced volume filters (20-day avg, max RVOL)
3. ✅ Price range filters (min/max price)

### Phase 2: Technical Indicators (Requires calculation)
1. ⚠️ RSI calculation (needs historical data)
2. ⚠️ Moving averages (SMA 50, SMA 200)
3. ⚠️ ATR calculation

### Phase 3: Advanced Features
1. 🔮 Pattern recognition
2. 🔮 Fundamental filters (if data available)
3. 🔮 Priority scoring system

## Recommended Starting Point

**Conservative Approach:**
Start with Phase 1 improvements - they're easy to implement and add immediate value without requiring new calculations.

**Aggressive Approach:**
Add RSI and basic moving averages (Phase 2) - these are standard indicators that most screeners use.

## Code Changes Required

### 1. Update `config/criteria.py`
Add new criteria parameters (see `criteria_enhanced.py` for reference)

### 2. Update `data/providers.py`
- Add RSI calculation function
- Add moving average calculations (SMA 50, SMA 200)
- Add ATR calculation
- Update screening logic to check new criteria

### 3. Update `screener/core.py` (if needed)
- Add priority scoring if implementing Phase 3

## Example: RSI Calculation
```python
def calculate_rsi(prices, period=14):
    """Calculate RSI from price series"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]
```

## Testing Strategy
1. Run current scanner and save results
2. Implement Phase 1 improvements
3. Compare results - should see:
   - Fewer false positives (bad stocks filtered out)
   - Similar or better quality catches
   - Slightly fewer total catches (more selective)

## References
- TradingView Screener patterns
- Finviz screening criteria
- Quantitative trading research papers
- Swing trading best practices
