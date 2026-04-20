"""app/domain/ports/repositories.py: Module."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.models.calendar_integration import CalendarIntegration
from app.domain.models.congregation import Congregation
from app.domain.models.congregation_group import CongregationGroup
from app.domain.models.district import District
from app.domain.models.event import Event, EventStatus
from app.domain.models.leader import Leader
from app.domain.models.leader_registration import LeaderRegistration, RegistrationStatus
from app.domain.models.invitation import (
    CongregationInvitation,
    InvitationOverwriteRequest,
    OverwriteDecisionStatus,
)
from app.domain.models.service_assignment import ServiceAssignment
from app.domain.models.user import User


class DistrictRepository(ABC):
    @abstractmethod
    async def get(self, district_id: uuid.UUID) -> District | None: ...

    @abstractmethod
    async def list_all(self) -> list[District]: ...

    @abstractmethod
    async def save(self, district: District) -> None: ...


class CongregationGroupRepository(ABC):
    @abstractmethod
    async def get(self, group_id: uuid.UUID) -> CongregationGroup | None: ...

    @abstractmethod
    async def list_by_district(self, district_id: uuid.UUID) -> list[CongregationGroup]: ...

    @abstractmethod
    async def save(self, group: CongregationGroup) -> None: ...

    @abstractmethod
    async def delete(self, group_id: uuid.UUID) -> None: ...


class CongregationRepository(ABC):
    @abstractmethod
    async def get(self, congregation_id: uuid.UUID) -> Congregation | None: ...

    @abstractmethod
    async def list_by_district(
        self, district_id: uuid.UUID, group_id: uuid.UUID | None = None
    ) -> list[Congregation]: ...

    @abstractmethod
    async def list_by_ids(self, congregation_ids: list[uuid.UUID]) -> list[Congregation]: ...

    @abstractmethod
    async def save(self, congregation: Congregation) -> None: ...


class EventRepository(ABC):
    @abstractmethod
    async def get(self, event_id: uuid.UUID) -> Event | None: ...

    @abstractmethod
    async def list(
        self,
        *,
        district_id: uuid.UUID | None = None,
        congregation_id: uuid.UUID | None = None,
        group_id: uuid.UUID | None = None,
        only_district_level: bool = False,
        status: EventStatus | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Event], int]: ...

    @abstractmethod
    async def get_by_external_uid(
        self, external_uid: str, calendar_integration_id: uuid.UUID
    ) -> Event | None: ...

    @abstractmethod
    async def get_by_external_uid_district(
        self, external_uid: str, district_id: uuid.UUID
    ) -> Event | None: ...

    @abstractmethod
    async def list_linked_by_source_event(self, source_event_id: uuid.UUID) -> list[Event]: ...

    @abstractmethod
    async def get_by_generation_slot_key(
        self,
        *,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID,
        generation_slot_key: str,
    ) -> Event | None: ...

    @abstractmethod
    async def get_matching_draft_service_slot(
        self,
        *,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> Event | None: ...

    @abstractmethod
    async def save(self, event: Event) -> None: ...

    @abstractmethod
    async def delete_before(self, cutoff: datetime) -> int:
        """Delete all events whose end_at is before *cutoff*.

        Returns the number of deleted rows.
        """
        ...


class ServiceAssignmentRepository(ABC):
    @abstractmethod
    async def get(self, assignment_id: uuid.UUID) -> ServiceAssignment | None: ...

    @abstractmethod
    async def list_by_event(self, event_id: uuid.UUID) -> list[ServiceAssignment]: ...

    @abstractmethod
    async def list_by_events(self, event_ids: list[uuid.UUID]) -> list[ServiceAssignment]: ...

    @abstractmethod
    async def save(self, assignment: ServiceAssignment) -> None: ...

    @abstractmethod
    async def delete(self, assignment_id: uuid.UUID) -> None:
        pass


class InvitationRepository(ABC):
    @abstractmethod
    async def get(self, invitation_id: uuid.UUID) -> CongregationInvitation | None: ...

    @abstractmethod
    async def list_by_source_event(
        self, source_event_id: uuid.UUID
    ) -> list[CongregationInvitation]: ...

    @abstractmethod
    async def list_by_source_events(
        self, source_event_ids: list[uuid.UUID]
    ) -> list[CongregationInvitation]: ...

    @abstractmethod
    async def save(self, invitation: CongregationInvitation) -> None: ...

    @abstractmethod
    async def delete(self, invitation_id: uuid.UUID) -> None: ...


class InvitationOverwriteRequestRepository(ABC):
    @abstractmethod
    async def get(self, request_id: uuid.UUID) -> InvitationOverwriteRequest | None: ...

    @abstractmethod
    async def list_open_by_district(
        self, district_id: uuid.UUID
    ) -> list[InvitationOverwriteRequest]: ...

    @abstractmethod
    async def list_open_by_source_event(
        self, source_event_id: uuid.UUID
    ) -> list[InvitationOverwriteRequest]: ...

    @abstractmethod
    async def save(self, request: InvitationOverwriteRequest) -> None: ...

    @abstractmethod
    async def set_status(
        self,
        request_id: uuid.UUID,
        status: OverwriteDecisionStatus,
    ) -> InvitationOverwriteRequest | None: ...


class LeaderRepository(ABC):
    @abstractmethod
    async def get(self, leader_id: uuid.UUID) -> Leader | None: ...

    @abstractmethod
    async def list_by_district(
        self,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID | None = None,
        active_only: bool = False,
    ) -> list[Leader]: ...

    @abstractmethod
    async def save(self, leader: Leader) -> None: ...

    @abstractmethod
    async def delete(self, leader_id: uuid.UUID) -> None: ...


class CalendarIntegrationRepository(ABC):
    @abstractmethod
    async def get(self, integration_id: uuid.UUID) -> CalendarIntegration | None: ...

    @abstractmethod
    async def list_by_district(self, district_id: uuid.UUID) -> list[CalendarIntegration]: ...

    @abstractmethod
    async def list_active(self) -> list[CalendarIntegration]:
        """Return all active integrations — used by the Celery beat scheduler."""
        ...

    @abstractmethod
    async def save(self, integration: CalendarIntegration) -> None: ...

    @abstractmethod
    async def delete(self, integration_id: uuid.UUID) -> None: ...


class UserRepository(ABC):
    @abstractmethod
    async def get_by_sub(self, sub: str) -> User | None:
        """Get user by OIDC subject (user ID from IDP)."""
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        ...

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get user by internal UUID."""
        ...

    @abstractmethod
    async def save(self, user: User) -> None:
        """Create or update user."""
        ...

    @abstractmethod
    async def has_any_user(self) -> bool:
        """Check whether at least one user exists."""
        ...


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
