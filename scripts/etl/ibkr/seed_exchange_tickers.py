"""
seed_exchange_tickers.py

Bootstrap the tickers table for exchanges that have no FinanceDatabase seed
(SEHK, LSE, JSE, TADAWUL).

Two sources:
  --source static (default)
      Read tickers from scripts/etl/ibkr/universe_lists/{exchange}.json.
      These JSONs are manually-curated major-index constituents (HSI, FTSE 100,
      JSE Top 40, TASI large-caps). Refresh the JSON every 6–12 months.

  --source ibkr
      Use the IBKR MOST_ACTIVE server-side scanner.  Requires an IBKR scanner
      subscription — returns 0 results on the default free delayed feed.
      Kept for if/when scanner access is enabled.

After seeding, run collect_historical_yfinance.py --exchange <code>[,...] to
backfill 10y OHLCV history for the seeded exchanges.

USAGE:
    PYTHONPATH="." python scripts/etl/ibkr/seed_exchange_tickers.py
    PYTHONPATH="." python scripts/etl/ibkr/seed_exchange_tickers.py --exchanges SEHK,LSE
    PYTHONPATH="." python scripts/etl/ibkr/seed_exchange_tickers.py --dry-run
    PYTHONPATH="." python scripts/etl/ibkr/seed_exchange_tickers.py --source ibkr

Symbol translation for the IBKR-scanner path is handled by ibkr_to_yfinance()
in config/markets.py.  Static JSON lists are already in yfinance format.
"""

import sys
import os
import io
import json
import time
import argparse

sys.path.append(os.getcwd())
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

from db import get_db

STATIC_LIST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'universe_lists'
)

# Exchanges with a curated static list on disk.
STATIC_EXCHANGES = ['SEHK', 'LSE', 'JSE', 'TADAWUL']

# IBKR scanner config per exchange:
#   exchange_code → (instrument, location_code)
# Location codes verified against live TWS reqScannerParameters() on 2026-04-22.
# LSE and TADAWUL are listed as access-restricted in IBKR's scanner XML — they
# may require specific market-data subscriptions beyond the default free delayed
# feed. If a scan returns 0 results at runtime, that's why.
#
# JSE (Johannesburg) has NO IBKR scanner location code — South Africa is absent
# from the STK.EU / STK.ME / STK.HK location trees. JSE universe must be seeded
# from the static list (see universe_lists/jse.json).
EXCHANGE_SCAN_CONFIG = {
    'SEHK':    ('STK', 'STK.HK.SEHK'),
    'LSE':     ('STK', 'STK.EU.LSE'),
    'TADAWUL': ('STK', 'STK.ME.TADAWUL'),
}

IBKR_PORT = int(os.getenv('IBKR_PORT', '7496'))
IBKR_HOST = os.getenv('IBKR_HOST', '127.0.0.1')
CLIENT_ID = 96  # distinct from main pipeline IDs


def get_static_tickers(exchange: str) -> list[str]:
    """Load curated yfinance-format tickers from universe_lists/{exchange}.json."""
    path = os.path.join(STATIC_LIST_DIR, f'{exchange.lower()}.json')
    if not os.path.exists(path):
        print(f"  ⚠️  No static list at {path} — skipping {exchange}.")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    tickers = data.get('tickers', [])
    print(f"  Loaded {len(tickers)} tickers for {exchange} from {data.get('index_name', 'static list')} (source_date={data.get('source_date','?')})")
    return tickers


def scan_ibkr_exchange(ib, exchange: str, instrument: str, location: str) -> list[str]:
    """Run MOST_ACTIVE scanner for one exchange, return yfinance-format tickers.

    Requires an IBKR scanner subscription — returns 0 on a free delayed-data feed.
    """
    from ib_async import ScannerSubscription
    from config.markets import ibkr_to_yfinance

    subscription = ScannerSubscription(
        instrument=instrument,
        locationCode=location,
        scanCode='MOST_ACTIVE',
    )
    print(f"  Scanning {exchange} ({location})...")
    try:
        scan_data = ib.reqScannerData(subscription)
    except Exception as e:
        print(f"  ⚠️  Scanner error for {exchange}: {e}")
        return []

    tickers = [ibkr_to_yfinance(item.contractDetails.contract.symbol, exchange)
               for item in scan_data]
    print(f"  Found {len(tickers)} tickers for {exchange}")
    return tickers


