"""
Intelligent Market Scheduler
Schedules scans based on optimal market hours to minimize rate limiting and maximize data freshness.
"""

import schedule
import time
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Callable
import os

# Market timezone mappings
MARKET_TIMEZONES = {
    'north_america': 'US/Eastern',  # TSX, NYSE
    'india': 'Asia/Kolkata',       # NSE
    'indonesia': 'Asia/Jakarta',   # IDX
    'thailand': 'Asia/Bangkok',    # SET
}

# Optimal scanning windows (in market local time)
SCAN_WINDOWS = {
    'north_america': {
        'start': '09:30',  # Market open + 1 hour (data stabilizing)
        'end': '15:30',    # Market close - 30 min
        'timezone': 'US/Eastern'
    },
    'india': {
        'start': '09:45',  # Market open + 30 min
        'end': '15:15',    # Market close - 15 min
        'timezone': 'Asia/Kolkata'
    },
    'indonesia': {
        'start': '09:30',  # Market open + 30 min
        'end': '15:30',    # Market close - 30 min
        'timezone': 'Asia/Jakarta'
    },
    'thailand': {
        'start': '10:30',  # Market open + 30 min
        'end': '16:30',    # Market close - 30 min
        'timezone': 'Asia/Bangkok'
    }
}

class MarketScheduler:
    """
    Schedules market scans at optimal times based on market hours and data freshness.
    """

    def __init__(self, user_timezone: str = 'US/Mountain'):
        """
        Initialize scheduler with user's local timezone.

        Args:
            user_timezone: User's local timezone (default: MST)
        """
        self.user_timezone = pytz.timezone(user_timezone)
        self.utc = pytz.timezone('UTC')
        self.scheduled_jobs = []

    def get_optimal_scan_time(self, market_region: str) -> datetime:
        """
        Calculate optimal scan time for a market region in user's timezone.

        Args:
            market_region: One of 'north_america', 'india', 'indonesia', 'thailand'

        Returns:
            datetime: Optimal scan time in user's timezone
        """
        if market_region not in SCAN_WINDOWS:
            raise ValueError(f"Unknown market region: {market_region}")

        window = SCAN_WINDOWS[market_region]
        market_tz = pytz.timezone(window['timezone'])

        # Get current time in market's timezone
        now_market = datetime.now(market_tz)

        # Parse scan start time
        start_hour, start_min = map(int, window['start'].split(':'))
        scan_start = now_market.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)

        # If we're past today's scan window, schedule for tomorrow
        if now_market > scan_start:
            scan_start = scan_start + timedelta(days=1)

        # Convert to user's timezone
        scan_start_user = scan_start.astimezone(self.user_timezone)

        return scan_start_user

    def schedule_market_scan(self, market_region: str, scan_function: Callable,
                           days_of_week: List[int] = None) -> schedule.Job:
        """
        Schedule a market scan for optimal time.

        Args:
            market_region: Market region to scan
            scan_function: Function to call for scanning
            days_of_week: List of weekday numbers (0=Monday, 6=Sunday). Default: weekdays only

        Returns:
            schedule.Job: The scheduled job
        """
        if days_of_week is None:
            days_of_week = [0, 1, 2, 3, 4]  # Monday-Friday

        scan_time = self.get_optimal_scan_time(market_region)
        scan_hour = scan_time.hour
        scan_minute = scan_time.minute

        # Schedule the job
        job = schedule.every().day.at(f"{scan_hour:02d}:{scan_minute:02d}").do(scan_function)

        # Restrict to specific days if provided
        if hasattr(job, 'tag'):
            job.tag(market_region)

        self.scheduled_jobs.append({
            'job': job,
            'market_region': market_region,
            'scan_time': scan_time,
            'function': scan_function
        })

        print(f"Scheduled {market_region} scan for {scan_time.strftime('%A %I:%M %p %Z')}")
        return job

    def get_schedule_summary(self) -> str:
        """Get a summary of all scheduled scans."""
        summary = "Market Scan Schedule:\n"
        summary += "=" * 50 + "\n"

        for job_info in self.scheduled_jobs:
            region = job_info['market_region']
            scan_time = job_info['scan_time']
            summary += f"{region.upper()}: {scan_time.strftime('%A %I:%M %p %Z')}\n"

        return summary

    def run_scheduler(self, test_mode: bool = False):
        """
        Run the scheduler. In test mode, runs once and exits.
        In production mode, runs continuously.
        """
        print(self.get_schedule_summary())

        if test_mode:
            print("TEST MODE: Running all scheduled scans once...")
            for job_info in self.scheduled_jobs:
                print(f"Running {job_info['market_region']} scan...")
                try:
                    job_info['function']()
                except Exception as e:
                    print(f"Error in {job_info['market_region']} scan: {e}")
            print("Test mode complete.")
            return

        print("Scheduler running. Press Ctrl+C to stop.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\nScheduler stopped by user.")

def create_optimal_schedule(scan_function: Callable) -> MarketScheduler:
    """
    Create an optimal scanning schedule for all market regions.

    Args:
        scan_function: Function that takes a market_config parameter

    Returns:
        MarketScheduler: Configured scheduler
    """

    # Create market-specific scan functions
    def scan_north_america():
        from config.markets import MARKETS
        markets = {k: v for k, v in MARKETS.items() if k in ['tsx']}  # Only North America
        scan_function(markets)

    def scan_asian_emerging():
        from config.markets import MARKETS
        markets = {k: v for k, v in MARKETS.items() if k in ['nse', 'idx', 'set']}  # Asian emerging
        scan_function(markets)

    # Initialize scheduler
    scheduler = MarketScheduler(user_timezone='US/Mountain')  # MST

    # Schedule scans
    scheduler.schedule_market_scan('north_america', scan_north_america)
    scheduler.schedule_market_scan('india', lambda: scan_function({'nse': True}))
    scheduler.schedule_market_scan('indonesia', lambda: scan_function({'idx': True}))
    scheduler.schedule_market_scan('thailand', lambda: scan_function({'set': True}))

    return scheduler

# Example usage and testing
def demo_scheduler():
    """Demonstrate the scheduler functionality."""

    def mock_scan(markets_config=None):
        markets_str = ", ".join(markets_config.keys()) if markets_config else "all markets"
        print(f"🔍 Scanning markets: {markets_str} at {datetime.now()}")

    print("Market Scheduler Demo")
    print("=" * 30)

    # Create scheduler
    scheduler = create_optimal_schedule(mock_scan)

    # Show schedule
    print("\n" + scheduler.get_schedule_summary())

    # Show next run times
    print("\nNext scan times:")
    for region in ['north_america', 'india', 'indonesia', 'thailand']:
        next_time = scheduler.get_optimal_scan_time(region)
        print(f"  {region}: {next_time.strftime('%A %I:%M %p %Z')}")

    # Run in test mode (execute all scans once)
    print("\nRunning test scans...")
    scheduler.run_scheduler(test_mode=True)

if __name__ == "__main__":
    demo_scheduler()