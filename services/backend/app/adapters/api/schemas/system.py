# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Pydantic schemas for the system version endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class SystemVersionResponse(BaseModel):
    """Response for GET /api/v1/system/version."""

    current_version: str
    latest_version: str | None = None
    last_checked: float | None = None
    release_url: str | None = None
    update_available: bool = False
