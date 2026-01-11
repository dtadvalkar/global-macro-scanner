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

# Market timezone mappings - expanded for all supported markets
MARKET_TIMEZONES = {
    'north_america': 'US/Eastern',  # US, Canada
    'europe': 'Europe/London',      # UK, Germany, France
    'india': 'Asia/Kolkata',        # NSE
    'asia_pacific': 'Asia/Tokyo',   # Japan, Australia, Singapore, Hong Kong
    'emerging_asia': 'Asia/Bangkok' # Thailand, Indonesia
}

# Market to region mapping
MARKET_REGIONS = {
    'us': 'north_america',
    'tsx': 'north_america',  # Canada
    'uk': 'europe',
    'germany': 'europe',
    'france': 'europe',
    'japan': 'asia_pacific',
    'australia': 'asia_pacific',
    'singapore': 'asia_pacific',
    'hongkong': 'asia_pacific',
    'nse': 'india',
    'idx': 'emerging_asia',  # Indonesia
    'set': 'emerging_asia'   # Thailand
}

# Optimal scanning windows (in market local time)
# Times chosen to be 30-60 minutes after market open for data stabilization
SCAN_WINDOWS = {
    'north_america': {
        'start': '09:30',  # US market open + 30 min
        'end': '15:30',    # US market close - 30 min
        'timezone': 'US/Eastern'
    },
    'europe': {
        'start': '09:30',  # London open + 30 min
        'end': '16:30',    # London close - 30 min
        'timezone': 'Europe/London'
    },
    'india': {
        'start': '09:45',  # NSE open + 30 min
        'end': '15:15',    # NSE close - 15 min
        'timezone': 'Asia/Kolkata'
    },
    'asia_pacific': {
        'start': '09:30',  # Tokyo open + 30 min (covers most APAC)
        'end': '15:30',    # Tokyo close - 30 min
        'timezone': 'Asia/Tokyo'
    },
    'emerging_asia': {
        'start': '10:30',  # Bangkok open + 30 min (covers Thailand/Indonesia)
        'end': '16:30',    # Bangkok close - 30 min
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

def create_optimal_schedule(scan_function: Callable, enabled_markets: Dict = None) -> MarketScheduler:
    """
    Create an optimal scanning schedule for all enabled market regions.

    Args:
        scan_function: Function that takes a market_config parameter
        enabled_markets: Dict of enabled markets (defaults to config.markets.MARKETS)

    Returns:
        MarketScheduler: Configured scheduler
    """
    if enabled_markets is None:
        from config.markets import MARKETS
        enabled_markets = MARKETS

    # Group markets by region
    region_markets = {}
    for market_key, is_enabled in enabled_markets.items():
        if not is_enabled:
            continue

        region = MARKET_REGIONS.get(market_key)
        if region:
            if region not in region_markets:
                region_markets[region] = []
            region_markets[region].append(market_key)

    # Initialize scheduler
    scheduler = MarketScheduler(user_timezone='US/Mountain')  # MST

    # Create and schedule region-specific scan functions
    for region, markets in region_markets.items():
        def scan_region(region_markets=markets):
            markets_config = {m: True for m in region_markets}
            scan_function(markets_config)

        scheduler.schedule_market_scan(region, scan_region)

    return scheduler

def create_windows_task_scheduler_script():
    """
    Generate Windows Task Scheduler XML and batch file for automated scanning.

    Returns:
        tuple: (xml_content, batch_content) for Task Scheduler setup
    """
    import os

    # Get script directory and python path
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python_exe = os.sys.executable
    main_script = os.path.join(script_dir, 'main_automated.py')

    # Create batch file content
    batch_content = f'''@echo off
REM Global Market Scanner - Automated Daily Scan
REM Generated for Windows Task Scheduler

cd /d "{script_dir}"
"{python_exe}" "{main_script}" --scheduled-scan

REM Keep window open briefly to show any errors
timeout /t 30 /nobreak > nul
'''

    # Create XML for Task Scheduler (daily at 6 AM MST)
    xml_content = '''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mitask">
  <RegistrationInfo>
    <Description>Global Market Scanner - Automated Daily Scan</Description>
    <Author>SYSTEM</Author>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2024-01-01T13:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>''' + os.path.join(script_dir, 'scheduler', 'run_market_scanner.bat') + '''</Command>
      <Arguments></Arguments>
      <WorkingDirectory>''' + script_dir + '''</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''

    return xml_content, batch_content

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
    regions = ['north_america', 'europe', 'india', 'asia_pacific', 'emerging_asia']
    for region in regions:
        try:
            next_time = scheduler.get_optimal_scan_time(region)
            print(f"  {region}: {next_time.strftime('%A %I:%M %p %Z')}")
        except ValueError:
            pass  # Skip regions not in SCAN_WINDOWS

    # Run in test mode (execute all scans once)
    print("\nRunning test scans...")
    scheduler.run_scheduler(test_mode=True)

if __name__ == "__main__":
    demo_scheduler()