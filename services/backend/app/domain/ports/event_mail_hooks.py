"""Ports for event-driven mail hooks."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.events import EventType
from app.domain.models.event_mail_hook import EventMailHook
from app.domain.models.role import Role


class EventMailHookRepository(ABC):
    @abstractmethod
    async def get(self, district_id: uuid.UUID, hook_id: uuid.UUID) -> EventMailHook | None:
        """Return the hook only when it belongs to the district."""

    @abstractmethod
    async def list_by_district(self, district_id: uuid.UUID) -> list[EventMailHook]:
        """All hooks of a district, active and inactive."""

    @abstractmethod
    async def list_active(
        self, district_id: uuid.UUID, event_type: EventType
    ) -> list[EventMailHook]:
        """Active hooks matching an emitted event."""

    @abstractmethod
    async def save(self, hook: EventMailHook) -> None:
        """Insert or update."""


class RecipientDirectory(ABC):
    @abstractmethod
    async def emails_for_role(self, district_id: uuid.UUID, role: Role) -> list[str]:
        """Distinct e-mail addresses of district-scoped members holding exactly ``role``."""

    @abstractmethod
    async def district_name(self, district_id: uuid.UUID) -> str | None:
        """Display name of the district, ``None`` when it no longer exists."""
