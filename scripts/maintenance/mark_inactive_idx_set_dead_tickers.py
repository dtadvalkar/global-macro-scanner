r"""Mark dead IDX / SET tickers INACTIVE.

A "dead" ticker satisfies all of:

- `tickers.market` is IDX or SET
- `tickers.ticker` ends in `.JK` or `.BK`
- `tickers.status` is ACTIVE or NULL
- ZERO rows in `prices_daily`
- No positive `stock_fundamentals.mkt_cap_usd`

Defaults to dry-run. Pass `--apply` to actually mutate. The script
aborts if the candidate count exceeds 50 unless `--force` is also
supplied, to prevent a quiet large-scale deactivation.

Examples (PowerShell):

    .\.venv\Scripts\python.exe scripts\maintenance\mark_inactive_idx_set_dead_tickers.py
    .\.venv\Scripts\python.exe scripts\maintenance\mark_inactive_idx_set_dead_tickers.py --apply
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

# Repo root on sys.path so `from db import get_db` works when run directly.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from db import get_db                                                       # noqa: E402

CANDIDATE_SQL = "analytics/dead_idx_set_tickers.sql"
CAP_DEFAULT = 50
NEW_STATUS = "INACTIVE"
STATUS_MESSAGE = "Dead IDX/SET cleanup: no prices_daily rows + no positive mkt_cap_usd"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Mark dead IDX/SET .JK/.BK tickers INACTIVE (dry-run by default)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually update DB. Without this flag the script only previews.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Required if candidate count exceeds the safety cap.",
    )
    parser.add_argument(
        "--cap",
        type=int,
        default=CAP_DEFAULT,
        help=f"Maximum candidates without --force (default {CAP_DEFAULT}).",
    )
    return parser.parse_args()


def fetch_candidates(db):
    rows = db.query_file(CANDIDATE_SQL, ('%.JK', '%.BK'))
    return rows or []


def print_candidates(rows):
    by_market = Counter(r[1] for r in rows)
    print(f"Candidates: {len(rows)} total")
    for market, count in sorted(by_market.items()):
        print(f"  {market}: {count}")
    print()
    print(f"{'ticker':<14} {'market':<8} {'status':<10} {'prices_rows':>11} {'mkt_cap_usd':>14}")
    print("-" * 60)
    for ticker, market, status, prices_rows, mcap in rows:
        status_str = status if status is not None else "NULL"
        print(
            f"{ticker:<14} {market:<8} {status_str:<10} {prices_rows:>11d} "
            f"{(float(mcap) if mcap is not None else 0):>14.2f}"
        )


def apply_changes(db, rows):
    """Use the existing db.update_ticker_status helper one row at a time.

    The helper records `status`, `status_message`, and bumps `last_updated`;
    that's exactly the per-row UPDATE we want. Iterating is fine at this
    cap (<= 50 rows) and avoids introducing a new SQL file just for this.
    """
    changed = 0
    for ticker, market, old_status, _prices, _mcap in rows:
        db.update_ticker_status(ticker, NEW_STATUS, STATUS_MESSAGE)
        old_repr = old_status if old_status is not None else "NULL"
        print(f"  {ticker:<14} ({market}) {old_repr} -> {NEW_STATUS}")
        changed += 1
    return changed


def main():
    args = parse_args()
    db = get_db()
    rows = fetch_candidates(db)

    if not rows:
        print("No candidates match the strict dead-ticker rule. Nothing to do.")
        return 0

    print_candidates(rows)

    if len(rows) > args.cap and not args.force:
        print(
            f"\nABORT: candidate count {len(rows)} exceeds safety cap {args.cap}. "
            "Re-run with --force only after auditing the list above."
        )
        return 2

    if not args.apply:
        print(
            "\n[dry-run] No changes made. Pass --apply to mark these tickers INACTIVE."
        )
        return 0

    print(f"\nApplying status={NEW_STATUS} to {len(rows)} tickers...")
    changed = apply_changes(db, rows)
    print(f"\n[ok] Updated {changed} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
