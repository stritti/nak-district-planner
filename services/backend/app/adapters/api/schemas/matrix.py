import uuid
from datetime import datetime, time

from pydantic import BaseModel

from app.domain.models.service_assignment import AssignmentStatus


class MatrixCell(BaseModel):
    event_id: uuid.UUID | None = None
    planning_slot_id: uuid.UUID | None = None
    event_title: str | None = None
    category: str | None = None
    is_gap: bool = False  # category==Gottesdienst AND no assignment
    planned_time: time | None = None
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None
    has_deviation: bool = False
    assignment_id: uuid.UUID | None = None
    assignment_status: AssignmentStatus | None = None
    leader_id: uuid.UUID | None = None
    leader_name: str | None = None


class MatrixRow(BaseModel):
    congregation_id: uuid.UUID
    congregation_name: str
    cells: dict[str, MatrixCell]  # "YYYY-MM-DD" → cell


class MatrixResponse(BaseModel):
    dates: list[str]  # sorted ISO date strings "YYYY-MM-DD"
    rows: list[MatrixRow]
    holidays: dict[str, list[str]] = {}  # "YYYY-MM-DD" → list of holiday names
