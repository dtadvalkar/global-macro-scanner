#!/usr/bin/env python3
"""
Test the Fundamental Cache Manager integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data.cache_manager import FundamentalCacheManager
from config import CRITERIA

def test_fundamental_cache():
    """Test fundamental caching functionality"""
    print("TESTING FUNDAMENTAL CACHE INTEGRATION")
    print("=" * 50)

    cache = FundamentalCacheManager()

    # Test 1: Check early filtering
    print("\n1. Testing Early Filtering")

    # Test with a small cap stock (should be skipped)
    small_cap_data = {
        'symbol': 'SMALL',
        'exchange': 'SMART',
        'market_cap_usd': 30000000,  # $30M - below $150M emerging market threshold
        'sector': 'Technology',
        'industry': 'Software',
        'currency': 'USD',
        'country': 'United States'
    }

    cache.set_fundamentals('SMALL', small_cap_data)
    can_skip, reason = cache.can_skip_by_fundamentals('SMALL', CRITERIA)
    print(f"SMALL stock filtering: {'SKIP' if can_skip else 'PROCESS'} - {reason}")

    # Test with a large cap stock (should pass)
    large_cap_data = {
        'symbol': 'AAPL',
        'exchange': 'SMART',
        'market_cap_usd': 3000000000000,  # $3T - way above threshold
        'sector': 'Technology',
        'industry': 'Consumer Electronics',
        'currency': 'USD',
        'country': 'United States'
    }

    cache.set_fundamentals('AAPL', large_cap_data)
    can_skip, reason = cache.can_skip_by_fundamentals('AAPL', CRITERIA)
    print(f"AAPL stock filtering: {'SKIP' if can_skip else 'PROCESS'} - {reason}")

    # Test 2: Check cache retrieval
    print("\n2. Testing Cache Retrieval")
    fundamentals = cache.get_fundamentals('AAPL')
    if fundamentals:
        print(f"Retrieved AAPL fundamentals: ${fundamentals['market_cap_usd']/1e9:.1f}B market cap")
    else:
        print("Failed to retrieve AAPL fundamentals")

    # Test 3: Check market cap statistics
    print("\n3. Testing Market Cap Statistics")
    stats = cache.get_market_cap_stats()
    if stats:
        print(f"Cache contains {stats['total_stocks']} stocks")
        print(f"Average market cap: ${stats['avg_market_cap']/1e9:.1f}B")
    else:
        print("No statistics available (cache empty)")

    print("\nFundamental cache integration test completed")

if __name__ == '__main__':
    test_fundamental_cache()