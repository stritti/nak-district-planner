# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""HTTP 409 payloads for service-assignment conflicts shared by inbound routers."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.adapters.api.schemas.conflict import ConflictItem, ConflictResponse


def conflict_items(conflicts: list) -> list[ConflictItem]:
    return [
        ConflictItem(
            rule_id=conflict.rule_id,
            severity=conflict.severity,
            message=conflict.message,
            details=conflict.details,
        )
        for conflict in conflicts
    ]


def raise_for_conflicts(conflicts: list, *, confirm_warnings: bool) -> None:
    """Block on any BLOCK conflict; WARN conflicts need explicit acknowledgement."""
    blocking = [conflict for conflict in conflicts if conflict.severity.value == "BLOCK"]
    warnings = [conflict for conflict in conflicts if conflict.severity.value == "WARN"]
    if blocking or (warnings and not confirm_warnings):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ConflictResponse(conflicts=conflict_items(blocking + warnings)).model_dump(
                mode="json"
            ),
        )
