"""app/domain/ports/repositories.py: Module."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import date, datetime

from app.domain.models.calendar_integration import CalendarIntegration
from app.domain.models.congregation import Congregation
from app.domain.models.congregation_group import CongregationGroup
from app.domain.models.district import District
from app.domain.models.event import Event, EventApprovalStatus, EventStatus
from app.domain.models.event_instance import EventInstance
from app.domain.models.invitation import (
    CongregationInvitation,
    InvitationOverwriteRequest,
    OverwriteDecisionStatus,
)
from app.domain.models.leader import Leader
from app.domain.models.leader_registration import LeaderRegistration, RegistrationStatus
from app.domain.models.notification import Notification, NotificationType
from app.domain.models.planning_series import PlanningSeries
from app.domain.models.planning_slot import PlanningSlot
from app.domain.models.service_assignment import ServiceAssignment
from app.domain.models.user import User


class DistrictRepository(ABC):
    @abstractmethod
    async def get(self, district_id: uuid.UUID) -> District | None:
        pass

    @abstractmethod
    async def list_all(self) -> list[District]:
        pass

    @abstractmethod
    async def save(self, district: District) -> None:
        pass


class CongregationGroupRepository(ABC):
    @abstractmethod
    async def get(self, group_id: uuid.UUID) -> CongregationGroup | None:
        pass

    @abstractmethod
    async def list_by_district(self, district_id: uuid.UUID) -> list[CongregationGroup]:
        pass

    @abstractmethod
    async def save(self, group: CongregationGroup) -> None:
        pass

    @abstractmethod
    async def delete(self, group_id: uuid.UUID) -> None:
        pass


class CongregationRepository(ABC):
    @abstractmethod
    async def get(self, congregation_id: uuid.UUID) -> Congregation | None:
        pass

    @abstractmethod
    async def list_by_district(
        self, district_id: uuid.UUID, group_id: uuid.UUID | None = None
    ) -> list[Congregation]:
        pass

    @abstractmethod
    async def list_by_ids(self, congregation_ids: list[uuid.UUID]) -> list[Congregation]:
        pass

    @abstractmethod
    async def save(self, congregation: Congregation) -> None:
        pass


class EventRepository(ABC):
    @abstractmethod
    async def get(self, event_id: uuid.UUID) -> Event | None:
        pass

    @abstractmethod
    async def list(
        self,
        *,
        district_id: uuid.UUID | None = None,
        congregation_id: uuid.UUID | None = None,
        group_id: uuid.UUID | None = None,
        only_district_level: bool = False,
        status: EventStatus | None = None,
        approval_status: EventApprovalStatus | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Event], int]:
        pass

    @abstractmethod
    async def get_by_external_uid(
        self, external_uid: str, calendar_integration_id: uuid.UUID
    ) -> Event | None:
        pass

    @abstractmethod
    async def get_by_external_uid_district(
        self, external_uid: str, district_id: uuid.UUID
    ) -> Event | None:
        pass

    @abstractmethod
    async def list_linked_by_source_event(self, source_event_id: uuid.UUID) -> list[Event]:
        pass

    @abstractmethod
    async def get_by_generation_slot_key(
        self,
        *,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID,
        generation_slot_key: str,
    ) -> Event | None:
        pass

    @abstractmethod
    async def get_matching_draft_service_slot(
        self,
        *,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> Event | None:
        pass

    @abstractmethod
    async def save(self, event: Event) -> None:
        pass

    @abstractmethod
    async def bulk_update_approval_status(
        self,
        *,
        district_id: uuid.UUID,
        year: int,
        month: int,
        new_status: EventApprovalStatus,
        congregation_id: uuid.UUID | None = None,
    ) -> int:
        """Update approval_status for all events in a given month.

        Returns the number of updated rows.
        """
        pass

    @abstractmethod
    async def delete_before(self, cutoff: datetime) -> int:
        """Delete all events whose end_at is before *cutoff*.

        Returns the number of deleted rows.
        """
        pass


class PlanningSeriesRepository(ABC):
    @abstractmethod
    async def get(self, series_id: uuid.UUID) -> PlanningSeries | None:
        pass

    @abstractmethod
    async def list_all(self) -> list[PlanningSeries]:
        """List all planning series across all districts."""
        pass

    @abstractmethod
    async def list_by_district(self, district_id: uuid.UUID) -> list[PlanningSeries]:
        """List all planning series for a given district."""
        pass

    @abstractmethod
    async def list_all_active(self) -> list[PlanningSeries]:
        """List all active PlanningSeries across all districts."""
        pass

    @abstractmethod
    async def list_active(self) -> list[PlanningSeries]:
        """List all active planning series (is_active=True, within active_from/active_until window)."""
        pass

    @abstractmethod
    async def save(self, series: PlanningSeries) -> None:
        pass


class PlanningSlotRepository(ABC):
    @abstractmethod
    async def get(self, slot_id: uuid.UUID) -> PlanningSlot | None:
        pass

    @abstractmethod
    async def get_by_series_and_date(
        self, series_id: uuid.UUID, planning_date: date
    ) -> PlanningSlot | None:
        """Get PlanningSlot by series_id and planning_date."""
        pass

    @abstractmethod
    async def get_by_series_date(
        self,
        *,
        series_id: uuid.UUID,
        planning_date: date,
        congregation_id: uuid.UUID | None,
    ) -> PlanningSlot | None:
        """Check if a slot already exists for this series on a given date."""
        pass

    @abstractmethod
    async def list_for_date_range(
        self,
        *,
        district_id: uuid.UUID,
        from_date: date,
        to_date: date,
    ) -> list[PlanningSlot]:
        """List all PlanningSlots for a district in a date range."""
        pass

    @abstractmethod
    async def save(self, slot: PlanningSlot) -> None:
        pass


class EventInstanceRepository(ABC):
    @abstractmethod
    async def get(self, instance_id: uuid.UUID) -> EventInstance | None:
        pass

    @abstractmethod
    async def list_by_planning_slot(
        self, planning_slot_id: uuid.UUID
    ) -> list[EventInstance]:
        """List all EventInstances for a specific PlanningSlot."""
        pass

    @abstractmethod
    async def get_by_planning_slot(self, planning_slot_id: uuid.UUID) -> EventInstance | None:
        """Get the first EventInstance for a PlanningSlot (auto-matching)."""
        pass

    @abstractmethod
    async def list_by_planning_slots(
        self, planning_slot_ids: list[uuid.UUID]
    ) -> list[EventInstance]:
        """List all EventInstances for multiple PlanningSlots."""
        pass

    @abstractmethod
    async def save(self, instance: EventInstance) -> None:
        pass


class ServiceAssignmentRepository(ABC):
    @abstractmethod
    async def get(self, assignment_id: uuid.UUID) -> ServiceAssignment | None:
        pass

    @abstractmethod
    async def list_by_planning_slot(self, slot_or_event_id: uuid.UUID) -> list[ServiceAssignment]:
        pass

    @abstractmethod
    async def list_by_planning_slots(
        self, slot_or_event_ids: list[uuid.UUID]
    ) -> list[ServiceAssignment]:
        pass

    @abstractmethod
    async def save(self, assignment: ServiceAssignment) -> None:
        pass

    @abstractmethod
    async def delete(self, assignment_id: uuid.UUID) -> None:
        pass


class InvitationRepository(ABC):
    @abstractmethod
    async def get(self, invitation_id: uuid.UUID) -> CongregationInvitation | None:
        pass

    @abstractmethod
    async def list_by_source_event(
        self, source_event_id: uuid.UUID
    ) -> list[CongregationInvitation]:
        pass

    @abstractmethod
    async def list_by_source_events(
        self, source_event_ids: list[uuid.UUID]
    ) -> list[CongregationInvitation]:
        pass

    @abstractmethod
    async def list_by_source_planning_slot(
        self, source_planning_slot_id: uuid.UUID
    ) -> list[CongregationInvitation]:
        pass

    @abstractmethod
    async def list_by_source_planning_slots(
        self, source_planning_slot_ids: list[uuid.UUID]
    ) -> list[CongregationInvitation]:
        pass

    @abstractmethod
    async def save(self, invitation: CongregationInvitation) -> None:
        pass

    @abstractmethod
    async def delete(self, invitation_id: uuid.UUID) -> None:
        pass


class InvitationOverwriteRequestRepository(ABC):
    @abstractmethod
    async def get(self, request_id: uuid.UUID) -> InvitationOverwriteRequest | None:
        pass

    @abstractmethod
    async def list_open_by_district(
        self, district_id: uuid.UUID
    ) -> list[InvitationOverwriteRequest]:
        pass

    @abstractmethod
    async def list_open_by_source_event(
        self, source_event_id: uuid.UUID
    ) -> list[InvitationOverwriteRequest]:
        pass

    @abstractmethod
    async def save(self, request: InvitationOverwriteRequest) -> None:
        pass

    @abstractmethod
    async def set_status(
        self,
        request_id: uuid.UUID,
        status: OverwriteDecisionStatus,
    ) -> InvitationOverwriteRequest | None:
        pass


class LeaderRepository(ABC):
    @abstractmethod
    async def get(self, leader_id: uuid.UUID) -> Leader | None:
        pass

    @abstractmethod
    async def list_by_district(
        self,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID | None = None,
        active_only: bool = False,
    ) -> list[Leader]:
        pass

    @abstractmethod
    async def save(self, leader: Leader) -> None:
        pass

    @abstractmethod
    async def delete(self, leader_id: uuid.UUID) -> None:
        pass


class CalendarIntegrationRepository(ABC):
    @abstractmethod
    async def get(self, integration_id: uuid.UUID) -> CalendarIntegration | None:
        pass

    @abstractmethod
    async def list_by_district(self, district_id: uuid.UUID) -> list[CalendarIntegration]:
        pass

    @abstractmethod
    async def list_by_congregation(self, congregation_id: uuid.UUID) -> list[CalendarIntegration]:
        pass

    @abstractmethod
    async def list_active(self) -> list[CalendarIntegration]:
        """Return all active integrations — used by the Celery beat scheduler."""
        pass

    @abstractmethod
    async def save(self, integration: CalendarIntegration) -> None:
        pass

    @abstractmethod
    async def delete(self, integration_id: uuid.UUID) -> None:
        pass


class UserRepository(ABC):
    @abstractmethod
    async def get_by_sub(self, sub: str) -> User | None:
        """Get user by OIDC subject (user ID from IDP)."""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get user by internal UUID."""
        pass

    @abstractmethod
    async def save(self, user: User) -> None:
        """Create or update user."""
        pass

    @abstractmethod
    async def has_any_user(self) -> bool:
        """Check whether at least one user exists."""
        pass


class NotificationRepository(ABC):
    @abstractmethod
    async def get(self, notification_id: uuid.UUID) -> Notification | None:
        pass

    @abstractmethod
    async def list_by_district(
        self,
        district_id: uuid.UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        """List notifications for a district, newest first. Returns (items, total)."""
        pass

    @abstractmethod
    async def save(self, notification: Notification) -> None:
        pass

    @abstractmethod
    async def mark_read(self, notification_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    async def mark_all_read(self, district_id: uuid.UUID, user_sub: str) -> int:
        """Mark all unread notifications as read for a district. Returns count."""
        pass


class LeaderRegistrationRepository(ABC):
    @abstractmethod
    async def get(self, registration_id: uuid.UUID) -> LeaderRegistration | None:
        pass

    @abstractmethod
    async def list_by_district(
        self,
        district_id: uuid.UUID,
        status: RegistrationStatus | None = None,
    ) -> list[LeaderRegistration]:
        pass

    @abstractmethod
    async def save(self, registration: LeaderRegistration) -> None:
        pass

    @abstractmethod
    async def delete(self, registration_id: uuid.UUID) -> None:
        pass
