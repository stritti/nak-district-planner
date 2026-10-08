from __future__ import annotations

import uuid
from collections.abc import Collection, Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from enum import Enum, StrEnum

APPLICABILITY_ALL = "all"
"""Sentinel: a district-level slot applies to every congregation of the district."""


class InvalidApplicabilityError(ValueError):
    """The requested congregation distribution violates the UC-04 rules."""


class EventApprovalStatus(StrEnum):
    """Planning/release workflow status (matches the DB enum event_approval_status)."""

    PLANNED = "PLANNED"
    CONFIRMED = "CONFIRMED"


class PlanningSlotStatus(str, Enum):
    """Status of a planning slot in the system.

    ACTIVE slots are usable for service assignments; CANCELLED slots
    are excluded from the planning matrix and assignment flow.
    """

    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


@dataclass
class PlanningSlot:
    id: uuid.UUID
    district_id: uuid.UUID
    planning_date: date
    planning_time: time
    status: PlanningSlotStatus
    created_at: datetime
    updated_at: datetime
    series_id: uuid.UUID | None = None
    congregation_id: uuid.UUID | None = None
    category: str | None = None
    # Title for the slot (used when no EventInstance exists or as fallback)
    title: str | None = None
    # Approval status for planning workflow (migrated from Event.approval_status)
    approval_status: EventApprovalStatus | None = None
    # Invitation tracking fields (migrated from Event)
    invitation_source_congregation_id: uuid.UUID | None = None
    invitation_source_event_id: uuid.UUID | None = None
    # List of congregation IDs (as strings) that this slot applies to (for district-wide holidays)
    # Supports "all" sentinel string for district-wide applicability
    applicability: list[str] = field(default_factory=list)
    # Stable identity of the generator occurrence that created this slot (e.g.
    # "draft-service:<congregation>:<local date>"). Survives planner edits of
    # date/time so a re-run never re-creates a moved, cancelled slot. Unique per
    # district; None for manually created or imported slots.
    generation_key: str | None = None

    @classmethod
    def create(
        cls,
        *,
        district_id: uuid.UUID,
        planning_date: date,
        planning_time: time,
        series_id: uuid.UUID | None = None,
        congregation_id: uuid.UUID | None = None,
        category: str | None = None,
        title: str | None = None,
        approval_status: EventApprovalStatus | None = None,
        invitation_source_congregation_id: uuid.UUID | None = None,
        invitation_source_event_id: uuid.UUID | None = None,
        applicability: list[str] | None = None,
        status: PlanningSlotStatus = PlanningSlotStatus.ACTIVE,
        slot_id: uuid.UUID | None = None,
        generation_key: str | None = None,
    ) -> PlanningSlot:
        now = datetime.now(timezone.utc)
        return cls(
            id=slot_id or uuid.uuid4(),
            district_id=district_id,
            series_id=series_id,
            congregation_id=congregation_id,
            category=category,
            title=title,
            approval_status=approval_status,
            invitation_source_congregation_id=invitation_source_congregation_id,
            invitation_source_event_id=invitation_source_event_id,
            applicability=applicability or [],
            generation_key=generation_key,
            planning_date=planning_date,
            planning_time=planning_time,
            status=status,
            created_at=now,
            updated_at=now,
        )

    def forget_generation_key_if_reassigned(
        self,
        *,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID | None,
        category: str | None,
    ) -> None:
        """Drop the generator identity once the slot stops being the generated occurrence.

        The key names the congregation's service occurrence (district-unique). A slot
        moved to another congregation or changed to another category no longer
        represents it; keeping the key would make the generator treat the original
        service as existing, and the unique index would block re-creating it. Pass
        the district/congregation/category as last persisted.
        """
        if (self.district_id, self.congregation_id, self.category) != (
            district_id,
            congregation_id,
            category,
        ):
            self.generation_key = None


    def is_visible_to(self, congregation_id: uuid.UUID) -> bool:
        """Whether this slot belongs in the given congregation's scope (UC-03/04/05).

        A congregation slot is visible only to its own congregation; a district
        slot (``congregation_id is None``) only to the congregations listed in
        ``applicability`` (or all of them via the ``"all"`` sentinel). An empty
        ``applicability`` means "not distributed". Status and approval are
        deliberately not considered here; see :meth:`is_distributed_to`.
        """
        if self.congregation_id is not None:
            return self.congregation_id == congregation_id
        return (
            APPLICABILITY_ALL in self.applicability
            or str(congregation_id) in self.applicability
        )

    @property
    def is_confirmed(self) -> bool:
        """Approval policy: only CONFIRMED slots are released to outside audiences."""
        return self.approval_status == EventApprovalStatus.CONFIRMED

    def is_distributed_to(self, congregation_id: uuid.UUID) -> bool:
        """Whether a district slot is released (CONFIRMED) to the congregation (UC-04)."""
        return (
            self.congregation_id is None
            and self.is_confirmed
            and self.is_visible_to(congregation_id)
        )

    def distribute_to(
        self,
        entries: Iterable[str],
        district_congregation_ids: Collection[uuid.UUID],
    ) -> None:
        """Set the congregations a district-level slot is distributed to (UC-04).

        Accepts either the ``"all"`` sentinel alone, an empty list (not
        distributed) or congregation IDs of this slot's district. IDs are stored
        canonically and de-duplicated in input order.
        """
        requested = list(dict.fromkeys(entries))
        if any(not entry.strip() for entry in requested):
            raise InvalidApplicabilityError("Leere Gemeinde-IDs sind nicht erlaubt.")
        requested = [entry.strip() for entry in requested]
        if requested and self.congregation_id is not None:
            raise InvalidApplicabilityError(
                "Nur Bezirksveranstaltungen können an Gemeinden verteilt werden."
            )
        if APPLICABILITY_ALL in requested:
            if len(requested) > 1:
                raise InvalidApplicabilityError(
                    "'all' kann nicht mit einzelnen Gemeinden kombiniert werden."
                )
            self.applicability = [APPLICABILITY_ALL]
            return
        self.applicability = list(
            dict.fromkeys(
                str(_congregation_in_district(entry, district_congregation_ids))
                for entry in requested
            )
        )


def _congregation_in_district(
    entry: str, district_congregation_ids: Collection[uuid.UUID]
) -> uuid.UUID:
    try:
        congregation_id = uuid.UUID(entry)
    except ValueError as exc:
        raise InvalidApplicabilityError(f"Ungültige Gemeinde-ID: {entry!r}") from exc
    if congregation_id not in district_congregation_ids:
        raise InvalidApplicabilityError("Gemeinde gehört nicht zum Bezirk des Ereignisses.")
    return congregation_id
