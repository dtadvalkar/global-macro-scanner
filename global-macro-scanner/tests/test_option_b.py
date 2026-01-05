from screener.core import screen_universe
from config import CRITERIA
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

def test_option_b():
    # We don't need a full universe for Option B test
    universe = [] # Scanner doesn't use the universe input
    
    print("Testing Full Option B Flow...")
    results = screen_universe(universe, CRITERIA)
    
    if results:
        print(f"✅ Success! Found {len(results)} confirmed results.")
    else:
        print("❌ Option B failed or found nothing.")

if __name__ == "__main__":
    test_option_b()
