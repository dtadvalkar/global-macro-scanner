"""
Screening Utilities
Centralized logic for applying stock screening criteria.
Called by data providers after fetching raw stock data.
"""

from config import CRITERIA
from config.markets import get_min_market_cap
from datetime import datetime
import numpy as np

def should_pass_screening(symbol_data, criteria=None):
    """
    Apply all screening criteria to determine if a stock passes filters.

    Args:
        symbol_data (dict): Raw stock data with keys like 'symbol', 'price', 'low_52w',
                           'usd_mcap', 'rvol', 'volume', 'high_52w', etc.
        criteria (dict, optional): Screening criteria. Defaults to CRITERIA from config.

    Returns:
        dict or None: Filtered stock data if it passes all criteria, None otherwise.
    """
    if criteria is None:
        criteria = CRITERIA

    # Extract data with defaults for missing fields
    symbol = symbol_data.get('symbol', '')
    price = symbol_data.get('price', 0)
    low_52w = symbol_data.get('low_52w', 0)
    usd_mcap = symbol_data.get('usd_mcap', 0)  # In billions
    rvol = symbol_data.get('rvol', 0)
    volume = symbol_data.get('volume', 0)
    high_52w = symbol_data.get('high_52w', 0)

    # Convert market cap back to full dollars if needed
    if usd_mcap < 1000:  # Likely in billions
        usd_mcap_full = usd_mcap * 1e9
    else:
        usd_mcap_full = usd_mcap

    # ============================================
    # 1. BASIC VALIDATION (Required fields)
    # ============================================
    if not symbol or not (price > 0):
        return None

    # ============================================
    # 2. MARKET CAP FILTER (Size thresholds)
    # ============================================
    # Determine exchange from suffix for market cap thresholds
    exchange_map = {'.NS': 'NSE', '.TO': 'TSE', '.JK': 'IDX', '.BK': 'SET'}
    exchange = 'SMA'  # Default to major market
    for suffix, ex in exchange_map.items():
        if symbol.endswith(suffix):
            exchange = ex
            break

    min_cap = get_min_market_cap(exchange)
    if usd_mcap_full < min_cap:
        return None

    # ============================================
    # 3. PRICE FILTERS
    # ============================================
    # Price proximity to 52w low (Anchor Filter)
    # DE-COUPLED: If low_52w is missing, we skip this check and allow pass on Volume
    if low_52w and low_52w > 0:
        pct_from_low = price / low_52w
        if pct_from_low > criteria.get('price_52w_low_pct', 1.03):
            return None

        # Optional: Price vs 52w high (avoid dead cats)
        if criteria.get('price_52w_high_pct', 0) > 0:
            if high_52w and high_52w > 0:
                pct_from_high = price / high_52w
                if pct_from_high > criteria['price_52w_high_pct']:
                    return None
    else:
        # Flag that we are missing baseline for reasoning/display
        pct_from_low = 0

    # ============================================
    # 4. VOLUME & LIQUIDITY FILTERS
    # ============================================
    vol_ok = volume >= criteria.get('min_volume', 100000)
    rvol_ok = rvol >= criteria.get('min_rvol', 2.0)

    # Must meet at least one volume condition
    if not (vol_ok or rvol_ok):
        return None

    # Optional: RVOL cap (filter out extreme anomalies)
    if 'max_rvol' in criteria and rvol > criteria['max_rvol']:
        return None

    # 20-day average volume floor — pass through if field absent (IBKR path)
    if 'min_avg_volume_20d' in criteria:
        avg_vol_20d = symbol_data.get('avg_volume_20d', 0)
        if avg_vol_20d > 0 and avg_vol_20d < criteria['min_avg_volume_20d']:
            return None

    # Days-since-low freshness window — pass through if field absent (IBKR path)
    if 'min_days_since_low' in criteria or 'max_days_since_low' in criteria:
        days_since_low = symbol_data.get('days_since_low')
        if days_since_low is not None:
            if days_since_low < criteria.get('min_days_since_low', 1):
                return None
            if days_since_low > criteria.get('max_days_since_low', 30):
                return None

    # ============================================
    # 5. RISK MANAGEMENT FILTERS
    # ============================================
    # Price range filters
    if 'min_price' in criteria and price < criteria['min_price']:
        return None
    if 'max_price' in criteria and price > criteria['max_price']:
        return None

    # ============================================
    # 6. FUTURE FILTERS (Currently disabled)
    # ============================================
    # These will be implemented when enabled in criteria

    # RSI Filter (when enabled)
    if criteria.get('rsi_enabled', False):
        rsi = symbol_data.get('rsi', 50)  # Default to neutral
        if not (criteria.get('rsi_min', 0) <= rsi <= criteria.get('rsi_max', 100)):
            return None

    # Moving Average Filters (when enabled)
    if criteria.get('ma_enabled', False):
        price_vs_sma50 = symbol_data.get('price_vs_sma50_pct', 1.0)
        sma50_vs_sma200 = symbol_data.get('sma50_vs_sma200_pct', 1.0)

        if price_vs_sma50 < criteria.get('price_vs_sma50_pct', 0.95):
            return None
        if sma50_vs_sma200 < criteria.get('sma50_vs_sma200_pct', 0.90):
            return None

    # ATR (Volatility) Filters (when enabled)
    if criteria.get('atr_enabled', False):
        atr_pct = symbol_data.get('atr_pct', 0.05)  # Default to 5%
        if not (criteria.get('atr_min_pct', 0.02) <= atr_pct <= criteria.get('atr_max_pct', 0.10)):
            return None

    # Pattern Recognition (when enabled)
    if criteria.get('pattern_enabled', False):
        # Double Bottom Detection
        if criteria.get('double_bottom_enabled', False):
            hist = symbol_data.get('price_history')
            if hist is not None and len(hist) >= 20:
                if detect_double_bottom(hist):
                    # Double bottom detected - this is a positive signal
                    pass  # Allow to pass through
                else:
                    # No double bottom - but don't fail here, just note it
                    pass

        # Breakout Detection
        if criteria.get('breakout_enabled', False):
            breakout_result = detect_breakout_near_low(
                price, low_52w, volume,
                symbol_data.get('avg_volume_20d', volume),  # Fallback to current volume
                criteria.get('price_52w_low_pct', 1.01)
            )

            if breakout_result.get('detected', False):
                # Strong breakout signal - allow to pass
                pass
            elif criteria.get('volume_confirmation_required', False):
                # If volume confirmation is required and not detected, fail
                volume_confirm = confirm_volume_spike(
                    volume,
                    symbol_data.get('avg_volume_20d', volume),
                    criteria.get('min_volume_spike_ratio', 2.0)
                )
                if not volume_confirm['confirmed']:
                    return None

    # Fundamental Filters (when enabled)
    if criteria.get('fundamental_enabled', False):
        debt_to_equity = symbol_data.get('debt_to_equity', 0)
        current_ratio = symbol_data.get('current_ratio', 2.0)

        if debt_to_equity > criteria.get('max_debt_to_equity', 2.0):
            return None
        if current_ratio < criteria.get('min_current_ratio', 1.0):
            return None

    # ============================================
    # PASSED ALL FILTERS
    # ============================================
    # Return enriched data for successful stocks
    result = {
        'symbol': symbol,
        'price': price,
        'low_52w': low_52w,
        'usd_mcap': usd_mcap,  # Keep in billions for display
        'pct_from_low': pct_from_low if 'pct_from_low' in locals() else price / low_52w,
        'rvol': rvol,
        'volume': volume,
        'time': symbol_data.get('time', datetime.now())
    }

    # Add optional fields if available
    for key in ['high_52w', 'rsi', 'sma50', 'sma200', 'atr_pct', 'debt_to_equity', 'current_ratio']:
        if key in symbol_data:
            result[key] = symbol_data[key]

    return result

