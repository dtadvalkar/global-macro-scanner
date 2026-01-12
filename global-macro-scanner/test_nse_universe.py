#!/usr/bin/env python3
"""Test NSE Universe Loading Only"""

from config import MARKETS
from screener.universe import get_universe

# Create markets dict with only NSE enabled
nse_only_markets = {k: False for k in MARKETS}
nse_only_markets['nse'] = True

print(f"Loading NSE universe with markets: {nse_only_markets}")
universe = get_universe(nse_only_markets)
print(f"Loaded {len(universe)} NSE stocks")