import asyncio
from ib_insync import IB, Stock
import logging

# Set up logging to console to see EXACTLY what IBKR is saying
logging.basicConfig(level=logging.INFO)

async def test_xml():
    ib = IB()
    try:
        print("Connecting to IBKR LIVE Trading (7496)...")
        await ib.connectAsync('127.0.0.1', 7496, clientId=131)
        
        contract = Stock('RELIANCE', 'NSE', 'INR')
        print(f"Qualifying contract for {contract.symbol}...")
        qualified = await ib.qualifyContractsAsync(contract)
        
        if not qualified:
            print("FAILED to qualify contract.")
            return

        print(f"QUALIFIED: {qualified[0]}")
        
        ib.reqMarketDataType(3) # Delayed

        print("Requesting ReportSnapshot. This can take up to 60s...")
        try:
            # We use the blocking-style await here
            xml = await asyncio.wait_for(ib.reqFundamentalDataAsync(qualified[0], reportType='ReportSnapshot'), timeout=45)
            if xml:
                print(f"SUCCESS! Received {len(xml)} bytes.")
                with open("debug_reliance.xml", "w") as f:
                    f.write(xml)
            else:
                print("FAILURE: IBKR returned an empty string for the XML.")
        except asyncio.TimeoutError:
            print("TIMEOUT: IBKR did not respond to the XML request within 45s.")
        except Exception as e:
            print(f"ERROR: {e}")

        ib.disconnect()
    except Exception as e:
        print(f"CONNECTION ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_xml())

if __name__ == "__main__":
    asyncio.run(test_xml())
