# 🎣 Screening Criteria Implementation Guide

## 📋 DOCUMENT POSITIONING

### Relationship to Master Plan
**This document is a detailed implementation guide for Task #1** of the [Master Development Plan](../master_development_plan.md).

- **Master Plan**: Strategic roadmap, task tracking, timelines, success metrics
- **This Document**: Technical implementation details, code architecture, testing procedures

### Current Status in Master Plan
**Task #1: Enhanced Scanning Logic** ✅ **COMPLETED**
- ✅ Technical indicators (RSI, MA, ATR) implemented and active
- ✅ Pattern recognition (double bottoms, volume confirmation, breakouts) integrated
- ✅ Performance optimizations (caching, parallel processing) deployed
- ✅ Centralized criteria management system operational

---

## 🎯 IMPLEMENTATION GUIDE

This document provides detailed technical guidance for the stock screening criteria system, focusing on the technical indicators, filtering logic, and signal quality improvements that form the core of the Global Market Scanner's screening engine.

## Architecture Changes (Completed)

### Centralized Criteria Management
- **Before:** Filtering logic scattered across providers with hardcoded thresholds
- **After:** All criteria defined in `config/criteria.py`, applied via `screening_utils.should_pass_screening()`
- **Benefits:** Single source of truth, easier to modify, consistent across providers

### ✅ IMPLEMENTED CRITERIA (ACTIVE)
**Core Filters (Always Active):**
- ✅ Price within 1.01x of 52-week low (primary signal)
- ✅ Volume > 100k OR RVOL > 2.0x (liquidity confirmation)
- ✅ Market cap filtering (exchange-specific thresholds)
- ✅ Price range limits ($1.00 - $1000.00)

**Enhanced Technical Filters (Task #1 ✅ COMPLETED):**
- ✅ RSI momentum filtering (20-45 range for oversold confirmation)
- ✅ Moving average support (price ≤1.03x SMA50, trend context)
- ✅ ATR volatility filtering (1.5-8% range for risk management)
- ✅ Pattern recognition (double bottoms, volume spikes, breakouts)
- ✅ Volume consistency checks (20-day average validation)

**Performance Optimizations (Task #2 ✅ COMPLETED):**
- ✅ Intelligent caching (1-hour TTL, smart cache keys)
- ✅ Parallel processing (5 concurrent requests)
- ✅ Adaptive rate limiting (0.8 req/sec, 25% faster)
- ✅ Early filtering to reduce API calls

## 📈 NEXT PHASE ENHANCEMENTS

### Phase 1: Immediate Improvements (Current Sprint)
**Timeline**: Next 1-2 weeks (after IBKR permissions)

#### Enhanced Volume & Risk Filters
- `max_rvol`: Cap extreme RVOL anomalies (>20x likely data errors)
- Enhanced days-since-low filtering (1-30 day window)
- Improved volume consistency validation

### Phase 2: Advanced Features (Back Burner - Q2 2025)
**Status**: Deferred until MVP proves profitable

#### Fundamental Integration 🔮 BACK BURNER
- Earnings quality metrics
- Revenue growth trends
- Institutional ownership data
- Debt-to-equity ratios
- Current ratio analysis

#### Advanced Criteria System 🔮 BACK BURNER
- Time-based opportunity windows
- Sector rotation analysis
- Correlation-based filtering
- Market regime detection
- Volatility clustering analysis

#### Priority Scoring System 🔮 BACK BURNER
- Composite ranking by quality
- Multi-factor scoring (RVOL, proximity, RSI, momentum)
- Alert prioritization

## Implementation Priority

## ✅ IMPLEMENTATION STATUS SUMMARY

### Master Plan Task #1: Enhanced Scanning Logic ✅ COMPLETED
**Completion**: 100% - All technical indicators and pattern recognition implemented

### Master Plan Task #2: Performance Optimizations ✅ COMPLETED
**Completion**: 100% - Optimized provider with caching, parallel processing, and rate limiting

### Next Steps (Aligned with Master Plan)
1. **Task #3**: Wait for IBKR permissions (external dependency)
2. **Task #4**: Test with current markets (India, Australia, Singapore)
3. **Task #5**: Implement automated scheduling system
4. **Task #6**: Enhance Telegram alert system

### Back Burner Items (Phase 2 - Post-MVP)
- Fundamental integration (earnings, debt ratios, etc.)
- Advanced criteria (sector rotation, correlations)
- Priority scoring system

## Recommended Starting Point

**Conservative Approach:**
Start with Phase 1 improvements - they're easy to implement and add immediate value without requiring new calculations.

**Aggressive Approach:**
Add RSI and basic moving averages (Phase 2) - these are standard indicators that most screeners use.

## Implementation Status

### Completed Architecture Changes
1. **Centralized Criteria** (`config/criteria.py`): All criteria documented and organized
2. **Screening Utility** (`screening/screening_utils.py`): Shared filtering logic
3. **Provider Refactoring** (`data/providers.py`): Removed hardcoded logic, now uses centralized filtering
4. **Documentation Updates**: Code comments and architecture docs updated

### Current Implementation Details

#### Active Criteria (Implemented)
- **Price Filters:** 52-week low proximity, price range limits
- **Volume Filters:** Absolute volume, RVOL, 20-day average consistency
- **Market Cap:** Exchange-specific thresholds via market registry
- **Risk Filters:** Price range caps, RVOL anomaly detection

#### Future Criteria (Documented but Disabled)
- **Technical Indicators:** RSI, moving averages, ATR (framework ready)
- **Fundamental Filters:** Debt-to-equity, current ratio (hooks in place)
- **Pattern Recognition:** Volume confirmation, days since low (logic ready)
- **Priority Scoring:** Composite ranking system (structure ready)

### Code Architecture

#### Before (Scattered Logic)
```python
# In YFinanceProvider
if usd_mcap > min_cap and (vol_ok or rvol_ok):
    # ... hardcoded filtering

# In IBKRProvider
if pct_from_low <= criteria['price_52w_low_pct'] and (vol_ok or rvol_ok):
    # ... different hardcoded logic
```

#### After (Centralized Logic)
```python
# In all providers
symbol_data = {...}  # Raw data
filtered_result = should_pass_screening(symbol_data, criteria)
if filtered_result:
    results.append(filtered_result)
```

#### Benefits
- **Consistency:** Same logic across all data sources
- **Maintainability:** Change criteria in one place
- **Extensibility:** Easy to add new filters
- **Testing:** Centralized logic easier to unit test

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
