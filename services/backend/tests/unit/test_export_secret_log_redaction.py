# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Secret ICS export tokens must never reach logs, audit metadata or metrics (#603)."""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from app.adapters.api.access_metrics import route_template
from app.adapters.api.log_redaction import (
    RedactSecretPathsFilter,
    install_log_redaction,
    redact_secret_path,
)
from app.adapters.api.middleware.audit import AuditMiddleware
from app.adapters.api.middleware.rate_limit import RateLimitMiddleware
from app.application.audit_service import AuditContext
from app.application.rate_limiter import RateLimitResult

CANARY = "canary-TOKEN-9f3a7c1d"
FEED = f"/api/v1/export/{CANARY}/calendar.ics"


def _request(path: str = FEED, method: str = "GET") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": b"",
            "headers": [],
            "client": ("203.0.113.9", 1234),
        }
    )


@pytest.mark.parametrize(
    "path",
    [FEED, f"/api/v1/export/{CANARY}", f"/api/v1/export/{CANARY}/", f"{FEED}?x=1"],
)
def test_redacts_every_export_secret_shape(path: str) -> None:
    assert CANARY not in redact_secret_path(path)


def test_keeps_other_paths_untouched() -> None:
    for path in ("/api/v1/export-tokens", "/api/v1/events", "/api/v1/export-tokens/abc"):
        assert redact_secret_path(path) == path
    assert redact_secret_path(FEED) == "/api/v1/export/{redacted}/calendar.ics"


async def test_rate_limit_log_never_contains_the_token(caplog: pytest.LogCaptureFixture) -> None:
    middleware = RateLimitMiddleware(app=MagicMock(), rate_limiter=MagicMock())
    middleware.rate_limiter.get_rate_limit_headers = AsyncMock(return_value={})
    result = RateLimitResult(allowed=False, remaining=0, limit=1, reset_in=MagicMock())
    with caplog.at_level(logging.WARNING):
        await middleware._rate_limited_response(_request(), "ip:203.0.113.9", result, "normal")
    assert CANARY not in caplog.text
    assert "{redacted}" in caplog.text


@pytest.mark.parametrize("status_code", [200, 403, 404, 429, 500])
async def test_audit_metadata_never_contains_the_token(status_code: int) -> None:
    audit_service = MagicMock()
    audit_service.log = AsyncMock()
    middleware = AuditMiddleware(app=MagicMock(), audit_service=audit_service)
    response = MagicMock(status_code=status_code, headers={})
    context = AuditContext(user_sub=None, ip_address="203.0.113.9", user_agent="test")
    await middleware._log_audit_event(
        _request(), response, RuntimeError(f"boom {FEED}"), context, "req-1", 0.01
    )
    audit_service.log.assert_awaited_once()
    assert CANARY not in repr(audit_service.log.await_args)


def test_unmatched_route_metric_label_never_contains_the_token() -> None:
    assert CANARY not in route_template(_request())


def test_uvicorn_style_access_record_is_redacted() -> None:
    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 1,
        '%s - "%s %s HTTP/%s" %d', ("203.0.113.9:1234", "GET", FEED, "1.1", 200), None,
    )
    assert RedactSecretPathsFilter().filter(record) is True
    assert CANARY not in record.getMessage()


def _formatted(record: logging.LogRecord) -> str:
    """What a real handler writes: message plus traceback and stack info."""
    handler = logging.StreamHandler()
    handler.addFilter(RedactSecretPathsFilter())
    assert handler.filter(record)
    return handler.format(record)


def test_traceback_and_stack_info_are_redacted_in_the_final_output() -> None:
    try:
        raise RuntimeError(f"upstream failed for {FEED}")
    except RuntimeError:
        import sys

        record = logging.LogRecord(
            "app", logging.ERROR, __file__, 1, "Feed failed", None, sys.exc_info()
        )
    record.stack_info = f"Stack (most recent call last):\n  GET {FEED}"
    output = _formatted(record)
    assert CANARY not in output
    assert "{redacted}" in output
    assert "RuntimeError" in output  # the traceback itself is preserved


def test_logger_exception_with_the_url_in_the_message_is_redacted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = logging.getLogger("tests.redaction")
    handler = logging.StreamHandler()
    handler.addFilter(RedactSecretPathsFilter())
    stream = io.StringIO()
    handler.setStream(stream)
    logger.addHandler(handler)
    logger.propagate = False
    try:
        try:
            raise ValueError(FEED)
        except ValueError:
            logger.exception("request %s failed", FEED)
    finally:
        logger.removeHandler(handler)
        logger.propagate = True
    assert CANARY not in stream.getvalue()
    assert "ValueError" in stream.getvalue()


def test_installed_filter_covers_handlers_of_uvicorn_loggers() -> None:
    access = logging.getLogger("uvicorn.access")
    handler = logging.StreamHandler()
    access.addHandler(handler)
    try:
        install_log_redaction()
        install_log_redaction()  # idempotent
        assert sum(isinstance(f, RedactSecretPathsFilter) for f in handler.filters) == 1
    finally:
        access.removeHandler(handler)


def test_nginx_access_log_masks_the_export_secret() -> None:
    conf = (Path(__file__).parents[3] / "frontend" / "nginx.conf").read_text()
    assert re.search(r"log_format\s+\w+", conf)
    assert re.search(r"access_log\s+\S+\s+\w+", conf)
    assert "$request_uri" not in re.search(r"log_format[^;]+;", conf, re.S).group(0)
    assert "export" in conf.split("map $request_uri", 1)[1].split("}", 1)[0]
