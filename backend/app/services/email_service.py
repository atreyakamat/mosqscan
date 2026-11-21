"""Configurable email service for password reset and notifications."""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, List

from app.config import settings

logger = logging.getLogger(__name__)


class EmailProvider:
    """Base interface for email providers."""

    def send_password_reset_email(self, to_email: str, reset_link: str) -> bool:
        raise NotImplementedError


class ConsoleEmailProvider(EmailProvider):
    """
    Console/Local email provider for development and testing.
    Records dispatches without logging sensitive tokens to stdout.
    """

    def __init__(self) -> None:
        self.sent_messages: List[dict[str, Any]] = []

    def send_password_reset_email(self, to_email: str, reset_link: str) -> bool:
        # Note: In accordance with ASD-STE100 and security rules: do NOT log tokens.
        logger.info("Password reset email dispatched to %s (token redacted)", to_email)
        self.sent_messages.append(
            {
                "to": to_email,
                "reset_link": reset_link,
            }
        )
        return True

    def clear(self) -> None:
        self.sent_messages.clear()


class SMTPEmailProvider(EmailProvider):
    """SMTP email provider for staging and production."""

    def __init__(self) -> None:
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.tls = settings.SMTP_TLS
        self.from_email = settings.EMAIL_FROM

    def send_password_reset_email(self, to_email: str, reset_link: str) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Vectora AI — Password Reset Request"
            msg["From"] = self.from_email
            msg["To"] = to_email

            text_content = (
                "You requested a password reset for your Vectora AI account.\n\n"
                f"Please open this link within 15 minutes to reset your password:\n{reset_link}\n\n"
                "If you did not request this reset, you can safely ignore this email.\n"
            )
            msg.attach(MIMEText(text_content, "plain"))

            server = smtplib.SMTP(self.host, self.port, timeout=5.0)
            if self.tls:
                server.starttls()
            if self.user and self.password:
                server.login(self.user, self.password)
            server.sendmail(self.from_email, [to_email], msg.as_string())
            server.quit()
            logger.info("Password reset email sent via SMTP to %s (token redacted)", to_email)
            return True
        except Exception as exc:
            logger.error("Failed to send password reset email to %s: %s", to_email, exc)
            return False


_console_provider = ConsoleEmailProvider()


def get_email_provider() -> EmailProvider:
    """Return configured email provider instance."""
    provider_name = settings.EMAIL_PROVIDER.lower().strip()
    if provider_name == "smtp":
        return SMTPEmailProvider()
    return _console_provider