def main():
    parser = argparse.ArgumentParser(description='Seed tickers table from static list or IBKR scanner.')
    parser.add_argument(
        '--source',
        choices=['static', 'ibkr'],
        default='static',
        help='Ticker source (default: static). `ibkr` requires an IBKR scanner subscription.',
    )
    parser.add_argument(
        '--exchanges',
        default=','.join(STATIC_EXCHANGES),
        help=f'Comma-separated exchange codes (default: all). Available: {", ".join(STATIC_EXCHANGES)}',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print tickers found without writing to DB.',
    )
    args = parser.parse_args()

    requested = [e.strip().upper() for e in args.exchanges.split(',')]

    if args.source == 'static':
        valid = STATIC_EXCHANGES
    else:
        valid = list(EXCHANGE_SCAN_CONFIG.keys())

    unknown = [e for e in requested if e not in valid]
    if unknown:
        print(f"❌ Unknown exchange(s) for source={args.source}: {', '.join(unknown)}")
        print(f"   Available: {', '.join(valid)}")
        sys.exit(1)

    print("=" * 70)
    print("EXCHANGE TICKER SEEDING")
    print("=" * 70)
    print(f"Source    : {args.source}")
    print(f"Exchanges : {', '.join(requested)}")
    if args.source == 'ibkr':
        print(f"IBKR      : {IBKR_HOST}:{IBKR_PORT}")
    print(f"Dry-run   : {args.dry_run}")
    print("=" * 70)

    ib = None
    if args.source == 'ibkr':
        from ib_async import IB, util
        util.patchAsyncio()
        ib = IB()
        try:
            ib.connect(IBKR_HOST, IBKR_PORT, clientId=CLIENT_ID)
            ib.reqMarketDataType(3)
            print(f"Connected to IBKR (delayed data mode).\n")
        except Exception as e:
            print(f"❌ IBKR connection failed: {e}")
            print(f"   Is TWS running on {IBKR_HOST}:{IBKR_PORT}?")
            sys.exit(1)

    db = get_db()
    total_seeded = 0

    for exchange in requested:
        if args.source == 'static':
            tickers = get_static_tickers(exchange)
        else:
            instrument, location = EXCHANGE_SCAN_CONFIG[exchange]
            tickers = scan_ibkr_exchange(ib, exchange, instrument, location)

        if not tickers:
            print(f"  ⚪ No tickers returned for {exchange} — skipping.\n")
            continue

        if args.dry_run:
            print(f"  [dry-run] Would seed {len(tickers)} tickers for {exchange}:")
            for t in tickers[:10]:
                print(f"    {t}")
            if len(tickers) > 10:
                print(f"    ... and {len(tickers) - 10} more")
        else:
            db.save_tickers(exchange, tickers)
            print(f"  ✅ Seeded {len(tickers)} tickers for {exchange} into tickers table.\n")
            total_seeded += len(tickers)

        if args.source == 'ibkr':
            time.sleep(1)

    if ib is not None:
        try:
            ib.disconnect()
        except Exception:
            pass

    print("=" * 70)
    if args.dry_run:
        print("DRY RUN COMPLETE — no data written.")
    else:
        print(f"SEEDING COMPLETE — {total_seeded} total tickers written.")
        print()
        print("Next step: backfill 10y OHLCV from yfinance")
        exch_arg = ','.join(requested)
        print(f"  PYTHONPATH='.' python scripts/etl/yfinance/collect_historical_yfinance.py --exchange {exch_arg}")
    print("=" * 70)


if __name__ == '__main__':
    main()
