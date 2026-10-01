"""Capturing transport for isolated tests."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.ports.mail import MailRecord, MailService


class MockMailService(MailService):
    def __init__(self) -> None:
        self.sent: list[MailRecord] = []

    def send(self, to: list[str], subject: str, body: str) -> None:
        self.sent.append(MailRecord(tuple(to), subject, body, datetime.now(UTC)))

    def clear(self) -> None:
        self.sent.clear()
