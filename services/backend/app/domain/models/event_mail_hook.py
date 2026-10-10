# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Domain model and safe template contract for event-driven emails."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from string import Formatter
from uuid import UUID, uuid4

from app.domain.events import EventType
from app.domain.models.role import Role

EVENT_PLACEHOLDERS: dict[EventType, frozenset[str]] = {
    EventType.SLOT_UNASSIGNED: frozenset(
        {"district_name", "congregation_name", "date", "event_title"}
    ),
    EventType.EXTERNAL_EVENT_DETECTED: frozenset(
        {"district_name", "event_title", "event_date", "source"}
    ),
    EventType.SYNC_ERROR: frozenset(
        {"district_name", "integration_name", "error_message", "timestamp"}
    ),
    EventType.REGISTRATION_RECEIVED: frozenset(
        {"district_name", "leader_name", "leader_email"}
    ),
    EventType.ASSIGNMENT_CONFIRMED: frozenset(
        {"district_name", "leader_name", "event_title", "event_date"}
    ),
    EventType.PLAN_FINALIZED: frozenset({"district_name", "month", "year"}),
}


def validate_template(event_type: EventType, template: str) -> None:
    """Accept named fields only, never indexing, attributes, or format modifiers."""
    try:
        for _, name, format_spec, conversion in Formatter().parse(template):
            if name is not None and (
                name not in EVENT_PLACEHOLDERS[event_type] or format_spec or conversion
            ):
                raise ValueError(f"Unsupported event placeholder: {name!r}")
    except ValueError as exc:
        raise ValueError(f"Invalid {event_type} template: {exc}") from exc


@dataclass(frozen=True, slots=True)
class EventMailHook:
    district_id: UUID
    event_type: EventType
    recipient_role: Role
    subject_template: str
    body_template: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Normalise enums and reject unknown roles or unsafe templates."""
        # Accept plain strings from adapters but store the canonical enum.
        try:
            role = Role(self.recipient_role)
        except ValueError as exc:
            raise ValueError(f"Unknown recipient_role: {self.recipient_role!r}") from exc
        object.__setattr__(self, "recipient_role", role)
        object.__setattr__(self, "event_type", EventType(self.event_type))
        validate_template(self.event_type, self.subject_template)
        validate_template(self.event_type, self.body_template)

    def update(
        self,
        *,
        recipient_role: Role | str | None = None,
        subject_template: str | None = None,
        body_template: str | None = None,
        is_active: bool | None = None,
    ) -> EventMailHook:
        return replace(
            self,
            recipient_role=self.recipient_role if recipient_role is None else recipient_role,
            subject_template=(
                self.subject_template if subject_template is None else subject_template
            ),
            body_template=self.body_template if body_template is None else body_template,
            is_active=self.is_active if is_active is None else is_active,
            updated_at=datetime.now(UTC),
        )
