#!/usr/bin/env python3
"""
IBKR Fundamentals Collection (multi-exchange, generalized in Task 11).

Fetches one-time / quarterly fundamentals from IBKR (ReportSnapshot,
ReportRatios, ContractDetails) and persists raw payloads to the
`ibkr_fundamentals` table, keyed by full yfinance-format ticker.

Supported exchanges (IBKR free delayed data): NSE, SEHK, LSE, JSE,
TADAWUL, ASX, SGX. Currency, IBKR exchange code, and symbol normalisation
are resolved via config/markets.MARKET_REGISTRY.

Seed sources:
  --source tickers        Read from the `tickers` table (default).
                          Correct for SEHK/LSE/JSE/TADAWUL/ASX/SGX, where the
                          Large+Mid+Small cap filter is already applied at
                          seed time by Task 12 / 12.5.
  --source fd_capfilter   Re-seed from `stock_fundamentals_fd` with the
                          market_cap_category IN ('Large Cap','Mid Cap','Small Cap')
                          filter applied. Required for the NSE re-seed leg —
                          NSE intentionally does NOT use the `tickers` shortcut.

USAGE:
    # SEHK / LSE / JSE / TADAWUL / ASX / SGX (six new exchanges):
    python -m scripts.etl.ibkr.collect_ibkr_fundamentals --exchange JSE
    python -m scripts.etl.ibkr.collect_ibkr_fundamentals --exchange SEHK --limit 5

    # NSE re-seed (criterion-preserving, force-refresh):
    python -m scripts.etl.ibkr.collect_ibkr_fundamentals \\
        --exchange NSE --source fd_capfilter --max-age-days 0
"""
import argparse
import asyncio
import io
import json
import math
import random
import sys
from datetime import datetime
from typing import List, Tuple

from ib_insync import IB, Stock, util

from config.markets import MARKET_REGISTRY, normalise_ibkr_symbol
from db import get_db

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

IBKR_PORT = 7496  # Live account port


def clean_dict(obj):
    """Recursively convert NaN floats to None for JSON-safety."""
    if isinstance(obj, dict):
        return {k: clean_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_dict(x) for x in obj]
    if isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


async def fetch_ibkr_fundamentals_only(ibkr_symbol: str, exchange: str, currency: str, port: int):
    """Fetch ReportSnapshot, ReportRatios, ContractDetails for one contract."""
    client_id = random.randint(1000, 9999)
    print(f"   -> Connecting (ID: {client_id}) for {ibkr_symbol}@{exchange}/{currency}...")
    ib = IB()
    results = {
        "xml_snapshot": None,
        "xml_ratios": None,
        "contract_details": None,
        "error": None,
        "success": False,
    }

    try:
        await asyncio.wait_for(ib.connectAsync('127.0.0.1', port, clientId=client_id), timeout=10)
        contract = Stock(ibkr_symbol, exchange, currency)
        try:
            qualified = await asyncio.wait_for(ib.qualifyContractsAsync(contract), timeout=15)
        except asyncio.TimeoutError:
            print("   ! Contract qualification timed out.")
            results["error"] = "Contract qualification timeout"
            return results

        if not qualified:
            results["error"] = "Contract not qualified"
            return results

        print(f"   -> Contract qualified. Symbol: {qualified[0].localSymbol}")

        print("   -> Requesting ReportSnapshot...")
        try:
            results["xml_snapshot"] = await asyncio.wait_for(
                ib.reqFundamentalDataAsync(qualified[0], reportType='ReportSnapshot'),
                timeout=20,
            )
            print(f"   -> Snapshot received ({len(results['xml_snapshot'] or '')} bytes)")
        except Exception as e:
            print(f"   ! ReportSnapshot failed: {e}")
            results["error"] = f"ReportSnapshot failed: {e}"
            return results

        print("   -> Requesting ReportRatios...")
        try:
            results["xml_ratios"] = await asyncio.wait_for(
                ib.reqFundamentalDataAsync(qualified[0], reportType='ReportRatios'),
                timeout=20,
            )
            print(f"   -> Ratios received ({len(results['xml_ratios'] or '')} bytes)")
        except Exception as e:
            print(f"   ! ReportRatios failed: {e}")
            results["error"] = f"ReportRatios failed: {e}"
            return results

        print("   -> Fetching Contract Details...")
        try:
            cds = await asyncio.wait_for(ib.reqContractDetailsAsync(qualified[0]), timeout=10)
            if not cds:
                print("   ! No contract details received.")
                results["error"] = "No contract details"
                return results
            results["contract_details"] = util.tree(cds[0])
            print("   -> Contract details captured.")
        except Exception as e:
            print(f"   ! Contract details failed: {e}")
            results["error"] = f"Contract details failed: {e}"
            return results

        results["success"] = True
        print("   ✅ Fundamentals collection complete.")

    except asyncio.TimeoutError:
        print("   ! IBKR connection or request timed out.")
        results["error"] = "Timeout"
    except Exception as e:
        print(f"   ! IBKR Error: {e}")
        results["error"] = str(e)
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("   -> Disconnected from IBKR.")
    return results


def save_fundamentals_to_db(ticker: str, fundamentals_data: dict) -> None:
    """Upsert fundamentals payload into ibkr_fundamentals."""
    print(f"[DB] Saving fundamentals for {ticker}...")
    db = get_db()
    db.execute(
        """
        INSERT INTO ibkr_fundamentals (ticker, xml_snapshot, xml_ratios, contract_details, last_updated)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (ticker) DO UPDATE SET
            xml_snapshot     = EXCLUDED.xml_snapshot,
            xml_ratios       = EXCLUDED.xml_ratios,
            contract_details = EXCLUDED.contract_details,
            last_updated     = EXCLUDED.last_updated
        """,
        (
            ticker,
            fundamentals_data.get('xml_snapshot'),
            fundamentals_data.get('xml_ratios'),
            json.dumps(clean_dict(fundamentals_data.get('contract_details'))),
            datetime.now(),
        ),
    )
    print(f"   ✅ Saved fundamentals for {ticker}")


