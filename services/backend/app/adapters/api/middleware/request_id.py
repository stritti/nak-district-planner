# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Request correlation ID and access log (OpenSpec ``request-identity``, ``logging``).

Pure ASGI middleware, registered outermost so that every inner middleware, the
audit entry and the handlers see the same ``request_id``. ``X-Request-ID`` is
accepted only from a trusted proxy (the frontend nginx sets it from its own
``$request_id``) and only in a short, log-safe format: an oversized value would
not fit ``audit_logs.request_id`` and must never make the audit insert fail.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from urllib.parse import quote

from opentelemetry import trace
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.adapters.api.client_ip import is_trusted_proxy
from app.adapters.api.log_redaction import redact_secret_path
from app.logging_config import request_id_var

access_logger = logging.getLogger("app.access")

_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9-]{1,64}")
_QUIET_PATHS = frozenset({"/health", "/api/health"})


def resolve_request_id(scope: Scope) -> str:
    """Trusted, well-formed ``X-Request-ID`` or a fresh UUID."""
    client = scope.get("client")
    if is_trusted_proxy(client[0] if client else None):
        for name, value in scope.get("headers", ()):
            if name == b"x-request-id":
                candidate = value.decode("latin-1")
                if _VALID_REQUEST_ID.fullmatch(candidate):
                    return candidate
                break
    return str(uuid.uuid4())


class RequestIdMiddleware:
    """Bind ``request_id`` for the request and write one access-log record."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = resolve_request_id(scope)
        # Starlette's ServerErrorMiddleware runs outside this middleware; the
        # unhandled-exception handler reads the ID from request.state.
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_var.set(request_id)
        trace.get_current_span().set_attribute("request_id", request_id)

        status = 500
        start = time.perf_counter()

        async def send_with_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            self._log_access(scope, status, (time.perf_counter() - start) * 1000)
            request_id_var.reset(token)

    @staticmethod
    def _log_access(scope: Scope, status: int, duration_ms: float) -> None:
        # scope["path"] is URL-decoded: quote it again (as uvicorn's access log
        # does) so an encoded newline cannot forge extra log lines.
        path = quote(redact_secret_path(scope.get("path", "")), safe="/{}")
        # 5xx first: a failing health probe (database or Valkey down) must stay visible.
        if status >= 500:
            level = logging.ERROR
        elif path in _QUIET_PATHS or status == 429:
            level = logging.DEBUG
        else:
            level = logging.INFO
        if not access_logger.isEnabledFor(level):
            return
        method = scope.get("method", "")
        access_logger.log(
            level,
            '"%s %s HTTP/%s" %d %.1fms',
            method,
            path,
            scope.get("http_version", "1.1"),
            status,
            duration_ms,
            extra={
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": round(duration_ms, 1),
            },
        )
