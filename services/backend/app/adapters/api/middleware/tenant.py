"""Tenant routing context middleware for FastAPI.

Tenant routing information may be derived from request paths, query parameters,
or explicit tenant headers. User identity is security-sensitive and therefore
only comes from a previously verified principal on request state. Bearer
payloads are never decoded in middleware for authorization decisions.

Authorization itself belongs to authenticated FastAPI dependencies/application
RBAC and PostgreSQL RLS. ASGI middleware runs before those dependencies and must
not pretend to make user/tenant authorization decisions from unverified data.
"""

import logging
import re
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.tenant import TenantContext

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract non-authentication tenant routing context from a request."""

    UUID_PATTERN = re.compile(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )

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

    @classmethod
    def _extract_tenant_from_path(cls, path: str, context: dict) -> None:
        clean = path.lstrip("/")
        if clean.startswith("api/v1/"):
            clean = clean[7:]
        parts = clean.split("/")

        for index, part in enumerate(parts):
            if index + 1 >= len(parts):
                continue
            candidate = parts[index + 1]
            if cls.UUID_PATTERN.fullmatch(candidate) is None:
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
