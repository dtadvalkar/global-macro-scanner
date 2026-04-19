#!/usr/bin/env python3
"""
Test retry mechanism on just 3 failed tickers to understand the errors
"""

import asyncio
import json
import psycopg2
from ib_insync import IB, Stock, util
from config import DB_CONFIG
import sys
import io
import logging
from datetime import datetime

# Force UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add current directory to path for imports
sys.path.append('.')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def clean_dict(obj):
    """Recursively converts NaN values to None for JSON compatibility."""
    import math
    if isinstance(obj, dict):
        return {k: clean_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_dict(x) for x in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

async def test_single_ticker(ticker: str, port: int = 7496):
    """Test fundamentals collection for a single ticker with detailed logging."""
    base_symbol = ticker.split('.')[0]
    logging.info(f"Testing {ticker} (base: {base_symbol})")

    results = {
        "xml_snapshot": None,
        "xml_ratios": None,
        "contract_qualified": False,
        "error": None,
        "success": False
    }

    ib = IB()
    try:
        logging.info("Connecting to IBKR...")
        await asyncio.wait_for(ib.connectAsync('127.0.0.1', port, clientId=1001), timeout=15)
        logging.info("Connected successfully")

        # Test contract qualification
        contract = Stock(base_symbol, 'NSE', 'INR')
        logging.info(f"Qualifying contract for {base_symbol}.NSE...")
        qualified = await asyncio.wait_for(ib.qualifyContractsAsync(contract), timeout=15)

        if not qualified:
            results["error"] = "Contract not qualified - ticker may not exist in IBKR"
            logging.error("Contract qualification failed")
            return results

        results["contract_qualified"] = True
        logging.info(f"Contract qualified: {qualified[0].localSymbol}")

        # Test ReportSnapshot
        logging.info("Testing ReportSnapshot...")
        try:
            snapshot = await asyncio.wait_for(
                ib.reqFundamentalDataAsync(qualified[0], reportType='ReportSnapshot'),
                timeout=30
            )
            results["xml_snapshot"] = snapshot
            logging.info(f"ReportSnapshot SUCCESS: {len(snapshot)} bytes")
        except Exception as e:
            results["error"] = f"ReportSnapshot failed: {e}"
            logging.error(f"ReportSnapshot failed: {e}")
            return results

        # Test ReportRatios
        logging.info("Testing ReportRatios...")
        try:
            ratios = await asyncio.wait_for(
                ib.reqFundamentalDataAsync(qualified[0], reportType='ReportRatios'),
                timeout=30
            )
            results["xml_ratios"] = ratios
            results["success"] = True
            logging.info(f"ReportRatios SUCCESS: {len(ratios)} bytes")
        except Exception as e:
            results["error"] = f"ReportRatios failed: {e}"
            logging.error(f"ReportRatios failed: {e}")
            return results

    except asyncio.TimeoutError:
        results["error"] = "Connection timeout"
        logging.error("Connection timeout")
    except Exception as e:
        results["error"] = f"Connection error: {e}"
        logging.error(f"Connection error: {e}")
    finally:
        if ib.isConnected():
            ib.disconnect()
            logging.info("Disconnected from IBKR")

    return results

async def main():
    """Test 3 failed tickers."""
    print("TESTING FUNDAMENTALS RETRY ON 3 FAILED TICKERS")
    print("=" * 60)

    # Test just 3 failed tickers
    test_tickers = ["AARTIDRUGS.NSE", "ABBOTINDIA.NSE", "ADANIGREEN.NSE"]

    for ticker in test_tickers:
        print(f"\n{'='*40}")
        print(f"TESTING: {ticker}")
        print('=' * 40)

        result = await test_single_ticker(ticker)

        print(f"Contract qualified: {result['contract_qualified']}")
        print(f"Snapshot success: {result['xml_snapshot'] is not None}")
        print(f"Ratios success: {result['xml_ratios'] is not None}")
        print(f"Overall success: {result['success']}")

        if result['error']:
            print(f"Error: {result['error']}")

        # Small delay between tests
        await asyncio.sleep(2)

    print(f"\n{'='*60}")
    print("TEST COMPLETE")

if __name__ == "__main__":
    asyncio.run(main())