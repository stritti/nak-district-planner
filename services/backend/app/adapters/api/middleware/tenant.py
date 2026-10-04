"""Tenant isolation middleware for FastAPI.

Tenant routing information may be derived from request paths, query parameters,
or explicit tenant headers. User identity is different: it is security-sensitive
and therefore only comes from a previously verified principal on request state.
Bearer payloads are never decoded in middleware for authorization decisions.
"""

import logging
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_403_FORBIDDEN

from app.tenant import TenantContext

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract non-authentication tenant routing context from a request."""

    UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def __init__(
        self,
        app,
        exempt_paths: set[str] | None = None,
        exempt_methods: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.exempt_paths = exempt_paths or {"/api/health"}
        self.exempt_methods = exempt_methods or {"OPTIONS"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.exempt_paths or request.method in self.exempt_methods:
            return await call_next(request)

        tenant_context = self._extract_tenant_context(request)
        verified_sub = self._verified_sub(request)
        if verified_sub:
            tenant_context["user_sub"] = verified_sub

        TenantContext.set_context(
            tenant_id=tenant_context.get("tenant_id"),
            district_id=tenant_context.get("district_id"),
            congregation_id=tenant_context.get("congregation_id"),
            user_sub=verified_sub,
            user_roles=tenant_context.get("user_roles"),
        )
        request.state.tenant_context = tenant_context

        try:
            return await call_next(request)
        finally:
            TenantContext.clear_context()

    @staticmethod
    def _verified_sub(request: Request) -> str | None:
        """Return a subject only when an authentication layer verified it."""
        user = getattr(request.state, "user", None)
        if not user:
            return None
        sub = getattr(user, "sub", None)
        return sub if isinstance(sub, str) and sub else None

    def _extract_tenant_context(self, request: Request) -> dict:
        """Extract tenant routing data without interpreting bearer credentials."""
        context: dict = {}

        user = getattr(request.state, "user", None)
        if user:
            context["user_email"] = getattr(user, "email", None)
        if hasattr(request.state, "user_roles"):
            context["user_roles"] = request.state.user_roles

        self._extract_tenant_from_path(request.url.path, context)

        query_params = getattr(request, "query_params", {})
        if "district_id" in query_params:
            self._set_uuid_context(context, "district_id", query_params["district_id"], "district")
        if "congregation_id" in query_params:
            self._set_uuid_context(
                context,
                "congregation_id",
                query_params["congregation_id"],
                "congregation",
                prefer_existing_tenant=True,
            )

        district_id = request.headers.get("X-District-ID")
        if district_id:
            self._set_uuid_context(context, "district_id", district_id, "district")

        congregation_id = request.headers.get("X-Congregation-ID")
        if congregation_id:
            self._set_uuid_context(
                context,
                "congregation_id",
                congregation_id,
                "congregation",
                prefer_existing_tenant=True,
            )

        return context

    @staticmethod
    def _set_uuid_context(
        context: dict,
        field: str,
        raw_value: object,
        tenant_type: str,
        *,
        prefer_existing_tenant: bool = False,
    ) -> None:
        try:
            value = raw_value if isinstance(raw_value, uuid.UUID) else uuid.UUID(str(raw_value))
        except (ValueError, TypeError, AttributeError):
            logger.warning("Invalid %s value: %s", field, raw_value)
            return

        context[field] = value
        if not prefer_existing_tenant or "tenant_id" not in context:
            context["tenant_id"] = value
            context["tenant_type"] = tenant_type

    @staticmethod
    def _extract_tenant_from_path(path: str, context: dict) -> None:
        import re

        clean = path.lstrip("/")
        if clean.startswith("api/v1/"):
            clean = clean[7:]
        parts = clean.split("/")

        for index, part in enumerate(parts):
            if index + 1 >= len(parts):
                continue
            candidate = parts[index + 1]
            match = re.fullmatch(TenantMiddleware.UUID_PATTERN, candidate)
            if not match:
                continue

            if part == "districts":
                district_id = uuid.UUID(candidate)
                context["district_id"] = district_id
                context["tenant_id"] = district_id
                context["tenant_type"] = "district"
            elif part == "congregations":
                congregation_id = uuid.UUID(candidate)
                context["congregation_id"] = congregation_id
                if "tenant_id" not in context:
                    context["tenant_id"] = congregation_id
                    context["tenant_type"] = "congregation"


class TenantValidationMiddleware(BaseHTTPMiddleware):
    """Pre-validate tenant access only when a verified principal is available.

    FastAPI dependencies normally perform authentication after ASGI middleware.
    In that common case this middleware deliberately defers authorization to the
    route/application RBAC checks and PostgreSQL RLS rather than trusting an
    unverified bearer payload.
    """

    def __init__(
        self,
        app,
        exempt_paths: set[str] | None = None,
        exempt_methods: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.exempt_paths = exempt_paths or {"/api/health", "/api/v1/auth"}
        self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        if request.method in self.exempt_methods:
            return await call_next(request)

        user = getattr(request.state, "user", None)
        user_sub = getattr(user, "sub", None) if user else None
        if not isinstance(user_sub, str) or not user_sub:
            return await call_next(request)

        tenant_context = getattr(request.state, "tenant_context", {})
        tenant_id = tenant_context.get("tenant_id")
        tenant_type = tenant_context.get("tenant_type")
        if not tenant_id or not tenant_type:
            return await call_next(request)

        from app.adapters.db.session import AsyncSessionLocal
        from app.application.tenant_validation import (
            TenantValidationError,
            TenantValidationService,
        )

        async with AsyncSessionLocal() as session:
            validation_service = TenantValidationService(session)
            try:
                await validation_service.validate_user_in_tenant(
                    user_sub=user_sub,
                    tenant_id=(uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id),
                    tenant_type=tenant_type,
                )
            except TenantValidationError as exc:
                logger.warning(
                    "Tenant validation denied for verified user=%s tenant=%s type=%s: %s",
                    user_sub,
                    tenant_id,
                    tenant_type,
                    exc,
                )
                return JSONResponse(
                    status_code=HTTP_403_FORBIDDEN,
                    content={"detail": str(exc)},
                )

        return await call_next(request)
