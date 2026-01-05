import sys
import io
from screener.core import screen_universe
from config import CRITERIA
import os
from dotenv import load_dotenv

load_dotenv()

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_option_b():
    universe = []
    print("Testing Full Option B Flow (UTF-8)...")
    results = screen_universe(universe, CRITERIA)
    
    if results:
        print(f"Success! Found {len(results)} confirmed results.")
        for r in results:
            print(f"  {r['symbol']}: {r['price']}")
    else:
        print("Option B failed or found nothing.")

if __name__ == "__main__":
    test_option_b()
