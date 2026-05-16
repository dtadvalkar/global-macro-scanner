#!/usr/bin/env python3
"""Monthly IDX/SET yahooquery fundamentals refresh scheduler.

Wraps `scripts/etl/yahooquery/seed_idx_set_fundamentals.py` (the Phase 2
seeder) so it runs once a month against `.JK` and `.BK` rows. Cap data for
these mid-band tickers drifts slowly; daily refresh would burn Yahoo quota
on near-static numbers.

Due rule:
  - Run on the 1st day of any month.
  - OR if the latest `stock_fundamentals.last_fundamental_update` for any
    `.JK` / `.BK` row is NULL or older than 25 days.

Flags:
  --run       Force a run regardless of the due rule.
  --dry-run   Print the command that would run; do not execute.
  (default)   Run only if due.

Exit codes:
  0  not due (default mode and not due)
  0  due/forced run succeeded
  nonzero  the seeder subprocess returned nonzero

Phase 5 of `docs/tasks/idx_set_enablement_plan.md`. No DB or subprocess
side effects on import; the `if __name__ == "__main__":` guard plus the
import-safety hook (`scripts/hooks/import_safety.py`) cover this.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SEEDER = REPO_ROOT / "scripts" / "etl" / "yahooquery" / "seed_idx_set_fundamentals.py"
STALE_DAYS = 25
LAST_UPDATE_SQL = (
    "SELECT MAX(last_fundamental_update) "
    "FROM stock_fundamentals "
    "WHERE ticker LIKE %s OR ticker LIKE %s"
)


def _ensure_repo_on_path() -> None:
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def get_last_update():
    """Return latest stock_fundamentals.last_fundamental_update for IDX/SET, or None."""
    _ensure_repo_on_path()
    from db import get_db  # local import keeps module import side-effect free

    db = get_db()
    try:
        row = db.query(LAST_UPDATE_SQL, ('%.JK', '%.BK'), fetch='one')
    finally:
        db.close()
    if not row:
        return None
    return row[0]


def is_first_of_month(today=None) -> bool:
    today = today or date.today()
    return today.day == 1


def days_since(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        ref = value.date()
    elif isinstance(value, date):
        ref = value
    else:
        return None
    return (date.today() - ref).days


def evaluate_due():
    """Return (should_run, reason, last_update_value)."""
    if is_first_of_month():
        return True, "First of month", None  # last_update still reported separately
    last_update = get_last_update()
    age = days_since(last_update)
    if last_update is None:
        return True, "No previous IDX/SET fundamental update found (NULL)", last_update
    if age is None:
        return True, f"Unrecognised last_update type: {type(last_update).__name__}", last_update
    if age > STALE_DAYS:
        return True, f"{age} days since last IDX/SET refresh (> {STALE_DAYS})", last_update
    return False, f"{age} days since last IDX/SET refresh (<= {STALE_DAYS})", last_update


def run_seeder(dry_run: bool = False) -> int:
    if not SEEDER.exists():
        print(f"[err] Seeder not found: {SEEDER}")
        return 1
    cmd = [sys.executable, str(SEEDER)]
    if dry_run:
        print(f"[dry-run] Would execute: {' '.join(cmd)}")
        print(f"[dry-run] cwd: {REPO_ROOT}")
        return 0
    print(f"[run] Executing: {' '.join(cmd)}")
    print(f"[run] cwd: {REPO_ROOT}")
    try:
        result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    except Exception as e:
        print(f"[err] Seeder subprocess failed to launch: {e}")
        return 1
    if result.returncode == 0:
        print("[ok] Seeder completed successfully.")
    else:
        print(f"[err] Seeder exited with code {result.returncode}")
    return result.returncode


def main(argv=None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    forced = "--run" in argv
    dry_run = "--dry-run" in argv

    print("MONTHLY IDX/SET YAHOOQUERY FUNDAMENTALS SCHEDULER")
    print("=" * 50)
    print(f"Today: {date.today().isoformat()}")
    print(f"Stale threshold: {STALE_DAYS} days")

    if forced:
        should_run, reason, last_update = True, "Forced run requested", None
        # Still fetch last_update for reporting context, but tolerate failures.
        try:
            last_update = get_last_update()
        except Exception as e:
            print(f"[warn] Could not read last_fundamental_update: {e}")
    else:
        try:
            should_run, reason, last_update = evaluate_due()
        except Exception as e:
            print(f"[err] Could not evaluate due rule: {e}")
            return 1

    print(f"Last IDX/SET update: {last_update if last_update is not None else 'NULL (never)'}")
    print(f"Should run: {should_run}")
    print(f"Reason: {reason}")
    print()

    if not should_run and not dry_run:
        print("[skip] Not due. Use --run to force.")
        return 0

    return run_seeder(dry_run=dry_run)


if __name__ == "__main__":
    sys.exit(main())
