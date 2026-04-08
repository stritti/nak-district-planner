import uuid
from datetime import datetime, time

from pydantic import BaseModel

from app.domain.models.service_assignment import AssignmentStatus


class MatrixCell(BaseModel):
    event_id: uuid.UUID | None = None
    planning_slot_id: uuid.UUID | None = None
    assignment_event_id: uuid.UUID | None = None
    invitation_source_congregation_name: str | None = None
    invitation_count: int = 0
    event_title: str | None = None
    event_start_at: datetime | None = None
    event_end_at: datetime | None = None
    category: str | None = None
    is_gap: bool = False  # category==Gottesdienst AND no assignment
    planned_time: time | None = None
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None
    has_deviation: bool = False
    is_assignment_editable: bool = True
    assignment_id: uuid.UUID | None = None
    assignment_status: AssignmentStatus | None = None
    leader_id: uuid.UUID | None = None
    leader_name: str | None = None


class MatrixRow(BaseModel):
    congregation_id: uuid.UUID
    congregation_name: str
    group_id: uuid.UUID | None = None
    group_name: str | None = None
    cells: dict[str, MatrixCell]  # "YYYY-MM-DD" → cell


class MatrixResponse(BaseModel):
    dates: list[str]  # sorted ISO date strings "YYYY-MM-DD"
    rows: list[MatrixRow]
    holidays: dict[str, list[str]] = {}  # "YYYY-MM-DD" → list of holiday names
