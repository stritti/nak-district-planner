# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Contract tests for authenticated, observable coverage reporting in CI."""

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[4] / ".github" / "workflows" / "ci.yml"


def _workflow_step(source: str, title: str) -> str:
    marker = f"      - name: {title}\n"
    return source.split(marker, 1)[1].split("\n      - name:", 1)[0]


def test_codecov_upload_requires_token_and_reports_errors() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    upload = _workflow_step(workflow, "Upload coverage to Codecov")

    assert "CODECOV_TOKEN_CONFIGURED: ${{ secrets.CODECOV_TOKEN != '' }}" in workflow
    assert "if: ${{ success() && env.CODECOV_TOKEN_CONFIGURED == 'true' }}" in upload
    assert "token: ${{ secrets.CODECOV_TOKEN }}" in upload
    assert "fail_ci_if_error: true" in upload


def test_missing_codecov_token_is_reported_without_disabling_local_coverage_gate() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    skip = _workflow_step(workflow, "Explain skipped Codecov upload")

    assert "if: ${{ success() && env.CODECOV_TOKEN_CONFIGURED != 'true' }}" in skip
    assert "::warning" in skip
    assert "CODECOV_TOKEN" in skip
    assert 'if [ "$TOTAL_COVERAGE" -lt 80 ]; then' in workflow
    assert "scripts/check_critical_router_coverage.py coverage.xml" in workflow
