"""Mail adapter composition root: apply the footer exactly once."""

from __future__ import annotations

from app.config import Settings, settings
from app.domain.ports.mail import MailService


def append_footer(body: str, footer: str) -> str:
    """Keep transport adapters responsible for transport only."""
    return f"{body}\n---\n{footer}" if footer else body


class FooterMailService(MailService):
    def __init__(self, delegate: MailService, footer: str) -> None:
        self._delegate = delegate
        self._footer = footer

    def send(self, to: list[str], subject: str, body: str) -> None:
        self._delegate.send(to, subject, append_footer(body, self._footer))


def create_mail_service(config: Settings | None = None) -> MailService:
    """Select delivery transport based on runtime environment."""
    from app.adapters.mail.log import LogMailService
    from app.adapters.mail.mock import MockMailService
    from app.adapters.mail.smtp import SmtpMailService

    config = config or settings
    if config.app_env == "production":
        delegate: MailService = SmtpMailService(
            host=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_user,
            password=config.smtp_password,
            from_address=config.email_from_address,
            use_starttls=config.smtp_starttls,
            timeout=config.smtp_timeout_seconds,
        )
    elif config.app_env == "test":
        delegate = MockMailService()
    else:
        delegate = LogMailService()
    return FooterMailService(delegate, config.email_footer)
