# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Request correlation ID and access log (OpenSpec ``request-identity``, ``logging``)."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import ClassVar

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from starlette.testclient import TestClient

from app.adapters.api.middleware import request_id as request_id_module
from app.adapters.api.middleware.audit import AuditMiddleware
from app.adapters.api.middleware.request_id import RequestIdMiddleware, resolve_request_id
from app.logging_config import ContextFilter, current_request_id, request_id_var

NGINX_PEER = ("172.18.0.5", 40000)
UNTRUSTED_PEER = ("203.0.113.9", 40000)
TOKEN = "s3cr3t-export-token-value"


@pytest.fixture(autouse=True)
def _context_filter(caplog):
    """What setup_logging installs on the real handler."""
    caplog.handler.addFilter(ContextFilter())


def _scope(peer, headers: dict[str, str]) -> dict:
    return {
        "type": "http",
        "client": peer,
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


# ----------------------------------------------------------------- resolution


def test_trusted_proxy_id_is_used() -> None:
    nginx_id = "0f3c9a6b2d8e4f1a9c7b5d3e1f2a4b6c"  # nginx $request_id: 32 hex chars
    assert resolve_request_id(_scope(NGINX_PEER, {"X-Request-ID": nginx_id})) == nginx_id


def test_untrusted_peer_gets_fresh_uuid() -> None:
    value = resolve_request_id(_scope(UNTRUSTED_PEER, {"X-Request-ID": "attacker-chosen"}))
    assert value != "attacker-chosen" and _is_uuid(value)


@pytest.mark.parametrize(
    "header",
    ["a" * 65, "abc\ndef", 'abc"def', "abc def", "abc;def", ""],
)
def test_malformed_or_oversized_id_from_trusted_peer_is_replaced(header: str) -> None:
    value = resolve_request_id(_scope(NGINX_PEER, {"X-Request-ID": header}))
    assert value != header and _is_uuid(value)


def test_missing_header_and_missing_peer_get_uuid() -> None:
    assert _is_uuid(resolve_request_id(_scope(NGINX_PEER, {})))
    assert _is_uuid(resolve_request_id(_scope(None, {"X-Request-ID": "abc"})))


# ----------------------------------------------------------------- middleware


def _app() -> FastAPI:
    app = FastAPI()
    seen: dict[str, str | None] = {}

    @app.get("/api/v1/events")
    async def events() -> dict:
        seen["handler"] = current_request_id()
        logging.getLogger("app.handler").error("handler failed")
        return {"ok": True}

    @app.get("/api/v1/export/{token}/calendar.ics")
    async def feed(token: str) -> dict:
        return {"ok": True}

    @app.get("/api/health")
    async def health() -> dict:
        return {"ok": True}

    @app.get("/health")
    async def health_down() -> JSONResponse:
        return JSONResponse({"db": "unavailable"}, status_code=503)

    @app.get("/limited")
    async def limited() -> JSONResponse:
        return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)

    @app.get("/denied")
    async def denied() -> None:
        raise HTTPException(status_code=403, detail="no")

    @app.get("/state")
    async def state(request: Request) -> dict:
        return {"id": request.state.request_id}

    app.add_middleware(RequestIdMiddleware)
    app.state.seen = seen
    return app


def _access(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "app.access"]


def test_handler_logs_and_access_line_share_the_request_id(caplog) -> None:
    app = _app()
    caplog.set_level(logging.DEBUG)
    with TestClient(app, client=NGINX_PEER) as client:
        response = client.get("/api/v1/events", headers={"X-Request-ID": "nginx-1"})
    assert response.status_code == 200
    assert app.state.seen["handler"] == "nginx-1"
    (handler_record,) = [r for r in caplog.records if r.name == "app.handler"]
    assert handler_record.request_id == "nginx-1"
    (access,) = _access(caplog)
    assert access.levelno == logging.INFO
    assert access.request_id == "nginx-1"
    assert (access.method, access.path, access.status) == ("GET", "/api/v1/events", 200)
    assert isinstance(access.duration_ms, float)
    assert access.getMessage().startswith('"GET /api/v1/events HTTP/1.1" 200 ')
    assert request_id_var.get() is None  # no leak after the request


def test_request_state_carries_the_id_for_the_error_handler() -> None:
    with TestClient(_app(), client=NGINX_PEER) as client:
        assert client.get("/state", headers={"X-Request-ID": "abc"}).json() == {"id": "abc"}


def test_access_line_has_redacted_path_without_query(caplog) -> None:
    caplog.set_level(logging.INFO)
    with TestClient(_app(), client=UNTRUSTED_PEER) as client:
        client.get(f"/api/v1/export/{TOKEN}/calendar.ics?x=1")
    (access,) = _access(caplog)
    assert TOKEN not in access.getMessage()
    assert access.path == "/api/v1/export/{redacted}/calendar.ics"
    assert "?" not in access.getMessage()


