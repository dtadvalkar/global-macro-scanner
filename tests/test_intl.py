from screener.core import screen_universe
from config import CRITERIA
import os
from dotenv import load_dotenv
from data.providers import IBKRScannerProvider

load_dotenv()

def test_intl_scans():
    host = os.getenv("IBKR_HOST", "127.0.0.1")
    port = int(os.getenv("IBKR_PORT", "7496"))
    client_id = 60
    
    scanner = IBKRScannerProvider(host, port, client_id)
    
    print("Testing Canada Scan...")
    found_ca = scanner.get_scanner_results('STOCK.NA', 'STK.NA.CANADA', 'MOST_ACTIVE')
    print(f"  Canada Results: {len(found_ca)}")
    if found_ca: print(f"  Example: {found_ca[0]}")
    
    print("Testing India Scan...")
    found_in = scanner.get_scanner_results('STOCK.HK', 'STK.HK.NSE', 'MOST_ACTIVE')
    print(f"  India Results: {len(found_in)}")
    if found_in: print(f"  Example: {found_in[0]}")

if __name__ == "__main__":
    test_intl_scans()
