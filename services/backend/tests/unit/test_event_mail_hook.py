"""Validate hook configuration and all supported event template contracts."""

from uuid import uuid4

import pytest

from app.application.event_template_renderer import render_event_template
from app.domain.events import EventType
from app.domain.models.event_mail_hook import EVENT_PLACEHOLDERS, EventMailHook


@pytest.mark.parametrize("event_type", list(EventType))
def test_all_valid_placeholders_render(event_type: EventType) -> None:
    payload = {field: f"value_{field}" for field in EVENT_PLACEHOLDERS[event_type]}
    template = ", ".join("{" + field + "}" for field in sorted(payload))
    assert render_event_template(event_type, template, payload) == ", ".join(
        payload[field] for field in sorted(payload)
    )


def test_missing_placeholder_becomes_empty_string() -> None:
    assert render_event_template(EventType.SYNC_ERROR, "Failure: {error_message}", {}) == (
        "Failure: "
    )


def test_none_payload_value_becomes_empty_string() -> None:
    assert render_event_template(
        EventType.SYNC_ERROR, "{error_message}", {"error_message": None}
    ) == ""


@pytest.mark.parametrize(
    "template",
    [
        "{other}",
        "{district_name.__class__}",
        "{district_name[0]}",
        "{district_name!r}",
        "{district_name:>10}",
        "{district_name",
        "{}",
    ],
)
def test_unsafe_and_unknown_placeholders_rejected(template: str) -> None:
    with pytest.raises(ValueError, match="Invalid|Unsupported"):
        render_event_template(EventType.SYNC_ERROR, template, {})


def test_hook_validated_at_creation_and_update() -> None:
    hook = EventMailHook(
        district_id=uuid4(),
        event_type=EventType.SYNC_ERROR,
        recipient_role="PLANNER",
        subject_template="{integration_name}",
        body_template="{error_message}",
    )
    assert hook.is_active
    disabled = hook.update(is_active=False)
    assert disabled.id == hook.id
    assert disabled.updated_at >= hook.updated_at
    assert not disabled.is_active
    assert hook.is_active
    with pytest.raises(ValueError, match="Invalid"):
        hook.update(body_template="{leader_name}")


def test_blank_role_rejected() -> None:
    with pytest.raises(ValueError, match="recipient_role"):
        EventMailHook(
            district_id=uuid4(),
            event_type=EventType.SYNC_ERROR,
            recipient_role=" ",
            subject_template="Test",
            body_template="Body",
        )
