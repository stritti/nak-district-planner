"""HookEvaluator (EventMailHookDispatcher), serialisation and bus wiring."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application import event_mail_hooks
from app.application.event_mail_hooks import (
    EventMailHookDispatcher,
    deserialize_event,
    enqueue_event_mail_dispatch,
    register_event_mail_hooks,
    serialize_event,
)
from app.domain.events import DomainEvent, DomainEventBus, EventType
from app.domain.models.event_mail_hook import EventMailHook
from app.domain.models.role import Role
from app.domain.ports.mail import MailDeliveryError

DISTRICT = uuid.uuid4()


class FakeHooks:
    def __init__(self, *hooks: EventMailHook) -> None:
        self.hooks = list(hooks)

    async def list_active(self, district_id, event_type):
        return [
            h
            for h in self.hooks
            if h.district_id == district_id and h.event_type == event_type and h.is_active
        ]


class FakeDirectory:
    def __init__(self, emails: dict[Role, list[str]], district_name: str | None = "Bezirk Süd"):
        self.emails = emails
        self.name = district_name

    async def emails_for_role(self, district_id, role):
        return self.emails.get(role, [])

    async def district_name(self, district_id):
        return self.name


class RecordingMail:
    def __init__(self, fail_for: set[str] = frozenset()) -> None:
        self.sent: list[tuple[list[str], str, str]] = []
        self.fail_for = fail_for

    def send(self, to, subject, body) -> None:
        if set(to) & self.fail_for:
            raise MailDeliveryError("smtp down")
        self.sent.append((to, subject, body))


def _hook(**overrides) -> EventMailHook:
    values = {
        "district_id": DISTRICT,
        "event_type": EventType.REGISTRATION_RECEIVED,
        "recipient_role": Role.DISTRICT_ADMIN,
        "subject_template": "Neue Registrierung: {leader_name}",
        "body_template": "{leader_name} <{leader_email}> in {district_name}",
    }
    values.update(overrides)
    return EventMailHook(**values)


def _event(**payload) -> DomainEvent:
    return DomainEvent(
        EventType.REGISTRATION_RECEIVED,
        DISTRICT,
        {"leader_name": "Anna Beispiel", "leader_email": "anna@example.org", **payload},
    )


def _dispatcher(hooks, directory=None, mail=None):
    directory = directory or FakeDirectory({Role.DISTRICT_ADMIN: ["a@x.org", "b@x.org"]})
    mail = mail or RecordingMail()
    return EventMailHookDispatcher(hooks, directory, mail), mail


class TestDispatch:
    async def test_sends_rendered_mail_to_each_recipient_individually(self) -> None:
        dispatcher, mail = _dispatcher(FakeHooks(_hook()))

        summary = await dispatcher.dispatch(_event())

        assert summary.hooks == 1 and summary.sent == 2 and summary.failed == 0
        assert [to for to, _, _ in mail.sent] == [["a@x.org"], ["b@x.org"]]
        _, subject, body = mail.sent[0]
        assert subject == "Neue Registrierung: Anna Beispiel"
        assert body == "Anna Beispiel <anna@example.org> in Bezirk Süd"

    async def test_district_name_comes_from_directory_not_from_payload(self) -> None:
        dispatcher, mail = _dispatcher(FakeHooks(_hook()))
        await dispatcher.dispatch(_event(district_name="Gefälscht"))
        assert mail.sent[0][2].endswith("in Bezirk Süd")

    async def test_payload_cannot_inject_header_lines_into_subject(self) -> None:
        dispatcher, mail = _dispatcher(FakeHooks(_hook()))
        await dispatcher.dispatch(_event(leader_name="Eve\r\nBcc: victim@example.org"))
        subject = mail.sent[0][1]
        assert "\n" not in subject and "\r" not in subject
        assert subject == "Neue Registrierung: Eve Bcc: victim@example.org"

    @pytest.mark.parametrize(
        "hook",
        [
            _hook(is_active=False),
            _hook(event_type=EventType.SYNC_ERROR, subject_template="x", body_template="y"),
            _hook(district_id=uuid.uuid4()),
        ],
        ids=["inactive", "other-event-type", "other-district"],
    )
    async def test_non_matching_hooks_are_ignored(self, hook) -> None:
        dispatcher, mail = _dispatcher(FakeHooks(hook))
        summary = await dispatcher.dispatch(_event())
        assert summary.hooks == 0
        assert mail.sent == []

    async def test_missing_district_skips_without_sending(self) -> None:
        directory = FakeDirectory({Role.DISTRICT_ADMIN: ["a@x.org"]}, district_name=None)
        dispatcher, mail = _dispatcher(FakeHooks(_hook()), directory)
        summary = await dispatcher.dispatch(_event())
        assert summary.skipped == 1 and mail.sent == []

    async def test_hook_without_recipients_is_skipped(self) -> None:
        dispatcher, _ = _dispatcher(
            FakeHooks(_hook(recipient_role=Role.PLANNER), _hook()),
        )
        summary = await dispatcher.dispatch(_event())
        assert summary.skipped == 1 and summary.sent == 2

    async def test_failed_delivery_is_counted_and_others_continue(self) -> None:
        mail = RecordingMail(fail_for={"a@x.org"})
        dispatcher, _ = _dispatcher(FakeHooks(_hook()), mail=mail)
        summary = await dispatcher.dispatch(_event())
        assert summary.failed == 1 and summary.sent == 1
        assert mail.sent[0][0] == ["b@x.org"]

    async def test_dispatch_never_emits_domain_events(self) -> None:
        dispatcher, _ = _dispatcher(FakeHooks(_hook()))
        with patch.object(DomainEventBus, "emit") as emit:
            await dispatcher.dispatch(_event())
        emit.assert_not_called()


class TestSerialisation:
    def test_roundtrip_stringifies_payload_and_keeps_none(self) -> None:
        occurred = datetime(2026, 9, 30, 12, tzinfo=UTC)
        event = DomainEvent(
            EventType.PLAN_FINALIZED, DISTRICT, {"year": 2026, "month": None}, occurred
        )

        restored = deserialize_event(serialize_event(event))

        assert restored == DomainEvent(
            EventType.PLAN_FINALIZED, DISTRICT, {"year": "2026", "month": None}, occurred
        )


class TestWiring:
    def test_register_subscribes_all_event_types_once(self) -> None:
        bus = DomainEventBus()
        register_event_mail_hooks(bus)
        register_event_mail_hooks(bus)
        for event_type in EventType:
            assert bus._handlers[event_type] == [enqueue_event_mail_dispatch]

    def test_enqueue_passes_serialised_event_to_celery(self) -> None:
        event = _event()
        task = MagicMock()
        with patch("app.application.event_mail_hook_tasks.dispatch_event_mail_hooks", task):
            enqueue_event_mail_dispatch(event)
        task.delay.assert_called_once_with(serialize_event(event))

    def test_unavailable_broker_is_logged_not_raised(self, caplog) -> None:
        task = MagicMock()
        task.delay.side_effect = ConnectionError("broker down")
        with patch("app.application.event_mail_hook_tasks.dispatch_event_mail_hooks", task):
            enqueue_event_mail_dispatch(_event())
        assert "could not be queued" in caplog.text


class TestCeleryTask:
    def test_task_dispatches_deserialised_event_with_sql_adapters(self) -> None:
        from app.application.event_mail_hook_tasks import dispatch_event_mail_hooks

        session = MagicMock()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=session)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)
        dispatch = AsyncMock(return_value=event_mail_hooks.DispatchSummary(hooks=1, sent=2))
        event = _event()

        with (
            patch("app.adapters.db.session.AsyncSessionLocal", factory),
            patch("app.adapters.mail.create_mail_service", return_value=RecordingMail()),
            patch.object(EventMailHookDispatcher, "dispatch", dispatch),
        ):
            result = dispatch_event_mail_hooks.run(serialize_event(event))

        assert result == {"hooks": 1, "sent": 2, "skipped": 0, "failed": 0}
        assert dispatch.await_args.args[0].payload == event.payload
