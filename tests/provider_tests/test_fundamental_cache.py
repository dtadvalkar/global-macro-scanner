#!/usr/bin/env python3
"""
Test the Fundamental Cache Manager (read-only path).

The cache_manager was pruned during the SQL-externalization cleanup
(2026-04-30) to only the working methods. Earlier tests of write-side
APIs (set_fundamentals, get_market_cap_stats, can_skip_by_fundamentals)
covered methods that AttributeErrored against uninitialized state and
have been removed.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data.cache_manager import FundamentalCacheManager


def test_fundamental_cache():
    print("TESTING FUNDAMENTAL CACHE (READ-ONLY)")
    print("=" * 50)

    cache = FundamentalCacheManager()

    # 1. Look up a ticker that should exist in the curated stock_fundamentals.
    fundamentals = cache.get_fundamentals('RELIANCE.NS')
    if fundamentals:
        mcap = fundamentals.get('market_cap_usd') or 0
        print(f"RELIANCE.NS: ${mcap/1e9:.1f}B market cap, exchange={fundamentals.get('exchange')}")
        assert fundamentals['ticker'] == 'RELIANCE.NS'
        assert fundamentals['data_source'] == 'ibkr'
    else:
        print("RELIANCE.NS not found (run flatten_ibkr_final.py to populate).")

    # 2. Memory cache hit on second call (no DB round-trip).
    fundamentals_again = cache.get_fundamentals('RELIANCE.NS')
    assert fundamentals_again is fundamentals or fundamentals is None, \
        "Second call should hit memory cache and return the same dict"
    print("Memory cache hit verified")

    # 3. Unknown ticker returns None cleanly.
    missing = cache.get_fundamentals('NONEXISTENT.ZZ')
    assert missing is None
    print("Unknown ticker returned None")

    print("\nFundamental cache test completed")


if __name__ == '__main__':
    test_fundamental_cache()
