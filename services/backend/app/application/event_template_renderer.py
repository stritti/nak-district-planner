"""Render restricted event-specific notification templates."""

from __future__ import annotations

from collections.abc import Mapping
from string import Formatter
from typing import Any

from app.domain.events import EventType
from app.domain.models.event_mail_hook import validate_template


class _MissingAsBlank(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return ""


def render_event_template(
    event_type: EventType, template: str, payload: Mapping[str, Any]
) -> str:
    """Reject unsupported expressions and substitute absent fields with blanks."""
    validate_template(event_type, template)
    values = _MissingAsBlank(
        {key: "" if value is None else str(value) for key, value in payload.items()}
    )
    return Formatter().vformat(template, (), values)
