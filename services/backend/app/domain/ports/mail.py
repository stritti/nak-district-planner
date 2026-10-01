"""Transport-agnostic outbound email contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class MailDeliveryError(Exception):
    """Outbound delivery failed; callers decide whether and when to retry."""


@dataclass(frozen=True)
class MailRecord:
    to: tuple[str, ...]
    subject: str
    body: str
    sent_at: datetime


class MailService(ABC):
    @abstractmethod
    def send(self, to: list[str], subject: str, body: str) -> None:
        """Deliver one message to the specified recipients or raise MailDeliveryError."""
        raise NotImplementedError
