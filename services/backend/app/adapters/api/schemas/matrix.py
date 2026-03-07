import uuid

from pydantic import BaseModel

from app.domain.models.service_assignment import AssignmentStatus


class MatrixCell(BaseModel):
    event_id: uuid.UUID | None = None
    event_title: str | None = None
    category: str | None = None
    is_gap: bool = False  # category==Gottesdienst AND no assignment
    assignment_id: uuid.UUID | None = None
    assignment_status: AssignmentStatus | None = None
    leader_name: str | None = None


class MatrixRow(BaseModel):
    congregation_id: uuid.UUID
    congregation_name: str
    cells: dict[str, MatrixCell]  # "YYYY-MM-DD" → cell


class MatrixResponse(BaseModel):
    dates: list[str]  # sorted ISO date strings "YYYY-MM-DD"
    rows: list[MatrixRow]
    holidays: dict[str, list[str]] = {}  # "YYYY-MM-DD" → list of holiday names
