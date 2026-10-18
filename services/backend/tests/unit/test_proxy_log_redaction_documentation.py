# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Guard the operational contract for the external ICS bearer route (#629)."""

from pathlib import Path

RUNBOOK = Path(__file__).resolve().parents[4] / "docs" / "operations" / "production-runbook.md"


def test_proxy_log_configuration_uses_original_request_and_suppresses_errors() -> None:
    section = RUNBOOK.read_text(encoding="utf-8").split("### 1.1a ")[1].split("### 1.2 ")[0]
    assert "map $request_uri $log_ics_request" in section
    assert "error_log /dev/null crit;" in section
    assert "map $uri $log_ics_request" not in section


def test_canary_requires_live_response_failure_case_and_propagates_exit_code() -> None:
    section = RUNBOOK.read_text(encoding="utf-8").split("### 1.1a ")[1].split("### 1.2 ")[0]
    assert "HTTP 200" in section
    assert "5xx" in section
    assert 'exit "$STATUS"' in section


def test_retained_token_can_be_resolved_to_export_token_id_safely() -> None:
    section = RUNBOOK.read_text(encoding="utf-8").split("### 1.1a ")[1].split("### 1.2 ")[0]
    assert "sha256sum" in section
    assert "WHERE token_hash=" in section
