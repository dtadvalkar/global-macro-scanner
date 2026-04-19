import asyncio
from ib_insync import IB

async def check_ibkr(port):
    ib = IB()
    try:
        print(f"Connecting to port {port}...")
        await ib.connectAsync('127.0.0.1', port, clientId=124)
        print(f"Connected to port {port}")
        ib.disconnect()
    except Exception as e:
        print(f"Failed to connect to port {port}: {e}")

if __name__ == "__main__":
    asyncio.run(check_ibkr(7497))
    asyncio.run(check_ibkr(7496))