def test_encoded_control_characters_cannot_forge_log_lines(caplog) -> None:
    caplog.set_level(logging.INFO)
    with TestClient(_app(), client=UNTRUSTED_PEER) as client:
        client.get("/api/not-found%0AERROR%20forged-entry%0D")
    (access,) = _access(caplog)
    assert "\n" not in access.getMessage() and "\r" not in access.getMessage()
    assert access.path == "/api/not-found%0AERROR%20forged-entry%0D"


@pytest.mark.parametrize("path", ["/api/health", "/limited"])
def test_health_and_rate_limited_requests_stay_off_info(caplog, path: str) -> None:
    caplog.set_level(logging.DEBUG)
    with TestClient(_app(), client=NGINX_PEER) as client:
        client.get(path)
    (access,) = _access(caplog)
    assert access.levelno == logging.DEBUG


def test_failing_health_probe_is_logged_as_error(caplog) -> None:
    caplog.set_level(logging.INFO)
    with TestClient(_app(), client=NGINX_PEER) as client:
        assert client.get("/health").status_code == 503
    (access,) = _access(caplog)
    assert access.levelno == logging.ERROR


def test_access_log_skipped_when_level_disabled(caplog) -> None:
    caplog.set_level(logging.WARNING)
    with TestClient(_app(), client=NGINX_PEER) as client:
        client.get("/api/v1/events")
    assert _access(caplog) == []


def test_unhandled_exception_is_logged_with_status_500(caplog) -> None:
    app = FastAPI()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    app.add_middleware(RequestIdMiddleware)
    caplog.set_level(logging.INFO)
    with TestClient(app, client=NGINX_PEER, raise_server_exceptions=False) as client:
        assert client.get("/boom").status_code == 500
    (access,) = _access(caplog)
    assert access.status == 500
    assert access.levelno == logging.ERROR


async def test_non_http_scope_passes_through() -> None:
    called = []

    async def inner(scope, receive, send) -> None:
        called.append(scope["type"])

    await RequestIdMiddleware(inner)({"type": "lifespan"}, None, None)
    assert called == ["lifespan"]


def test_request_id_is_set_as_span_attribute(monkeypatch) -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")

    async def inner(scope, receive, send) -> None:
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestIdMiddleware(inner)

    async def run() -> None:
        async def send(_message) -> None:
            return None

        scope = {**_scope(NGINX_PEER, {"X-Request-ID": "span-1"}), "method": "GET", "path": "/"}
        with tracer.start_as_current_span("server"):
            await middleware(scope, None, send)

    import asyncio

    asyncio.run(run())
    (span,) = exporter.get_finished_spans()
    assert span.attributes["request_id"] == "span-1"
    assert trace.get_current_span() is not None


# ----------------------------------------------------------------- audit


class _CapturingAudit(AuditMiddleware):
    contexts: ClassVar[list] = []

    async def _log_audit_event(self, request, response, error, context, request_id, duration):
        type(self).contexts.append((context.request_id, request_id))
        return True


def test_denied_request_audit_uses_the_same_request_id(caplog) -> None:
    _CapturingAudit.contexts = []
    app = _app()
    app.user_middleware.clear()
    app.add_middleware(_CapturingAudit, exempt_paths={"/api/health"})
    app.add_middleware(RequestIdMiddleware)
    caplog.set_level(logging.INFO)
    with TestClient(app, client=NGINX_PEER) as client:
        assert client.get("/denied", headers={"X-Request-ID": "deny-1"}).status_code == 403
    assert _CapturingAudit.contexts == [("deny-1", "deny-1")]
    (access,) = _access(caplog)
    assert access.request_id == "deny-1"


def test_oversized_trusted_id_still_audits_and_answers(caplog) -> None:
    _CapturingAudit.contexts = []
    app = _app()
    app.user_middleware.clear()
    app.add_middleware(_CapturingAudit, exempt_paths={"/api/health"})
    app.add_middleware(RequestIdMiddleware)
    with TestClient(app, client=NGINX_PEER) as client:
        assert client.get("/denied", headers={"X-Request-ID": "x" * 500}).status_code == 403
    ((stored, _),) = _CapturingAudit.contexts
    assert _is_uuid(stored) and len(stored) <= 100


def test_audit_middleware_generates_id_without_request_id_middleware() -> None:
    _CapturingAudit.contexts = []
    app = _app()
    app.user_middleware.clear()
    app.add_middleware(_CapturingAudit, exempt_paths={"/api/health"})
    with TestClient(app, client=NGINX_PEER) as client:
        client.get("/denied", headers={"X-Request-ID": "ignored"})
    ((stored, _),) = _CapturingAudit.contexts
    assert _is_uuid(stored)


def test_main_registers_request_id_middleware_outermost() -> None:
    from app import main

    assert main.app.user_middleware[0].cls is RequestIdMiddleware
    assert request_id_module.access_logger.name == "app.access"


# ----------------------------------------------------------------- nginx


def test_frontend_nginx_overwrites_x_request_id_on_every_backend_location() -> None:
    conf = (Path(__file__).parents[3] / "frontend" / "nginx.conf").read_text()
    proxies = conf.count("proxy_pass $backend_upstream")
    assert proxies >= 3
    assert conf.count("proxy_set_header X-Request-ID $request_id;") == proxies
