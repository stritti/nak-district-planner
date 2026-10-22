# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Audit Logging Middleware for FastAPI.

This middleware automatically logs audit events for all requests.
"""

import logging
import re
import time
import uuid
from datetime import UTC, datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_403_FORBIDDEN, HTTP_503_SERVICE_UNAVAILABLE

from app.adapters.api.access_metrics import record_access_denied
from app.adapters.api.client_ip import get_client_ip
from app.adapters.api.log_redaction import redact_secret_path
from app.adapters.db.repositories.audit_log import SqlAuditLogRepository
from app.application.audit_service import (
    AuditAction,
    AuditContext,
    AuditPersistenceError,
    AuditStatus,
    audit_service,
    audit_write_failures,
)
from app.audit_request import begin_request_audit, end_request_audit
from app.domain.models.audit_log import AuditLogCreate

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware for automatic audit logging.

    Registered via ``app.add_middleware()`` — Starlette instantiates it
    as ASGI middleware and calls ``dispatch(request, call_next)`` for
    each request.

    This middleware:
    - Generates a unique request ID for each request
    - Tracks request start time
    - Logs audit events for denied and failed requests synchronously, before the
      response is returned; if the entry cannot be persisted the response is 503
    - Lets a successful state-changing request carry its entry in its own
      transaction (see ``app.audit_request``) and writes it here only when no
      transaction did
    """

    def __init__(
        self,
        app,
        audit_service=audit_service,
        exempt_paths: set[str] | None = None,
        exempt_methods: set[str] | None = None,
    ):
        """Initialize the audit middleware.

        Args:
            app: FastAPI application instance.
            audit_service: Audit service instance.
            exempt_paths: Set of paths to exempt from audit logging.
            exempt_methods: Set of HTTP methods to exempt.
        """
        super().__init__(app)
        self.audit_service = audit_service
        self.exempt_paths = exempt_paths or {"/api/health"}
        self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS"}

    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        """Process a request through the middleware.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.

        Returns:
            HTTP response.
        """
        # Generate request ID
        request_id = str(uuid.uuid4())

        # Track start time
        start_time = time.time()

        # Extract pre-call information available before deps run
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent")

        # A successful write is audited inside its own transaction (before the commit)
        # unless its domain audit already is; the session dependency calls this hook.
        state = begin_request_audit()
        if self._is_state_changing(request):

            async def transaction_entry(session) -> None:
                context = self._extract_context(
                    request, request_id, ip_address=ip_address, user_agent=user_agent
                )
                await self._insert_in_transaction(session, request, context)

            state.transaction_entry = transaction_entry

        response = None
        error = None
        try:
            response = await call_next(request)
        except Exception as e:
            error = e
        finally:
            end_request_audit()

        duration = time.time() - start_time

        # NOTE: context is extracted *after call_next* so FastAPI dependency
        # resolution (get_current_user etc.) has already populated
        # request.state.user before we read it.
        if self._should_log_audit(request, response) and not (
            error is None and not _is_failure(response) and state.covered
        ):
            context = self._extract_context(
                request, request_id, ip_address=ip_address, user_agent=user_agent
            )
            if not await self._log_audit_event(
                request, response, error, context, request_id, duration
            ):
                # Never hand out an unaudited decision or result.
                return JSONResponse(
                    {"detail": "Audit-Protokollierung nicht verfügbar"},
                    status_code=HTTP_503_SERVICE_UNAVAILABLE,
                )

        if error is not None:
            raise error
        return response

    def _is_state_changing(self, request: Request) -> bool:
        return (
            request.url.path not in self.exempt_paths
            and request.method not in self.exempt_methods
        )

    async def _insert_in_transaction(
        self, session, request: Request, context: AuditContext
    ) -> None:
        """Insert the entry of a successful write into the transaction about to commit.

        The entry commits exactly when the change does. Row-level security would
        reject it for routes without a tenant, so the system-worker context is set
        for this single insert and cleared right after.
        """
        from sqlalchemy import text

        entry = self._build_entry(
            request, None, None, context, duration=None, status=AuditStatus.SUCCESS
        )
        await session.execute(text("SELECT set_config('app.is_system_worker', 'true', true)"))
        try:
            await SqlAuditLogRepository(session).create(entry)
        finally:
            await session.execute(text("SELECT set_config('app.is_system_worker', '', true)"))

    def _extract_context(
        self,
        request: Request,
        request_id: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditContext:
        """Extract audit context from request.

        Called *after* await call_next(request) so that FastAPI
        dependency resolution (get_current_user etc.) has already
        populated request.state.user before we read it.

        Args:
            request: HTTP request.
            request_id: Unique request ID.
            ip_address: Pre-extracted client IP (optional).
            user_agent: Pre-extracted user-agent (optional).

        Returns:
            AuditContext with extracted information.
        """
        # Extract user information from request state
        user_sub = None
        user_email = None
        user_roles = None

        if hasattr(request.state, "user"):
            user = request.state.user
            if user:
                user_sub = getattr(user, "sub", None)
                user_email = getattr(user, "email", None)

        # Extract roles from request state
        if hasattr(request.state, "user_roles"):
            user_roles = request.state.user_roles

        # Extract tenant context from path params (populated by FastAPI routing).
        # Requests rejected by TenantValidationMiddleware never reach routing;
        # fall back to the tenant the TenantMiddleware parsed from the path.
        path_params = getattr(request, "path_params", {}) or {}
        tenant_context = getattr(request.state, "tenant_context", None) or {}
        district_id = path_params.get(
            "district_id",
            getattr(request.state, "district_id", None) or tenant_context.get("district_id"),
        )
        congregation_id = path_params.get(
            "congregation_id",
            getattr(request.state, "congregation_id", None)
            or tenant_context.get("congregation_id"),
        )

        # Extract request information (or use pre-extracted values)
        if ip_address is None:
            ip_address = self._get_client_ip(request)
        if user_agent is None:
            user_agent = request.headers.get("user-agent")

        return AuditContext(
            user_sub=user_sub,
            user_email=user_email,
            user_roles=user_roles,
            district_id=district_id,
            congregation_id=congregation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    def _get_client_ip(self, request: Request) -> str | None:
        """Return the client IP via the shared trusted-proxy resolution."""
        return get_client_ip(request)

    def _should_log_audit(self, request: Request, response: Response | None = None) -> bool:
        """Determine if this request should be audit logged.

        Denied requests are logged for every method: a rejected read of another
        tenant's data is exactly what the audit trail must show.

        Args:
            request: HTTP request.
            response: HTTP response, if the request completed.

        Returns:
            True if request should be audit logged.
        """
        # Skip exempt paths
        if request.url.path in self.exempt_paths:
            return False

        if _is_denied(response):
            return True

        # Skip exempt methods
        if request.method in self.exempt_methods:
            return False

        return True

    def _build_entry(
        self,
        request: Request,
        response: Response | None,
        error: Exception | None,
        context: AuditContext,
        *,
        duration: float | None,
        status: AuditStatus | None = None,
    ) -> AuditLogCreate:
        """Describe the request as an audit entry (no body, no secrets, redacted path)."""
        if _is_denied(response):
            action = AuditAction.ACCESS_DENIED
        else:
            action = self._get_action_from_method(request.method, request.url.path)

        resource_type = self._get_resource_type(request.url.path)

        if status is None:
            # FAILED for exceptions and non-2xx/3xx responses
            status = AuditStatus.SUCCESS
            if error or (response and response.status_code >= 400):
                status = AuditStatus.FAILED
        error_message = (
            redact_secret_path(str(error))
            if error
            else (
                f"HTTP {response.status_code}"
                if response and response.status_code >= 400
                else None
            )
        )

        resource_id = self._extract_resource_id(request.url.path)
        # For CREATE responses with no path UUID, try Location header
        if resource_id is None and action == AuditAction.CREATE and response:
            location = response.headers.get("Location")
            if location:
                resource_id = self._extract_resource_id(location)

        metadata = {
            "http_method": request.method,
            "path": redact_secret_path(request.url.path),
            "user_agent": context.user_agent,
        }
        if response is not None or error is not None:
            metadata["status_code"] = response.status_code if response else None
        if duration is not None:
            metadata["duration_ms"] = round(duration * 1000, 2)
        return AuditLogCreate(
            timestamp=datetime.now(UTC),
            user_sub=context.user_sub,
            user_email=context.user_email,
            user_roles=context.user_roles,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            district_id=context.district_id,
            congregation_id=context.congregation_id,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            request_id=context.request_id,
            status=status,
            error_message=error_message,
            extra_metadata=metadata,
        )

    async def _log_audit_event(
        self,
        request: Request,
        response: Response | None,
        error: Exception | None,
        context: AuditContext,
        request_id: str,
        duration: float,
    ) -> bool:
        """Persist the audit entry of the request; ``False`` when that failed."""
        try:
            if _is_denied(response):
                record_access_denied(request)
            entry = self._build_entry(request, response, error, context, duration=duration)
            await self.audit_service.record(entry)
            return True
        except AuditPersistenceError:
            return False  # counted and logged by the service; the caller answers with 503
        except Exception as e:
            # The entry could not even be built: counted like a persistence failure.
            logger.error("Failed to build audit event (%s)", type(e).__name__)
            audit_write_failures.add(1, {"stage": "build"})
            return False

    def _get_action_from_method(self, method: str, path: str = "") -> AuditAction:
        """Map HTTP method to audit action.

        Args:
            method: HTTP method.
            path: Request URL path (used to detect command-style POST routes).

        Returns:
            Corresponding AuditAction.
        """
        method_upper = method.upper()

        if method_upper == "POST":
            if path and self._is_command_action(path):
                return AuditAction.UPDATE
            return AuditAction.CREATE
        elif method_upper == "PUT":
            return AuditAction.UPDATE
        elif method_upper == "PATCH":
            return AuditAction.UPDATE
        elif method_upper == "DELETE":
            return AuditAction.DELETE
        else:
            return AuditAction.UPDATE

    @staticmethod
    def _is_command_action(path: str) -> bool:
        """Detect if a POST route is a command-style action, not a resource create.

        Command-style POST routes (e.g. ``POST /api/v1/events/bulk-approval-status``)
        update existing resources rather than creating new ones.  Detection heuristic:
        if the last path segment is neither a known collection name nor a UUID,
        treat it as a command action.

        Args:
            path: Request URL path.

        Returns:
            True if the route is a command action.
        """
        clean = path.rstrip("/")
        last_segment = clean.split("/")[-1] if "/" in clean else clean

        # UUID-pattern segment → resource parameter, not a command
        if re.search(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", last_segment
        ):
            return False

        # Known collection names → resource create, not a command
        resource_names = {
            "events",
            "districts",
            "congregations",
            "leaders",
            "invitations",
            "service-assignments",
            "calendar-integrations",
            "memberships",
            "users",
            "export",
            "auth",
            "oidc",
            "token",
            "discovery",
        }
        if last_segment in resource_names:
            return False

        # Anything else (hyphenated or multi-word segment) → command-style action
        return True

    def _get_resource_type(self, path: str) -> str:
        """Extract resource type from URL path.

        For nested resource routes (e.g. ``/api/v1/events/{id}/assignments/{aid}``)
        the segment *before* the last UUID-parameter is used so the audit entry
        references the innermost resource type (e.g. ``assignments`` rather than
        ``events``).

        Args:
            path: URL path.

        Returns:
            Resource type string.
        """
        # Remove leading slash and version prefix
        clean_path = path.lstrip("/")
        if clean_path.startswith("api/v1/"):
            clean_path = clean_path[7:]  # Remove "api/v1/"

        parts = clean_path.split("/")

        # For nested resource routes, find the segment before the last UUID
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        for i in range(len(parts) - 1, 0, -1):
            if re.match(uuid_pattern, parts[i]):
                return parts[i - 1]

        if parts:
            return parts[0]

        return "unknown"

    def _extract_resource_id(self, path: str) -> uuid.UUID | None:
        """Extract resource ID from URL path if available.

        For nested resource routes (e.g. ``/api/v1/districts/{d}/congregations/{c}``)
        the *last* UUID in the path is used so the audit entry references the
        most specific (innermost) resource.

        Args:
            path: URL path.

        Returns:
            Resource ID as UUID, or None if not found.
        """
        # Look for UUID patterns in the path — use *last* match for nested routes
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        matches = re.findall(uuid_pattern, path)

        if matches:
            try:
                return uuid.UUID(matches[-1])
            except ValueError:
                logger.debug("Ignoring invalid UUID %r in audit path %r", matches[-1], path)

        return None


def _is_failure(response: Response | None) -> bool:
    return response is not None and response.status_code >= 400


def _is_denied(response: Response | None) -> bool:
    return response is not None and response.status_code == HTTP_403_FORBIDDEN
