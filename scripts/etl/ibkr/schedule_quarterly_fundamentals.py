#!/usr/bin/env python3
"""
Quarterly IBKR Fundamentals Update Scheduler

Automatically runs fundamentals collection on a quarterly schedule.
Fundamentals data changes infrequently (quarterly earnings, etc.).

SCHEDULE:
- Runs on the 1st day of each quarter (Jan, Apr, Jul, Oct)
- Can also be run manually with --force

USAGE:
    python schedule_quarterly_fundamentals.py        # Check if due to run
    python schedule_quarterly_fundamentals.py --run  # Force run now
    python schedule_quarterly_fundamentals.py --dry-run  # Show what would run
"""

import subprocess
import sys
from datetime import datetime, date
from pathlib import Path
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from config import DB_CONFIG
import psycopg2

def is_quarter_start():
    """Check if today is the start of a quarter (1st of Jan, Apr, Jul, Oct)."""
    today = date.today()
    return today.day == 1 and today.month in [1, 4, 7, 10]

def get_last_fundamentals_update():
    """Get the date of the last fundamentals update from database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()

        # Check when fundamentals were last updated
        cur.execute("""
            SELECT MAX(last_updated)
            FROM raw_ibkr_nse
            WHERE xml_snapshot IS NOT NULL
        """)

        result = cur.fetchone()
        last_update = result[0] if result and result[0] else None

        cur.close()
        conn.close()
        return last_update

    except Exception as e:
        print(f"Error checking last update: {e}")
        return None

def should_run_fundamentals_update():
    """Determine if fundamentals update should run."""
    if "--force" in sys.argv or "--run" in sys.argv:
        return True, "Forced run requested"

    if not is_quarter_start():
        return False, "Not quarter start date"

    last_update = get_last_fundamentals_update()
    if last_update is None:
        return True, "No previous fundamentals data found"

    # Check if it's been more than 80 days since last update
    days_since_update = (datetime.now().date() - last_update.date()).days
    if days_since_update > 80:  # ~3 months
        return True, f"{days_since_update} days since last update"

    return False, f"Last update was {days_since_update} days ago"

def run_fundamentals_update(dry_run=False):
    """Execute the fundamentals update process."""
    script_path = Path(__file__).parent / "collect_ibkr_fundamentals.py"

    if not script_path.exists():
        print(f"❌ Fundamentals script not found: {script_path}")
        return False

    # Get ticker count from our investment universe
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG['db_name'],
            user=DB_CONFIG['db_user'],
            password=DB_CONFIG['db_pass'],
            host=DB_CONFIG['db_host'],
            port=DB_CONFIG['db_port']
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM raw_fd_nse")
        ticker_count = cur.fetchone()[0]
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error getting ticker count: {e}")
        return False

    cmd = [sys.executable, str(script_path), "--all-universe"]

    if dry_run:
        print(f"🔍 DRY RUN - Would execute: {' '.join(cmd)}")
        print(f"   Expected to process {ticker_count} tickers")
        return True

    print(f"🚀 Starting quarterly fundamentals update...")
    print(f"   Processing {ticker_count} tickers")
    print(f"   Command: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent)
        success = result.returncode == 0
        if success:
            print("\n✅ Quarterly fundamentals update completed successfully!")
        else:
            print(f"\n❌ Quarterly fundamentals update failed with code {result.returncode}")
        return success
    except Exception as e:
        print(f"\n❌ Error running fundamentals update: {e}")
        return False

def main():
    """Main function."""
    should_run, reason = should_run_fundamentals_update()

    print("QUARTERLY IBKR FUNDAMENTALS SCHEDULER")
    print("=" * 50)
    print(f"Current date: {date.today()}")
    print(f"Quarter start: {is_quarter_start()}")
    print(f"Should run: {should_run}")
    print(f"Reason: {reason}")

    last_update = get_last_fundamentals_update()
    if last_update:
        print(f"Last update: {last_update.date()}")
    else:
        print("Last update: Never")

    print()

    if "--dry-run" in sys.argv:
        print("🔍 DRY RUN MODE")
        run_fundamentals_update(dry_run=True)
    elif should_run or "--run" in sys.argv:
        print("▶️  EXECUTING FUNDAMENTALS UPDATE")
        success = run_fundamentals_update(dry_run=False)
        if success:
            print("\n📅 Next scheduled run: Start of next quarter")
        sys.exit(0 if success else 1)
    else:
        print("⏰ Not scheduled to run today")
        print("💡 Use --run to force execution")
        sys.exit(0)

if __name__ == "__main__":
    main()