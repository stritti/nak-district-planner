"""Unit tests for API schemas and validation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timezone

import pytest
from pydantic import ValidationError

from app.adapters.api.schemas.district import (
    CongregationCreate,
    CongregationUpdate,
    DistrictCreate,
    DistrictResponse,
)
from app.adapters.api.schemas.event import (
    EventCreate,
    EventResponse,
    EventUpdate,
)
from app.adapters.api.schemas.leader import (
    LeaderCreate,
    LeaderResponse,
)
from app.adapters.api.schemas.service_assignment import (
    ServiceAssignmentCreate,
    ServiceAssignmentResponse,
)


class TestEventCreateSchema:
    """Tests for EventCreate schema validation."""

    def test_event_create_valid(self):
        """Valid EventCreate should pass validation."""
        data = {
            "title": "Gottesdienst",
            "district_id": str(uuid.uuid4()),
            "start_at": datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
            "end_at": datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
        }
        event = EventCreate(**data)
        assert event.title == "Gottesdienst"

    def test_event_create_missing_title(self):
        """EventCreate without title should fail."""
        data = {
            "district_id": str(uuid.uuid4()),
            "start_at": datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
            "end_at": datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
        }
        with pytest.raises(ValidationError):
            EventCreate(**data)

    def test_event_create_missing_district_id(self):
        """EventCreate without district_id should fail."""
        data = {
            "title": "Gottesdienst",
            "start_at": datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
            "end_at": datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
        }
        with pytest.raises(ValidationError):
            EventCreate(**data)

    def test_event_create_with_optional_fields(self):
        """EventCreate with optional fields should pass."""
        data = {
            "title": "Gottesdienst",
            "description": "Morningservice",
            "district_id": str(uuid.uuid4()),
            "congregation_id": str(uuid.uuid4()),
            "start_at": datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
            "end_at": datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
            "category": "Gottesdienst",
            "source": "INTERNAL",
            "status": "DRAFT",
            "visibility": "INTERNAL",
        }
        event = EventCreate(**data)
        assert event.description == "Morningservice"
        assert event.category == "Gottesdienst"

    def test_event_create_invalid_uuid(self):
        """EventCreate with invalid UUID should fail."""
        data = {
            "title": "Gottesdienst",
            "district_id": "not-a-uuid",
            "start_at": datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
            "end_at": datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
        }
        with pytest.raises(ValidationError):
            EventCreate(**data)

    def test_event_create_invalid_status(self):
        """EventCreate with invalid status should fail."""
        data = {
            "title": "Gottesdienst",
            "district_id": str(uuid.uuid4()),
            "start_at": datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
            "end_at": datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
            "status": "INVALID_STATUS",
        }
        with pytest.raises(ValidationError):
            EventCreate(**data)


class TestEventUpdateSchema:
    """Tests for EventUpdate schema validation."""

    def test_event_update_all_fields_optional(self):
        """EventUpdate with no fields should be valid."""
        event = EventUpdate()
        assert event.district_id is None
        assert event.status is None

    def test_event_update_partial(self):
        """EventUpdate with partial fields should pass."""
        data = {
            "status": "PUBLISHED",
        }
        event = EventUpdate(**data)
        assert event.status == "PUBLISHED"
        assert event.district_id is None

    def test_event_update_invalid_status(self):
        """EventUpdate with invalid status should fail."""
        data = {"status": "INVALID"}
        with pytest.raises(ValidationError):
            EventUpdate(**data)


class TestEventResponseSchema:
    """Tests for EventResponse schema."""

    def test_event_response_creation(self):
        """EventResponse should accept valid data."""
        event_id = uuid.uuid4()
        district_id = uuid.uuid4()
        data = {
            "id": event_id,
            "title": "Gottesdienst",
            "description": "Morning service",
            "district_id": district_id,
            "congregation_id": None,
            "category": "Gottesdienst",
            "source": "INTERNAL",
            "status": "DRAFT",
            "visibility": "INTERNAL",
            "audiences": [],
            "applicability": [],
            "start_at": datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
            "end_at": datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        response = EventResponse(**data)
        assert response.id == event_id
        assert response.title == "Gottesdienst"


class TestDistrictSchema:
    """Tests for District schemas."""

    def test_district_create_valid(self):
        """Valid DistrictCreate should pass."""
        data = {
            "name": "Bezirk München",
            "state_code": "BY",
        }
        district = DistrictCreate(**data)
        assert district.name == "Bezirk München"

    def test_district_create_missing_name(self):
        """DistrictCreate without name should fail."""
        with pytest.raises(ValidationError):
            DistrictCreate()

    def test_district_response_creation(self):
        """DistrictResponse should accept valid data."""
        district_id = uuid.uuid4()
        data = {
            "id": district_id,
            "name": "Bezirk München",
            "state_code": "BY",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        response = DistrictResponse(**data)
        assert response.id == district_id
        assert response.name == "Bezirk München"


class TestCongregationSchema:
    def test_congregation_create_with_group(self):
        payload = CongregationCreate(name="Gemeinde A", group_id=uuid.uuid4())
        assert payload.group_id is not None

    def test_congregation_create_without_group(self):
        payload = CongregationCreate(name="Gemeinde B")
        assert payload.group_id is None

    def test_congregation_update_accepts_group_reset(self):
        payload = CongregationUpdate(group_id=None)
        assert "group_id" in payload.model_fields_set


class TestLeaderSchema:
    """Tests for Leader schemas."""

    def test_leader_create_valid(self):
        """Valid LeaderCreate should pass."""
        data = {
            "name": "Pastor Schmidt",
            "rank": "Ap.",
            "email": "schmidt@example.com",
            "congregation_id": str(uuid.uuid4()),
        }
        leader = LeaderCreate(**data)
        assert leader.name == "Pastor Schmidt"

    def test_leader_create_missing_name(self):
        """LeaderCreate without name should fail."""
        data = {
            "rank": "APOSTLE",
            "congregation_id": str(uuid.uuid4()),
        }
        with pytest.raises(ValidationError):
            LeaderCreate(**data)

    def test_leader_create_missing_rank(self):
        """LeaderCreate without rank should succeed with rank defaulting to None."""
        data = {
            "name": "Pastor Schmidt",
            "congregation_id": str(uuid.uuid4()),
        }
        leader = LeaderCreate(**data)
        assert leader.rank is None

    def test_leader_response_creation(self):
        """LeaderResponse should accept valid data."""
        leader_id = uuid.uuid4()
        congregation_id = uuid.uuid4()
        district_id = uuid.uuid4()
        data = {
            "id": leader_id,
            "name": "Pastor Schmidt",
            "rank": "Ap.",
            "congregation_id": congregation_id,
            "district_id": district_id,
            "special_role": None,
            "user_sub": None,
            "email": "schmidt@example.com",
            "phone": None,
            "notes": None,
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        response = LeaderResponse(**data)
        assert response.id == leader_id
        assert response.name == "Pastor Schmidt"


class TestServiceAssignmentSchema:
    """Tests for ServiceAssignment schemas."""

    def test_service_assignment_create_with_leader_name(self):
        """Valid ServiceAssignmentCreate with leader_name should pass."""
        data = {
            "leader_name": "Pastor Schmidt",
        }
        assignment = ServiceAssignmentCreate(**data)
        assert assignment.leader_name == "Pastor Schmidt"

    def test_service_assignment_create_with_leader_id(self):
        """Valid ServiceAssignmentCreate with leader_id should pass."""
        data = {
            "leader_id": str(uuid.uuid4()),
        }
        assignment = ServiceAssignmentCreate(**data)
        assert assignment.leader_id is not None

    def test_service_assignment_create_missing_both(self):
        """ServiceAssignmentCreate without leader_id or leader_name should fail."""
        data = {}
        with pytest.raises(ValidationError):
            ServiceAssignmentCreate(**data)

    def test_service_assignment_create_missing_leader_name(self):
        """ServiceAssignmentCreate without leader_name should fail if no leader_id."""
        data = {}
        with pytest.raises(ValidationError):
            ServiceAssignmentCreate(**data)

    def test_service_assignment_response_creation(self):
        """ServiceAssignmentResponse should accept valid data."""
        assignment_id = uuid.uuid4()
        event_id = uuid.uuid4()
        leader_id = uuid.uuid4()
        data = {
            "id": assignment_id,
            "event_id": event_id,
            "leader_id": leader_id,
            "leader_name": "Pastor Schmidt",
            "status": "ASSIGNED",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        response = ServiceAssignmentResponse(**data)
        assert response.id == assignment_id
        assert response.leader_name == "Pastor Schmidt"
