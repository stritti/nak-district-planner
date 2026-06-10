"""Pydantic schemas for system version and update endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class SystemVersionResponse(BaseModel):
    """Response for GET /api/v1/system/version."""

    current_version: str
    latest_version: str | None = None
    last_checked: float | None = None
    release_url: str | None = None


class UpdateResponse(BaseModel):
    """Response for POST /api/v1/system/update."""

    status: str  # "manual" | "started"
    mode: str = "manual"
    instructions: list[str] | None = None