def calculate_rsi(prices, period=14):
    """
    Calculate RSI from price series.

    Args:
        prices: pandas Series of closing prices
        period: RSI period (default 14)

    Returns:
        float: RSI value
    """
    if len(prices) < period + 1:
        return 50.0  # Neutral RSI if insufficient data

    try:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    except Exception:
        return 50.0

def calculate_sma(prices, period):
    """
    Calculate Simple Moving Average.

    Args:
        prices: pandas Series of prices
        period: SMA period

    Returns:
        float: SMA value
    """
    if len(prices) < period:
        return prices.iloc[-1]  # Return last price if insufficient data

    try:
        return prices.tail(period).mean()
    except Exception:
        return prices.iloc[-1]

def calculate_atr(highs, lows, closes, period=14):
    """
    Calculate Average True Range (ATR) as percentage.

    Args:
        highs: pandas Series of high prices
        lows: pandas Series of low prices
        closes: pandas Series of closing prices
        period: ATR period

    Returns:
        float: ATR as percentage of price
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return 0.05  # Default 5% if insufficient data

    try:
        # True Range
        tr1 = highs - lows
        tr2 = (highs - closes.shift(1)).abs()
        tr3 = (lows - closes.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR
        atr = tr.rolling(window=period).mean()

        # ATR as percentage of current price
        current_price = closes.iloc[-1]
        atr_pct = atr.iloc[-1] / current_price if current_price > 0 else 0

        return atr_pct
    except Exception:
        return 0.05

def detect_double_bottom(prices, tolerance_pct=0.05):
    """
    Detect double bottom pattern in price series.

    Args:
        prices: pandas Series of closing prices
        tolerance_pct: Tolerance for bottom detection (default 5%)

    Returns:
        bool: True if double bottom pattern detected
    """
    if len(prices) < 20:
        return False

    try:
        # Look for two lows within tolerance of each other
        recent_lows = prices.tail(20).min()
        current_price = prices.iloc[-1]

        # Find all local minima in the last 20 days
        local_mins = []
        for i in range(1, len(prices.tail(20)) - 1):
            if prices.iloc[-(i+1)] < prices.iloc[-(i)] and prices.iloc[-(i+1)] < prices.iloc[-(i+2)]:
                local_mins.append(prices.iloc[-(i+1)])

        # Check if we have at least 2 lows within tolerance
        if len(local_mins) >= 2:
            # Sort lows and check if the two lowest are close
            local_mins.sort()
            if len(local_mins) >= 2:
                low1, low2 = local_mins[0], local_mins[1]
                if abs(low1 - low2) / low1 <= tolerance_pct:
                    # Current price should be breaking above the pattern
                    pattern_high = max(prices.tail(20))
                    if current_price > (low1 + low2) / 2:  # Above midpoint
                        return True
        return False
    except:
        return False

def confirm_volume_spike(volume, avg_volume_20d, spike_threshold=1.5):
    """
    Confirm if current volume represents a meaningful spike.

    Args:
        volume: Current trading volume
        avg_volume_20d: 20-day average volume
        spike_threshold: Minimum spike ratio (default 1.5x)

    Returns:
        dict: Volume confirmation metrics
    """
    if not avg_volume_20d or avg_volume_20d <= 0:
        return {'confirmed': False, 'ratio': 0, 'strength': 'insufficient_data'}

    ratio = volume / avg_volume_20d

    if ratio >= 4.0:
        strength = 'extreme'
    elif ratio >= 2.5:
        strength = 'strong'
    elif ratio >= spike_threshold:
        strength = 'moderate'
    else:
        strength = 'weak'

    return {
        'confirmed': ratio >= spike_threshold,
        'ratio': round(ratio, 1),
        'strength': strength
    }

def detect_breakout_near_low(price, low_52w, volume, avg_volume_20d, breakout_threshold=0.98):
    """
    Detect breakout patterns near 52-week lows.

    Args:
        price: Current price
        low_52w: 52-week low
        volume: Current volume
        avg_volume_20d: 20-day average volume
        breakout_threshold: How close to low for breakout detection

    Returns:
        dict: Breakout detection results
    """
    if not low_52w or low_52w <= 0:
        return {'detected': False, 'type': 'invalid_data'}

    pct_from_low = price / low_52w

    # Must be within threshold of 52w low
    if pct_from_low > breakout_threshold:
        return {'detected': False, 'type': 'not_near_low'}

    # Check volume confirmation
    volume_confirm = confirm_volume_spike(volume, avg_volume_20d, 2.0)

    if volume_confirm['confirmed']:
        if pct_from_low <= 1.02:  # Very close to low
            breakout_type = 'bullish_breakout_near_low'
        else:
            breakout_type = 'breakout_confirmation'

        return {
            'detected': True,
            'type': breakout_type,
            'pct_from_low': round(pct_from_low, 3),
            'volume_ratio': volume_confirm['ratio'],
            'volume_strength': volume_confirm['strength']
        }

    return {'detected': False, 'type': 'insufficient_volume'}

def apply_preset(criteria, preset_name):
    """
    Apply a preset configuration to criteria.

    Args:
        criteria: Base criteria dict
        preset_name: Name of preset from PRESETS

    Returns:
        dict: Modified criteria with preset applied
    """
    from config.criteria import PRESETS

    if preset_name not in PRESETS:
        return criteria

    preset = PRESETS[preset_name]
    result = criteria.copy()
    result.update(preset)
    return result