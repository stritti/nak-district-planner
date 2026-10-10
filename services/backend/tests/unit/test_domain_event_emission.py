# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Emission points: services publish domain events for committed changes only."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.api.routers import events as events_router
from app.adapters.api.routers import registrations as registrations_router
from app.adapters.api.routers import service_assignments as assignments_router
from app.adapters.api.schemas.registration import RegistrationApprove
from app.adapters.api.schemas.service_assignment import ServiceAssignmentUpdate
from app.application import external_candidate_ingestion as ingestion
from app.domain.events import EventType
from app.domain.models.calendar_integration import CalendarIntegration, CalendarType
from app.domain.models.congregation import Congregation
from app.domain.models.leader_registration import LeaderRegistration
from app.domain.models.membership import ScopeType
from app.domain.models.planning_slot import EventApprovalStatus, PlanningSlot
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.models.role import Role
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment

DISTRICT = uuid.uuid4()


def _published(publish) -> list:
    return [call.args[1] for call in publish.call_args_list]


# ── EXTERNAL_EVENT_DETECTED ──────────────────────────────────────────────────


class TestCandidateIngestion:
    START = datetime(2026, 7, 1, 10, tzinfo=UTC)
    INTEGRATION = CalendarIntegration.create(
        district_id=DISTRICT, name="Gemeindekalender", type=CalendarType.ICS, credentials_enc="x"
    )

    def _raw(self) -> RawCalendarEvent:
        return RawCalendarEvent(
            uid="ext",
            title="Konzert",
            start_at=self.START,
            end_at=self.START + timedelta(hours=1),
            description=None,
            content_hash="h",
            is_cancelled=False,
        )

    async def _ingest(self, existing_candidate=None):
        candidates = AsyncMock()
        candidates.by_external_event.return_value = existing_candidate
        session = object()
        with (
            patch.object(ingestion, "find_exact_matching_slot", return_value=None),
            patch.object(ingestion, "publish_after_commit") as publish,
        ):
            await ingestion.ingest_unlinked_event(
                raw=self._raw(),
                integration=self.INTEGRATION,
                session=session,
                candidate_repo=candidates,
                instance_repo=AsyncMock(),
                link_repo=AsyncMock(),
                notification_repo=AsyncMock(),
                content_hash="h",
            )
        return publish, session

    async def test_new_candidate_publishes_event(self) -> None:
        publish, session = await self._ingest()

        (event,) = _published(publish)
        assert publish.call_args.args[0] is session
        assert event.event_type == EventType.EXTERNAL_EVENT_DETECTED
        assert event.district_id == DISTRICT
        assert event.payload == {
            "event_title": "Konzert",
            "event_date": "2026-07-01",
            "source": "Gemeindekalender",
        }

    async def test_refreshing_existing_candidate_publishes_nothing(self) -> None:
        existing = ingestion.ExternalEventCandidate.create(
            integration=self.INTEGRATION, raw=self._raw(), content_hash="old"
        )
        publish, _ = await self._ingest(existing_candidate=existing)
        publish.assert_not_called()


# ── PLAN_FINALIZED ───────────────────────────────────────────────────────────


def _auth(superadmin: bool = False):
    return SimpleNamespace(
        user=SimpleNamespace(is_superadmin=superadmin), memberships=[], user_sub="u"
    )


async def _bulk(body, *, district_id=DISTRICT, slots=None):
    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = (
        [
            PlanningSlot.create(
                district_id=DISTRICT, planning_date=date(2026, 3, 1), planning_time=time(10)
            )
        ]
        if slots is None
        else slots
    )
    session = object()
    with (
        patch.object(events_router, "require_role_in_district"),
        patch.object(events_router, "publish_after_commit") as publish,
    ):
        await events_router.bulk_update_approval_status(
            body, _auth(superadmin=True), session, district_id, slot_repo
        )
    return publish


class TestPlanFinalized:
    def _body(self, **overrides):
        values = {"year": 2026, "month": 3, "approval_status": EventApprovalStatus.CONFIRMED}
        return events_router.BulkApprovalStatusRequest(**{**values, **overrides})

    async def test_confirming_district_month_publishes_event(self) -> None:
        publish = await _bulk(self._body())
        (event,) = _published(publish)
        assert event.event_type == EventType.PLAN_FINALIZED
        assert event.payload == {"month": "März", "year": "2026"}

    @pytest.mark.parametrize(
        ("overrides", "kwargs"),
        [
            ({"approval_status": EventApprovalStatus.PLANNED}, {}),
            ({"congregation_id": uuid.uuid4()}, {}),
            ({}, {"slots": []}),
            ({}, {"district_id": None}),
        ],
        ids=["back-to-planned", "single-congregation", "empty-month", "cross-district-superadmin"],
    )
    async def test_other_bulk_updates_publish_nothing(self, overrides, kwargs) -> None:
        publish = await _bulk(self._body(**overrides), **kwargs)
        publish.assert_not_called()


