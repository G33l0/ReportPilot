"""
Main orchestration module for the activity reporting system.

Coordinates data ingestion, cleaning, summarization, and report generation.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import traceback

from .utils.config_loader import ConfigLoader
from .utils.logger import setup_logger
from .ingestion import CSVReader, ExcelReader, APIReader, FolderReader
from .cleaning import DataCleaner
from .aggregation import DataSummarizer
from .reporting import ExcelReportGenerator, PDFReportGenerator
from .notification import EmailSender, SlackSender

logger = setup_logger(__name__)


class ActivityReporter:
    """
    Main orchestration class for activity reporting.

    Coordinates the entire reporting pipeline:
    1. Data ingestion from multiple sources
    2. Data cleaning and validation
    3. Weekly summarization and analysis
    4. Report generation (Excel and PDF)
    5. Delivery via email and Slack

    Example:
        >>> config = ConfigLoader('config/config.yaml')
        >>> reporter = ActivityReporter(config)
        >>> reporter.run()
    """

    def __init__(self, config: ConfigLoader):
        """
        Initialize the activity reporter.

        Args:
            config: ConfigLoader instance with system configuration
        """
        self.config = config
        self.cleaner = DataCleaner()
        self.summarizer = DataSummarizer()
        self.excel_generator = ExcelReportGenerator()
        self.pdf_generator = PDFReportGenerator()

        # Initialize notifiers if configured
        self.email_sender = None
        self.slack_sender = None

        if self.config.get('email.enabled', False):
            try:
                email_config = {
                    'smtp_host': self.config.get_env('REPORTPILOT_SMTP_HOST'),
                    'smtp_port': self.config.get_env('REPORTPILOT_SMTP_PORT'),
                    'from_email': self.config.get_env('REPORTPILOT_FROM_EMAIL'),
                    'password': self.config.get_env('REPORTPILOT_EMAIL_PASSWORD'),
                    'use_tls': self.config.get('email.use_tls', True)
                }
                self.email_sender = EmailSender(email_config)
                logger.info("Email sender initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize email sender: {str(e)}")

        if self.config.get('slack.enabled', False):
            try:
                slack_config = {
                    'bot_token': self.config.get_env('REPORTPILOT_SLACK_BOT_TOKEN'),
                    'webhook_url': self.config.get_env('REPORTPILOT_SLACK_WEBHOOK_URL'),
                    'default_channel': self.config.get('slack.default_channel')
                }
                self.slack_sender = SlackSender(slack_config)
                logger.info("Slack sender initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Slack sender: {str(e)}")

    def run(self) -> bool:
        """
        Execute the complete reporting pipeline.

        Returns:
            True if reporting completed successfully, False otherwise
        """
        logger.info("=" * 60)
        logger.info("Starting activity report generation")
        logger.info("=" * 60)

        try:
            # 1. Ingest data
            logger.info("Step 1: Data ingestion")
            combined_df = self._ingest_data()

            if combined_df is None or combined_df.empty:
                raise ValueError("No data ingested from sources")

            logger.info(f"Total rows ingested: {len(combined_df)}")

            # 2. Clean data
            logger.info("Step 2: Data cleaning")
            cleaned_df = self._clean_data(combined_df)

            logger.info(f"Rows after cleaning: {len(cleaned_df)}")

            # 3. Summarize data
            logger.info("Step 3: Data summarization")
            summaries = self._summarize_data(cleaned_df)

            logger.info(f"Generated {len(summaries)} summary reports")

            # 4. Generate reports
            logger.info("Step 4: Report generation")
            report_files = self._generate_reports(summaries)

            logger.info(f"Generated {len(report_files)} report files")

            # 5. Deliver reports
            logger.info("Step 5: Report delivery")
            self._deliver_reports(report_files, summaries)

            logger.info("=" * 60)
            logger.info("Activity report generation completed successfully")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            logger.error(traceback.format_exc())

            # Send error notifications
            self._send_error_notifications(str(e), traceback.format_exc())

            return False

    def _ingest_data(self):
        """Ingest data from all configured sources."""
        data_sources = self.config.get('data_sources', [])

        if not data_sources:
            raise ValueError("No data sources configured")

        dataframes = []

        for source_config in data_sources:
            source_type = source_config.get('type')
            enabled = source_config.get('enabled', True)

            if not enabled:
                logger.info(f"Skipping disabled source: {source_type}")
                continue

            try:
                # Create appropriate reader
                if source_type == 'csv':
                    reader = CSVReader(source_config)
                elif source_type == 'excel':
                    reader = ExcelReader(source_config)
                elif source_type == 'api':
                    reader = APIReader(source_config)
                elif source_type == 'folder':
                    reader = FolderReader(source_config)
                else:
                    logger.warning(f"Unknown source type: {source_type}")
                    continue

                # Read data
                df = reader.read()
                dataframes.append(df)

                logger.info(
                    f"Loaded {len(df)} rows from {source_type} source"
                )

            except Exception as e:
                logger.error(f"Failed to read from {source_type} source: {str(e)}")

                # Check if source is required
                if source_config.get('required', False):
                    raise

        if not dataframes:
            return None

        # Combine all dataframes
        import pandas as pd
        combined_df = pd.concat(dataframes, ignore_index=True)

        return combined_df

    def _clean_data(self, df):
        """Clean and validate data."""
        cleaning_config = self.config.get('cleaning', {})
        cleaned_df = self.cleaner.clean(df, cleaning_config)

        # Log cleaning statistics
        stats = self.cleaner.get_cleaning_stats()
        logger.info(f"Cleaning stats: {stats}")

        return cleaned_df

    def _summarize_data(self, df):
        """Generate weekly summaries."""
        summary_config = self.config.get('summarization', {})
        summaries = self.summarizer.summarize_weekly(df, summary_config)

        return summaries

    def _generate_reports(self, summaries) -> List[str]:
        """Generate Excel and PDF reports."""
        output_dir = Path(self.config.get('output.directory', 'data/output'))
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_files = []

        report_config = self.config.get('reports', {})

        # Generate Excel report
        if self.config.get('reports.excel.enabled', True):
            excel_path = output_dir / f"activity_report_{timestamp}.xlsx"
            self.excel_generator.generate(
                summaries,
                str(excel_path),
                report_config.get('excel', {})
            )
            report_files.append(str(excel_path))
            logger.info(f"Excel report: {excel_path}")

        # Generate PDF report
        if self.config.get('reports.pdf.enabled', True):
            pdf_path = output_dir / f"activity_report_{timestamp}.pdf"
            self.pdf_generator.generate(
                summaries,
                str(pdf_path),
                report_config.get('pdf', {})
            )
            report_files.append(str(pdf_path))
            logger.info(f"PDF report: {pdf_path}")

        return report_files

    def _deliver_reports(self, report_files: List[str], summaries: Dict):
        """Deliver reports via email and Slack."""
        # Generate summary text
        summary_text = self.summarizer.export_summary_text(summaries)

        # Email delivery
        if self.email_sender and self.config.get('email.enabled', False):
            try:
                recipients = self.config.get('email.recipients', [])
                if recipients:
                    subject = self.config.get(
                        'email.subject',
                        f"Weekly Activity Report - {datetime.now().strftime('%Y-%m-%d')}"
                    )

                    self.email_sender.send_report(
                        to=recipients,
                        subject=subject,
                        body=summary_text,
                        attachments=report_files
                    )
                    logger.info(f"Reports emailed to {len(recipients)} recipients")
            except Exception as e:
                logger.error(f"Email delivery failed: {str(e)}")

        # Slack delivery
        if self.slack_sender and self.config.get('slack.enabled', False):
            try:
                channel = self.config.get('slack.channel')
                self.slack_sender.send_success_notification(
                    channel=channel,
                    summary=summary_text,
                    files=report_files if self.slack_sender.bot_token else None
                )
                logger.info("Reports delivered to Slack")
            except Exception as e:
                logger.error(f"Slack delivery failed: {str(e)}")

    def _send_error_notifications(self, error_message: str, error_details: str):
        """Send error notifications via configured channels."""
        # Email notification
        if self.email_sender and self.config.get('email.enabled', False):
            try:
                recipients = self.config.get('email.recipients', [])
                if recipients:
                    self.email_sender.send_error_notification(
                        to=recipients,
                        error_message=error_message,
                        error_details=error_details
                    )
            except Exception as e:
                logger.error(f"Failed to send email error notification: {str(e)}")

        # Slack notification
        if self.slack_sender and self.config.get('slack.enabled', False):
            try:
                channel = self.config.get('slack.channel')
                self.slack_sender.send_error_notification(
                    error_message=error_message,
                    channel=channel,
                    error_details=error_details[:500]  # Limit details length
                )
            except Exception as e:
                logger.error(f"Failed to send Slack error notification: {str(e)}")


def main():
    """Main entry point for the reporting system."""
    # Set up logging
    log_file = Path('logs') / 'activity_reporter.log'
    log_file.parent.mkdir(exist_ok=True)

    global logger
    logger = setup_logger(__name__, str(log_file))

    try:
        # Load configuration
        config_path = Path('config') / 'config.yaml'

        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            logger.error("Please create config.yaml from config.yaml.example")
            sys.exit(1)

        config = ConfigLoader(str(config_path))

        # Create and run reporter
        reporter = ActivityReporter(config)
        success = reporter.run()

        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
