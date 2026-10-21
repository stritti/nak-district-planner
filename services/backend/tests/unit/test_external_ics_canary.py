# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Regression checks for offline inspection of ICS bearer tokens in logs (#629)."""

from __future__ import annotations

import gzip
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "check_ics_canary_logs.py"
TOKEN = "synthetic-canary-token-0123456789"


def _run(*, sources: list[str], token: str = TOKEN) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *[part for src in sources for part in ("--source", src)]],
        input=token + "\n",
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def _assert_secret_not_reported(result: subprocess.CompletedProcess[str]) -> None:
    assert TOKEN not in result.stdout
    assert TOKEN not in result.stderr


def test_redacted_proxy_and_apm_logs_pass(tmp_path: Path) -> None:
    proxy = tmp_path / "proxy.jsonl"
    tracing = tmp_path / "spans.jsonl"
    proxy.write_text('{"path":"/api/v1/export/[REDACTED]/calendar.ics"}\n')
    tracing.write_text('{"route":"/api/v1/export/{token}/calendar.ics"}\n')
    result = _run(sources=[str(proxy), str(tracing)])
    assert result.returncode == 0
    assert "2 sources" in result.stdout
    _assert_secret_not_reported(result)


def test_raw_proxy_path_rejects_without_printing_token(tmp_path: Path) -> None:
    proxy = tmp_path / "proxy.jsonl"
    proxy.write_text(f'{{"path":"/api/v1/export/{TOKEN}/calendar.ics"}}\n')
    result = _run(sources=[str(proxy)])
    assert result.returncode == 1
    assert "TOKEN FOUND" in result.stdout
    _assert_secret_not_reported(result)


def test_raw_token_across_read_boundary_is_detected(tmp_path: Path) -> None:
    proxy = tmp_path / "proxy.log"
    proxy.write_bytes(b"x" * (65536 - 5) + TOKEN.encode() + b"\n")
    result = _run(sources=[str(proxy)])
    assert result.returncode == 1
    _assert_secret_not_reported(result)


@pytest.mark.parametrize(
    ("sources", "token"), [([], TOKEN), (["missing.log"], TOKEN), (["dummy"], "")]
)
def test_invalid_or_missing_evidence_fails_closed(sources: list[str], token: str) -> None:
    result = _run(sources=sources, token=token)
    assert result.returncode == 2
    assert "INCOMPLETE" in result.stderr
    _assert_secret_not_reported(result)


def test_one_missing_sink_invalidates_other_clean_sink(tmp_path: Path) -> None:
    clean = tmp_path / "clean.log"
    clean.write_text("status=200 route=export_ics\n")
    result = _run(sources=[str(clean), str(tmp_path / "unavailable.log")])
    assert result.returncode == 2
    assert "INCOMPLETE" in result.stderr
    _assert_secret_not_reported(result)


def test_a_leak_outranks_an_unreadable_sink(tmp_path: Path) -> None:
    leaking = tmp_path / "proxy.log"
    leaking.write_text(f"GET /api/v1/export/{TOKEN}/calendar.ics\n")
    result = _run(sources=[str(leaking), str(tmp_path / "unavailable.log")])
    assert result.returncode == 1
    assert "TOKEN FOUND" in result.stdout
    assert "INCOMPLETE" in result.stderr
    _assert_secret_not_reported(result)


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le", "utf-32"])
def test_utf16_and_utf32_exports_are_never_approved_as_clean(
    tmp_path: Path, encoding: str
) -> None:
    source = tmp_path / "proxy.log"
    source.write_bytes(f"GET /api/v1/export/{TOKEN}/calendar.ics\n".encode(encoding))
    result = _run(sources=[str(source)])
    assert result.returncode == 2
    assert "INCOMPLETE" in result.stderr
    _assert_secret_not_reported(result)


def test_gzip_log_export_is_never_approved_as_clean(tmp_path: Path) -> None:
    source = tmp_path / "proxy.jsonl.gz"
    source.write_bytes(gzip.compress(f"request={TOKEN}".encode()))
    result = _run(sources=[str(source)])
    assert result.returncode == 2
    assert "INCOMPLETE" in result.stderr
    _assert_secret_not_reported(result)


def test_gzip_magic_rejected_without_extension(tmp_path: Path) -> None:
    source = tmp_path / "proxy.log"
    source.write_bytes(gzip.compress(f"request={TOKEN}".encode()))
    result = _run(sources=[str(source)])
    assert result.returncode == 2
    _assert_secret_not_reported(result)


def test_misplaced_positional_secret_never_echoed(tmp_path: Path) -> None:
    source = tmp_path / "proxy.log"
    source.write_text("clear")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--source", str(source), TOKEN],
        input=TOKEN + "\n",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "INCOMPLETE" in result.stderr
    _assert_secret_not_reported(result)
