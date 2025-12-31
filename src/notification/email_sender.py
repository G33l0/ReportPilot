"""
Email sender for the activity reporting system.

Sends reports via SMTP with attachment support.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import List, Optional, Dict, Any
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class EmailSender:
    """
    Send reports via email using SMTP.

    Supports:
    - Multiple recipients
    - HTML and plain text content
    - File attachments
    - TLS/SSL encryption

    Example:
        >>> sender = EmailSender(config)
        >>> sender.send_report(
        ...     to=['user@example.com'],
        ...     subject='Weekly Report',
        ...     body='Report attached',
        ...     attachments=['report.xlsx']
        ... )
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize email sender with SMTP configuration.

        Args:
            config: Email configuration dictionary

        Required config keys:
            - smtp_host: SMTP server hostname
            - smtp_port: SMTP server port
            - from_email: Sender email address
            - username: SMTP username (optional if same as from_email)
            - password: SMTP password

        Optional config keys:
            - use_tls: Use TLS encryption (default: True)
            - use_ssl: Use SSL encryption (default: False)
        """
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate email configuration."""
        required_keys = ['smtp_host', 'smtp_port', 'from_email', 'password']
        missing_keys = [key for key in required_keys if key not in self.config]

        if missing_keys:
            raise ValueError(f"Missing required email configuration: {missing_keys}")

    def send_report(
        self,
        to: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html: bool = False
    ) -> bool:
        """
        Send email with optional attachments.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Email body content
            attachments: List of file paths to attach (optional)
            cc: List of CC recipients (optional)
            bcc: List of BCC recipients (optional)
            html: Whether body is HTML (default: False)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config['from_email']
            msg['To'] = ', '.join(to)
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Add body
            body_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, body_type))

            # Add attachments
            if attachments:
                for file_path in attachments:
                    self._attach_file(msg, file_path)

            # Combine all recipients
            all_recipients = to.copy()
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)

            # Send email
            self._send_smtp(msg, all_recipients)

            logger.info(f"Email sent successfully to {len(all_recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    def _attach_file(self, msg: MIMEMultipart, file_path: str) -> None:
        """Attach a file to the email message."""
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"Attachment file not found: {file_path}")
            return

        with open(path, 'rb') as f:
            attachment = MIMEApplication(f.read(), Name=path.name)
            attachment['Content-Disposition'] = f'attachment; filename="{path.name}"'
            msg.attach(attachment)

        logger.info(f"Attached file: {path.name}")

    def _send_smtp(self, msg: MIMEMultipart, recipients: List[str]) -> None:
        """Send email via SMTP."""
        smtp_host = self.config['smtp_host']
        smtp_port = int(self.config['smtp_port'])
        username = self.config.get('username', self.config['from_email'])
        password = self.config['password']
        use_tls = self.config.get('use_tls', True)
        use_ssl = self.config.get('use_ssl', False)

        # Create SMTP connection
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)

        try:
            if use_tls and not use_ssl:
                server.starttls()

            # Login
            server.login(username, password)

            # Send email
            server.send_message(msg)

            logger.info(f"Email sent via SMTP: {smtp_host}:{smtp_port}")

        finally:
            server.quit()

    def send_error_notification(
        self,
        to: List[str],
        error_message: str,
        error_details: Optional[str] = None
    ) -> bool:
        """
        Send error notification email.

        Args:
            to: List of recipient email addresses
            error_message: Brief error description
            error_details: Detailed error information (optional)

        Returns:
            True if notification sent successfully
        """
        subject = "⚠️ Activity Report Generation Failed"

        body = f"""
Activity Report Generation Error

An error occurred while generating the activity report:

{error_message}
"""

        if error_details:
            body += f"\n\nDetails:\n{error_details}"

        body += "\n\nPlease check the logs for more information."

        return self.send_report(
            to=to,
            subject=subject,
            body=body
        )
