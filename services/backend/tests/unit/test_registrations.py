"""Unit tests for registration schemas and domain model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timezone

import pytest
from pydantic import ValidationError

from app.adapters.api.schemas.registration import (
    RegistrationApprove,
    RegistrationCreate,
    RegistrationReject,
    RegistrationResponse,
)
from app.domain.models.leader_registration import LeaderRegistration, RegistrationStatus
from app.domain.models.membership import ScopeType
from app.domain.models.role import Role


class TestRegistrationCreateSchema:
    """Tests for RegistrationCreate schema validation."""

    def test_valid_minimal(self):
        """Minimal valid registration (name + email only)."""
        data = {"name": "Max Mustermann", "email": "max@example.com"}
        reg = RegistrationCreate(**data)
        assert reg.name == "Max Mustermann"
        assert reg.email == "max@example.com"
        assert reg.rank is None
        assert reg.congregation_id is None

    def test_valid_with_rank(self):
        """Registration with optional rank."""
        data = {
            "name": "Max Mustermann",
            "email": "max@example.com",
            "rank": "Pr.",
            "phone": "+49123456789",
            "notes": "Bitte Gemeinde Musterstadt",
        }
        reg = RegistrationCreate(**data)
        assert reg.rank == "Pr."
        assert reg.notes == "Bitte Gemeinde Musterstadt"

    def test_missing_name(self):
        """Registration without name should fail."""
        with pytest.raises(ValidationError):
            RegistrationCreate(email="max@example.com")  # type: ignore[call-arg]

    def test_missing_email(self):
        """Registration without email should fail."""
        with pytest.raises(ValidationError):
            RegistrationCreate(name="Max")  # type: ignore[call-arg]

    def test_invalid_email(self):
        """Invalid email format should fail."""
        with pytest.raises(ValidationError):
            RegistrationCreate(name="Max", email="not-an-email")

    def test_empty_name_fails(self):
        """Empty name should fail (min_length=1)."""
        with pytest.raises(ValidationError):
            RegistrationCreate(name="", email="max@example.com")

    def test_phone_max_length(self):
        """Phone longer than 100 chars should fail."""
        with pytest.raises(ValidationError):
            RegistrationCreate(name="Max", email="max@example.com", phone="x" * 101)


class TestRegistrationApproveSchema:
    def test_required_assignment_fields(self):
        body = RegistrationApprove(
            role=Role.PLANNER,
            scope_type=ScopeType.DISTRICT,
            scope_id=uuid.uuid4(),
        )
        assert body.role == Role.PLANNER
        assert body.scope_type == ScopeType.DISTRICT

    def test_with_congregation(self):
        body = RegistrationApprove(
            role=Role.PLANNER,
            scope_type=ScopeType.CONGREGATION,
            scope_id=uuid.uuid4(),
            congregation_id=uuid.uuid4(),
            rank="Di.",
        )
        assert body.rank == "Di."


class TestRegistrationRejectSchema:
    def test_empty_body(self):
        body = RegistrationReject()
        assert body.reason is None

    def test_with_reason(self):
        body = RegistrationReject(reason="Keine freie Stelle")
        assert body.reason == "Keine freie Stelle"


class TestPendingOverviewSchema:
    def test_registration_pending_count_response(self):
        from app.adapters.api.routers.registrations import RegistrationPendingCountResponse

        row = RegistrationPendingCountResponse(district_id=uuid.uuid4(), pending=2)
        assert row.pending == 2

    def test_registration_pending_overview_response(self):
        from app.adapters.api.routers.registrations import (
            RegistrationPendingCountResponse,
            RegistrationPendingOverviewResponse,
        )

        district_id = uuid.uuid4()
        payload = RegistrationPendingOverviewResponse(
            total_pending=2,
            by_district=[RegistrationPendingCountResponse(district_id=district_id, pending=2)],
        )
        assert payload.total_pending == 2
        assert payload.by_district[0].district_id == district_id


class TestLeaderRegistrationDomainModel:
    def test_create_sets_pending_status(self):
        """LeaderRegistration.create() always starts with PENDING status."""
        reg = LeaderRegistration.create(
            district_id=uuid.uuid4(),
            name="Test Person",
            email="test@example.com",
        )
        assert reg.status == RegistrationStatus.PENDING
        assert reg.rejection_reason is None
        assert reg.user_sub is None
        assert reg.assigned_role is None
        assert reg.assigned_scope_type is None
        assert reg.assigned_scope_id is None
        assert reg.approved_by_sub is None
        assert reg.approved_at is None
        assert reg.idp_provision_status is None
        assert reg.idp_provision_error is None
        assert reg.idp_provisioned_at is None
        assert isinstance(reg.id, uuid.UUID)

    def test_create_with_user_sub(self):
        reg = LeaderRegistration.create(
            district_id=uuid.uuid4(),
            name="Test Person",
            email="test@example.com",
            user_sub="oidc|user-123",
        )
        assert reg.user_sub == "oidc|user-123"

    def test_created_at_set_automatically(self):
        before = datetime.now(UTC)
        reg = LeaderRegistration.create(
            district_id=uuid.uuid4(),
            name="Test",
            email="t@example.com",
        )
        after = datetime.now(UTC)
        assert before <= reg.created_at <= after
        assert reg.created_at == reg.updated_at


class TestRegistrationResponseSchema:
    def test_full_response(self):
        now = datetime.now(UTC)
        data = {
            "id": uuid.uuid4(),
            "district_id": uuid.uuid4(),
            "name": "Test",
            "email": "t@example.com",
            "rank": None,
            "congregation_id": None,
            "special_role": None,
            "phone": None,
            "notes": None,
            "status": "PENDING",
            "rejection_reason": None,
            "user_sub": None,
            "assigned_role": None,
            "assigned_scope_type": None,
            "assigned_scope_id": None,
            "approved_by_sub": None,
            "approved_at": None,
            "idp_provision_status": None,
            "idp_provision_error": None,
            "idp_provisioned_at": None,
            "created_at": now,
            "updated_at": now,
        }
        resp = RegistrationResponse(**data)
        assert resp.status == RegistrationStatus.PENDING