def load_seed_tickers(exchange: str, source: str, include_inactive: bool) -> List[str]:
    """Resolve the input ticker universe for a given exchange + seed mode.

    Returns yfinance-format tickers (e.g. RELIANCE.NS, 5.HK, BP.L).
    """
    db = get_db()

    if source == 'tickers':
        if include_inactive:
            rows = db.query(
                "SELECT ticker FROM tickers WHERE market = %s ORDER BY ticker",
                (exchange,),
            )
        else:
            rows = db.query(
                "SELECT ticker FROM tickers "
                "WHERE market = %s AND (status = 'ACTIVE' OR status IS NULL) "
                "ORDER BY ticker",
                (exchange,),
            )
        return [r[0] for r in (rows or [])]

    if source == 'fd_capfilter':
        # NSE re-seed: apply the same criterion that produced the curated 398.
        # NSE is intentionally excluded from CAP_FILTERED_EXCHANGES in
        # screener/universe.py — the filter must run here, not via `tickers`.
        if exchange != 'NSE':
            raise ValueError("--source fd_capfilter is only valid for --exchange NSE")
        rows = db.query(
            "SELECT ticker FROM stock_fundamentals_fd "
            "WHERE market_cap_category IN ('Large Cap','Mid Cap','Small Cap') "
            "ORDER BY ticker"
        )
        return [r[0] for r in (rows or [])]

    raise ValueError(f"Unknown source: {source}")


def filter_resumable(tickers: List[str], max_age_days: int) -> Tuple[List[str], List[str]]:
    """Split tickers into (to_fetch, skipped_fresh) using ibkr_fundamentals.last_updated.

    max_age_days <= 0 disables resume (force-refresh everything).
    """
    if max_age_days <= 0 or not tickers:
        return list(tickers), []
    db = get_db()
    rows = db.query(
        "SELECT ticker FROM ibkr_fundamentals "
        "WHERE xml_snapshot IS NOT NULL "
        "  AND last_updated > NOW() - (%s || ' days')::INTERVAL",
        (max_age_days,),
    )
    fresh = {r[0] for r in (rows or [])}
    to_fetch = [t for t in tickers if t not in fresh]
    skipped = [t for t in tickers if t in fresh]
    return to_fetch, skipped


async def collect_fundamentals_for_exchange(exchange: str, tickers: List[str]) -> None:
    cfg = MARKET_REGISTRY[exchange]
    currency = cfg['ibkr_currency']
    print(f"\n[IBKR FUNDAMENTALS] {exchange} — {len(tickers)} tickers, currency {currency}")
    print("=" * 70)

    successful = failed = 0
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Processing {ticker}...")
        # ticker is yf-format (e.g. RELIANCE.NS, 5.HK, BP.L); strip the suffix.
        base = ticker.rsplit('.', 1)[0]
        ibkr_sym = normalise_ibkr_symbol(base, exchange)

        result = await fetch_ibkr_fundamentals_only(ibkr_sym, exchange, currency, IBKR_PORT)
        if result["success"]:
            save_fundamentals_to_db(ticker, result)
            successful += 1
        else:
            print(f"   ❌ Failed: {result['error']}")
            failed += 1

    print("\n[SUMMARY] Fundamentals Collection Complete:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    total = successful + failed
    if total:
        print(f"  📊 Success rate: {successful / total * 100:.1f}%")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="IBKR fundamentals collection — multi-exchange.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        '--exchange', required=True,
        choices=sorted(MARKET_REGISTRY.keys()),
        help='Exchange code (NSE, SEHK, LSE, JSE, TADAWUL, ASX, SGX, ...)',
    )
    p.add_argument(
        '--source', default='tickers', choices=['tickers', 'fd_capfilter'],
        help='Seed source. Default: tickers (correct for the six new exchanges). '
             'Use fd_capfilter only for the NSE re-seed leg.',
    )
    p.add_argument(
        '--max-age-days', type=int, default=90,
        help='Skip tickers whose ibkr_fundamentals row is fresher than this. '
             '0 = force-refresh (use for NSE re-seed). Default: 90.',
    )
    p.add_argument(
        '--include-inactive', action='store_true',
        help='With --source tickers, also include rows where status = INACTIVE.',
    )
    p.add_argument(
        '--limit', type=int, default=None,
        help='Process only the first N (post-resume-filter) tickers. For smoke tests.',
    )
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    exchange = args.exchange.upper()

    seed = load_seed_tickers(exchange, args.source, args.include_inactive)
    print(f"[SEED] {exchange} via --source {args.source}: {len(seed)} tickers")
    if not seed:
        print("[SEED] Nothing to do — empty seed.")
        return

    to_fetch, skipped = filter_resumable(seed, args.max_age_days)
    if skipped:
        print(f"[RESUME] Skipping {len(skipped)} tickers fresh within {args.max_age_days} days")
    if args.limit is not None:
        to_fetch = to_fetch[: args.limit]
        print(f"[LIMIT] Capped to {len(to_fetch)} tickers for this run")
    if not to_fetch:
        print("[RESUME] All tickers already fresh — nothing to fetch.")
        return

    await collect_fundamentals_for_exchange(exchange, to_fetch)


if __name__ == "__main__":
    asyncio.run(main())
