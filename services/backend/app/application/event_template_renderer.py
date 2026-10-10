# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Render restricted event-specific notification templates."""

from __future__ import annotations

from collections.abc import Mapping
from string import Formatter
from typing import Any

from app.domain.events import EventType
from app.domain.models.event_mail_hook import EVENT_PLACEHOLDERS, validate_template


class _MissingAsBlank(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return ""


def render_event_template(
    event_type: EventType, template: str, payload: Mapping[str, Any]
) -> str:
    """Reject unsupported expressions and substitute absent fields with blanks."""
    validate_template(event_type, template)
    values = _MissingAsBlank(
        {
            key: "" if payload.get(key) is None else str(payload[key])
            for key in EVENT_PLACEHOLDERS[event_type]
            if key in payload
        }
    )
    return Formatter().vformat(template, (), values)
