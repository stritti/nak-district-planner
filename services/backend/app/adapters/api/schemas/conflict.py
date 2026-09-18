"""API schemas for planning conflict responses."""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.planning.conflict_result import Severity


class ConflictItem(BaseModel):
    rule_id: str
    severity: Severity
    message: str
    details: dict[str, object]


class ConflictResponse(BaseModel):
    conflicts: list[ConflictItem]