# ── ASSIGNMENT_CONFIRMED ─────────────────────────────────────────────────────


async def _update_assignment(assignment: ServiceAssignment, body, leader_name: str = "Pr. Leader"):
    slot = PlanningSlot.create(
        district_id=DISTRICT,
        planning_date=date(2026, 12, 24),
        planning_time=time(18),
        title="Christvesper",
    )
    assignment_repo = AsyncMock()
    assignment_repo.get.return_value = assignment
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    leader_repo = AsyncMock()
    leader_repo.get.return_value = SimpleNamespace(name=leader_name)
    with (
        patch.object(assignments_router, "require_role_in_district"),
        patch.object(assignments_router, "publish_after_commit") as publish,
    ):
        await assignments_router.update_assignment(
            assignment.event_id,
            assignment.id,
            body,
            _auth(),
            object(),
            slot_repo,
            assignment_repo,
            leader_repo,
        )
    return publish


class TestAssignmentConfirmed:
    def _assignment(self, **kwargs) -> ServiceAssignment:
        return ServiceAssignment.create(event_id=uuid.uuid4(), **kwargs)

    async def test_transition_to_confirmed_publishes_event_with_leader_from_directory(self) -> None:
        assignment = self._assignment(leader_id=uuid.uuid4())
        publish = await _update_assignment(
            assignment, ServiceAssignmentUpdate(status=AssignmentStatus.CONFIRMED)
        )
        (event,) = _published(publish)
        assert event.event_type == EventType.ASSIGNMENT_CONFIRMED
        assert event.payload == {
            "leader_name": "Pr. Leader",
            "event_title": "Christvesper",
            "event_date": "2026-12-24",
        }

    async def test_free_text_leader_name_is_used(self) -> None:
        assignment = self._assignment(leader_name="Gastprediger")
        publish = await _update_assignment(
            assignment, ServiceAssignmentUpdate(status=AssignmentStatus.CONFIRMED)
        )
        assert _published(publish)[0].payload["leader_name"] == "Gastprediger"

    @pytest.mark.parametrize("already_confirmed", [True, False])
    async def test_no_event_without_transition_to_confirmed(self, already_confirmed) -> None:
        assignment = self._assignment(leader_name="X")
        if already_confirmed:
            assignment.status = AssignmentStatus.CONFIRMED
            body = ServiceAssignmentUpdate(status=AssignmentStatus.CONFIRMED)
        else:
            body = ServiceAssignmentUpdate(leader_name="Y")
        publish = await _update_assignment(assignment, body)
        publish.assert_not_called()


# ── REGISTRATION_RECEIVED ────────────────────────────────────────────────────


async def test_registration_approval_publishes_event() -> None:
    reg = LeaderRegistration.create(district_id=DISTRICT, name="Anna", email="anna@example.org")
    congregation_id = uuid.uuid4()
    reg_repo = AsyncMock()
    reg_repo.get.return_value = reg
    cong_repo = AsyncMock()
    cong_repo.get.return_value = Congregation.create(name="G", district_id=DISTRICT)
    db = AsyncMock()
    db.scalar.return_value = DISTRICT  # congregation_id belongs to the district
    with (
        patch.object(registrations_router, "require_role_in_district"),
        patch.object(registrations_router, "get_idp_provisioner", return_value=None),
        patch.object(registrations_router, "publish_after_commit") as publish,
    ):
        await registrations_router.approve_registration(
            DISTRICT,
            reg.id,
            RegistrationApprove(
                role=Role.PLANNER,
                scope_type=ScopeType.CONGREGATION,
                scope_id=congregation_id,
                congregation_id=congregation_id,
            ),
            _auth(),
            db,
            reg_repo,
            cong_repo,
            AsyncMock(),
            AsyncMock(),
        )

    (event,) = _published(publish)
    assert publish.call_args.args[0] is db
    assert event.event_type == EventType.REGISTRATION_RECEIVED
    assert event.payload == {"leader_name": "Anna", "leader_email": "anna@example.org"}
