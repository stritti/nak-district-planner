# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Structured conflict mapping and explicit severity acknowledgement."""

import pytest
from fastapi import HTTPException

from app.adapters.api.conflict_http import raise_for_conflicts
from app.domain.planning.conflict_result import ConflictResult, Severity


@pytest.mark.parametrize(
    ("severity", "confirmed", "blocked"),
    [
        (Severity.PASS, False, False),
        (Severity.WARN, False, True),
        (Severity.WARN, True, False),
        (Severity.BLOCK, False, True),
        (Severity.BLOCK, True, True),
    ],
)
def test_conflict_acknowledgement_policy(severity, confirmed, blocked):
    conflict = ConflictResult(
        rule_id="RULE", severity=severity, message="Konflikt", details={"event": "e1"},
    )
    if blocked:
        with pytest.raises(HTTPException) as exc:
            raise_for_conflicts([conflict], confirm_warnings=confirmed)
        assert exc.value.status_code == 409
        assert exc.value.detail["conflicts"] == [{
            "rule_id": "RULE", "severity": severity.value,
            "message": "Konflikt", "details": {"event": "e1"},
        }]
    else:
        raise_for_conflicts([conflict], confirm_warnings=confirmed)


def test_confirmed_warning_never_overrides_a_mixed_blocking_conflict():
    conflicts = [
        ConflictResult(rule_id="WARN", severity=Severity.WARN, message="Warnung"),
        ConflictResult(rule_id="BLOCK", severity=Severity.BLOCK, message="Blockade"),
    ]
    with pytest.raises(HTTPException) as exc:
        raise_for_conflicts(conflicts, confirm_warnings=True)
    assert {item["severity"] for item in exc.value.detail["conflicts"]} == {"BLOCK", "WARN"}
