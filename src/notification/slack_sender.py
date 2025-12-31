"""
Slack sender for the activity reporting system.

Sends messages and uploads files to Slack channels.
"""

import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class SlackSender:
    """
    Send messages and files to Slack.

    Supports:
    - Text messages to channels
    - File uploads with comments
    - Rich message formatting
    - Error notifications

    Example:
        >>> sender = SlackSender(config)
        >>> sender.send_report(
        ...     channel='#reports',
        ...     message='Weekly report generated',
        ...     files=['report.xlsx']
        ... )
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Slack sender with API configuration.

        Args:
            config: Slack configuration dictionary

        Required config keys:
            - bot_token: Slack bot/app OAuth token (starts with 'xoxb-')
            OR
            - webhook_url: Slack incoming webhook URL

        Optional config keys:
            - default_channel: Default channel to send to
        """
        self.config = config
        self._validate_config()

        self.bot_token = config.get('bot_token')
        self.webhook_url = config.get('webhook_url')
        self.default_channel = config.get('default_channel')

    def _validate_config(self) -> None:
        """Validate Slack configuration."""
        if 'bot_token' not in self.config and 'webhook_url' not in self.config:
            raise ValueError(
                "Slack configuration requires either 'bot_token' or 'webhook_url'"
            )

    def send_report(
        self,
        message: str,
        channel: Optional[str] = None,
        files: Optional[List[str]] = None,
        thread_ts: Optional[str] = None
    ) -> bool:
        """
        Send report notification to Slack.

        Args:
            message: Message text to send
            channel: Channel to send to (uses default if not specified)
            files: List of file paths to upload (optional)
            thread_ts: Thread timestamp for threaded replies (optional)

        Returns:
            True if message sent successfully
        """
        target_channel = channel or self.default_channel

        if not target_channel and not self.webhook_url:
            logger.error("No channel specified and no default channel configured")
            return False

        try:
            # Send message
            if self.webhook_url:
                success = self._send_webhook(message)
            else:
                success = self._send_message(message, target_channel, thread_ts)

            if not success:
                return False

            # Upload files if provided
            if files and self.bot_token:
                for file_path in files:
                    self._upload_file(file_path, target_channel, message)

            logger.info(f"Slack notification sent to {target_channel or 'webhook'}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False

    def _send_webhook(self, message: str) -> bool:
        """Send message via webhook URL."""
        payload = {
            'text': message,
            'mrkdwn': True
        }

        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            logger.info("Message sent via Slack webhook")
            return True
        else:
            logger.error(f"Webhook request failed: {response.status_code} - {response.text}")
            return False

    def _send_message(
        self,
        message: str,
        channel: str,
        thread_ts: Optional[str] = None
    ) -> bool:
        """Send message via Slack API."""
        url = 'https://slack.com/api/chat.postMessage'

        headers = {
            'Authorization': f'Bearer {self.bot_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'channel': channel,
            'text': message,
            'mrkdwn': True
        }

        if thread_ts:
            payload['thread_ts'] = thread_ts

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=10
        )

        result = response.json()

        if result.get('ok'):
            logger.info(f"Message sent to Slack channel: {channel}")
            return True
        else:
            error = result.get('error', 'Unknown error')
            logger.error(f"Slack API error: {error}")
            return False

    def _upload_file(
        self,
        file_path: str,
        channel: str,
        comment: Optional[str] = None
    ) -> bool:
        """Upload file to Slack channel."""
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"File not found for upload: {file_path}")
            return False

        url = 'https://slack.com/api/files.upload'

        headers = {
            'Authorization': f'Bearer {self.bot_token}'
        }

        data = {
            'channels': channel,
            'filename': path.name
        }

        if comment:
            data['initial_comment'] = comment

        with open(path, 'rb') as f:
            files = {'file': f}

            response = requests.post(
                url,
                headers=headers,
                data=data,
                files=files,
                timeout=30
            )

        result = response.json()

        if result.get('ok'):
            logger.info(f"File uploaded to Slack: {path.name}")
            return True
        else:
            error = result.get('error', 'Unknown error')
            logger.error(f"File upload failed: {error}")
            return False

    def send_error_notification(
        self,
        error_message: str,
        channel: Optional[str] = None,
        error_details: Optional[str] = None
    ) -> bool:
        """
        Send error notification to Slack.

        Args:
            error_message: Brief error description
            channel: Channel to send to (uses default if not specified)
            error_details: Detailed error information (optional)

        Returns:
            True if notification sent successfully
        """
        target_channel = channel or self.default_channel

        message = f"""
:warning: *Activity Report Generation Failed*

{error_message}
"""

        if error_details:
            message += f"\n```\n{error_details}\n```"

        return self.send_report(
            message=message,
            channel=target_channel
        )

    def send_success_notification(
        self,
        channel: Optional[str] = None,
        summary: Optional[str] = None,
        files: Optional[List[str]] = None
    ) -> bool:
        """
        Send success notification with optional summary.

        Args:
            channel: Channel to send to (uses default if not specified)
            summary: Summary text to include
            files: Report files to upload

        Returns:
            True if notification sent successfully
        """
        target_channel = channel or self.default_channel

        message = ":white_check_mark: *Weekly Activity Report Generated*\n\n"

        if summary:
            message += summary

        return self.send_report(
            message=message,
            channel=target_channel,
            files=files
        )
