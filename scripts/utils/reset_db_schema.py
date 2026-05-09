"""Truncate `tickers` and `stock_fundamentals`.

Destructive, irreversible. Manual use only — requires typed confirmation.
Importing this module has no side effects.
"""
from db import get_db


CONFIRMATION_PHRASE = "TRUNCATE tickers stock_fundamentals"


def truncate_tables() -> None:
    """Truncate `tickers` and `stock_fundamentals`. Caller has already confirmed intent."""
    db = get_db()
    print("Truncating 'tickers' and 'stock_fundamentals'...")
    db.execute_file('admin/reset_truncate_tickers_and_fundamentals.sql')
    print("Done. Both tables are now empty.")


def _main() -> int:
    print("--- Clear Database Data (TRUNCATE) ---")
    print("This will TRUNCATE 'tickers' and 'stock_fundamentals' — destructive, irreversible.")
    print(f"To confirm, type exactly: {CONFIRMATION_PHRASE}")
    response = input("> ").strip()
    if response != CONFIRMATION_PHRASE:
        print("Confirmation did not match. Aborting; no changes made.")
        return 1
    truncate_tables()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
