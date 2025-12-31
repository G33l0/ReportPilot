"""
Main entry point with scheduler support for the activity reporting system.

This script can run in two modes:
1. One-time execution: Generate report immediately and exit
2. Scheduled execution: Run periodically based on configuration

Usage:
    python run.py                    # One-time execution
    python run.py --schedule         # Run with scheduler
    python run.py --schedule --now   # Run immediately then schedule
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config_loader import ConfigLoader
from src.utils.logger import setup_logger
from src.main import ActivityReporter

# APScheduler imports
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = setup_logger(__name__)


class ReportScheduler:
    """
    Scheduler for automated report generation.

    Supports:
    - Cron-style scheduling
    - Interval-based scheduling
    - One-time execution

    Example:
        >>> scheduler = ReportScheduler(config)
        >>> scheduler.start()
    """

    def __init__(self, config: ConfigLoader):
        """
        Initialize the report scheduler.

        Args:
            config: ConfigLoader instance with system configuration
        """
        self.config = config
        self.scheduler = BlockingScheduler()
        self.reporter = ActivityReporter(config)

    def job_function(self):
        """Execute the reporting job."""
        logger.info("Scheduled job triggered")
        try:
            self.reporter.run()
        except Exception as e:
            logger.error(f"Scheduled job failed: {str(e)}")

    def setup_schedule(self):
        """Set up the schedule based on configuration."""
        schedule_type = self.config.get('schedule.type', 'interval')

        if schedule_type == 'cron':
            # Cron-style scheduling
            cron_config = self.config.get('schedule.cron', {})

            # Default: Every Monday at 9:00 AM
            day_of_week = cron_config.get('day_of_week', 'mon')
            hour = cron_config.get('hour', 9)
            minute = cron_config.get('minute', 0)

            trigger = CronTrigger(
                day_of_week=day_of_week,
                hour=hour,
                minute=minute
            )

            self.scheduler.add_job(
                self.job_function,
                trigger,
                id='activity_report_job'
            )

            logger.info(
                f"Scheduled job: Every {day_of_week} at {hour:02d}:{minute:02d}"
            )

        elif schedule_type == 'interval':
            # Interval-based scheduling
            interval_config = self.config.get('schedule.interval', {})

            weeks = interval_config.get('weeks', 1)
            days = interval_config.get('days', 0)
            hours = interval_config.get('hours', 0)
            minutes = interval_config.get('minutes', 0)

            trigger = IntervalTrigger(
                weeks=weeks,
                days=days,
                hours=hours,
                minutes=minutes
            )

            self.scheduler.add_job(
                self.job_function,
                trigger,
                id='activity_report_job'
            )

            interval_str = []
            if weeks:
                interval_str.append(f"{weeks} week(s)")
            if days:
                interval_str.append(f"{days} day(s)")
            if hours:
                interval_str.append(f"{hours} hour(s)")
            if minutes:
                interval_str.append(f"{minutes} minute(s)")

            logger.info(f"Scheduled job: Every {', '.join(interval_str)}")

        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

    def start(self, run_now: bool = False):
        """
        Start the scheduler.

        Args:
            run_now: Run the job immediately before starting scheduler
        """
        logger.info("Starting report scheduler")

        # Set up schedule
        self.setup_schedule()

        # Run immediately if requested
        if run_now:
            logger.info("Running job immediately")
            self.job_function()

        # Start scheduler
        logger.info("Scheduler started. Press Ctrl+C to exit.")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")
            self.scheduler.shutdown()


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description='Activity Reporting Automation System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                    # Run once and exit
  python run.py --schedule         # Run with scheduler
  python run.py --schedule --now   # Run immediately then schedule
  python run.py --config custom.yaml  # Use custom config file
        """
    )

    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Run with scheduler (keeps running)'
    )

    parser.add_argument(
        '--now',
        action='store_true',
        help='Run immediately before starting scheduler (only with --schedule)'
    )

    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )

    args = parser.parse_args()

    # Set up logging
    log_file = Path('logs') / 'activity_reporter.log'
    log_file.parent.mkdir(exist_ok=True)

    global logger
    logger = setup_logger(__name__, str(log_file))

    # Load configuration
    config_path = Path(args.config)

    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        logger.error(
            "\nPlease create your configuration file:\n"
            f"  cp config/config.yaml.example {config_path}\n"
            "  # Edit the file with your settings\n"
        )
        sys.exit(1)

    try:
        config = ConfigLoader(str(config_path))

        if args.schedule:
            # Scheduled mode
            scheduler = ReportScheduler(config)
            scheduler.start(run_now=args.now)
        else:
            # One-time execution
            logger.info("Running in one-time execution mode")
            reporter = ActivityReporter(config)
            success = reporter.run()
            sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
