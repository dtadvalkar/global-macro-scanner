from ib_insync import *

def discover_scanners():
    ib = IB()
    try:
        ib.connect('127.0.0.1', 7497, clientId=15)
        
        print("🔍 Requesting Scanner XML parameters from IBKR...")
        # This returns a large XML string of everything IBKR supports
        xml = ib.reqScannerParameters()
        
        with open('ib_parameters.xml', 'w') as f:
            f.write(xml)
            
        print("✅ Scanner parameters saved to 'ib_parameters.xml'")
        print("You can now search this file for <LocationCode> or <ScanCode>.")
        
        ib.disconnect()
    except Exception as e:
        print(f"❌ Discovery failed: {e}")

if __name__ == "__main__":
    discover_scanners()
