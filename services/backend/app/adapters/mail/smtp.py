# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Synchronous SMTP adapter for Celery workers."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from app.domain.ports.mail import MailDeliveryError, MailService


class SmtpMailService(MailService):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        from_address: str,
        use_starttls: bool = True,
        timeout: float = 10.0,
    ) -> None:
        if not host or not from_address:
            raise ValueError("SMTP host and sender address must be configured")
        if bool(username) != bool(password):
            raise ValueError("SMTP username and password must be configured together")
        self._host, self._port = host, port
        self._username, self._password = username, password
        self._from_address = from_address
        self._use_starttls, self._timeout = use_starttls, timeout

    def send(self, to: list[str], subject: str, body: str) -> None:
        recipients = sorted(set(to))
        if not recipients:
            return
        if any("\n" in value or "\r" in value for value in [*recipients, subject]):
            raise MailDeliveryError("Invalid email header")
        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
                smtp.ehlo()
                if self._use_starttls:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if self._username and self._password:
                    smtp.login(self._username, self._password)
                # Individual envelope recipients prevent disclosure of membership addresses.
                for recipient in recipients:
                    message = EmailMessage()
                    message["From"] = self._from_address
                    message["To"] = recipient
                    message["Subject"] = subject
                    message.set_content(body)
                    smtp.send_message(message)
        except (smtplib.SMTPException, OSError, TimeoutError) as exc:
            raise MailDeliveryError("SMTP delivery failed") from exc
