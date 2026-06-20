"""Tenant Isolation Middleware for FastAPI.

This middleware extracts tenant context from requests and enforces tenant isolation.
"""

import logging
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.tenant import TenantContext

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware for tenant isolation.
    
    Registered via ``app.add_middleware()`` — Starlette calls
    ``dispatch(request, call_next)`` for each request.

    This middleware:
    - Extracts tenant context from request (district, congregation, user)
    - Sets tenant context variables for use by other components
    - Adds tenant information to request state
    """

    def __init__(
        self,
        app,
        exempt_paths: set[str] | None = None,
        exempt_methods: set[str] | None = None,
    ):
        """Initialize the tenant middleware.
        
        Args:
            app: FastAPI application instance.
            exempt_paths: Set of paths to exempt from tenant context extraction.
            exempt_methods: Set of HTTP methods to exempt.
        """
        super().__init__(app)
        self.exempt_paths = exempt_paths or {"/api/health"}
        self.exempt_methods = exempt_methods or {"OPTIONS"}

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
        # Skip for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Skip for exempt methods
        if request.method in self.exempt_methods:
            return await call_next(request)
        
        # Extract tenant context from request
        tenant_context = self._extract_tenant_context(request)
        
        # Set tenant context variables
        TenantContext.set_context(
            tenant_id=tenant_context.get("tenant_id"),
            district_id=tenant_context.get("district_id"),
            congregation_id=tenant_context.get("congregation_id"),
            user_sub=tenant_context.get("user_sub"),
            user_roles=tenant_context.get("user_roles"),
        )
        
        # Add tenant context to request state
        request.state.tenant_context = tenant_context
        
        # Process request
        response = await call_next(request)
        
        # Clear tenant context after request
        TenantContext.clear_context()
        
        return response

    def _extract_tenant_context(self, request: Request) -> dict:
        """Extract tenant context from request.
        
        Since this runs as ASGI middleware before FastAPI dependencies,
        ``request.state.user`` is normally not populated yet.  The method
        first tries ``request.state.user`` (for cases where an outer
        middleware or route has already resolved), then falls back to
        extracting the ``sub`` claim directly from the Bearer JWT payload
        without verifying the signature — safe because the value is used
        only for tenant-context extraction, not authentication.
        
        Args:
            request: HTTP request.
            
        Returns:
            Dictionary with tenant context information.
        """
        context = {}
        
        # Extract user information (may not be populated yet — middleware runs before deps)
        user_sub = None
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            user_sub = getattr(user, "sub", None)
            context["user_email"] = getattr(user, "email", None)
        
        # Fallback: extract sub from Bearer JWT payload
        if not user_sub:
            user_sub = self._extract_sub_from_bearer(request)
        
        context["user_sub"] = user_sub
        
        # Extract user roles
        if hasattr(request.state, "user_roles"):
            context["user_roles"] = request.state.user_roles
        
        # Try to extract tenant from path parameters
        path_params = getattr(request, "path_params", {})
        if "district_id" in path_params:
            context["district_id"] = path_params["district_id"]
            context["tenant_id"] = path_params["district_id"]
            context["tenant_type"] = "district"
        elif "congregation_id" in path_params:
            context["congregation_id"] = path_params["congregation_id"]
            context["tenant_id"] = path_params["congregation_id"]
            context["tenant_type"] = "congregation"
        
        # Try to extract tenant from query parameters
        query_params = getattr(request, "query_params", {})
        if "district_id" in query_params:
            context["district_id"] = query_params["district_id"]
        if "congregation_id" in query_params:
            context["congregation_id"] = query_params["congregation_id"]
        
        # Try to extract tenant from headers
        district_id = request.headers.get("X-District-ID")
        if district_id:
            try:
                context["district_id"] = uuid.UUID(district_id)
                context["tenant_id"] = context["district_id"]
                context["tenant_type"] = "district"
            except ValueError:
                logger.warning(f"Invalid district ID in header: {district_id}")
        
        congregation_id = request.headers.get("X-Congregation-ID")
        if congregation_id:
            try:
                context["congregation_id"] = uuid.UUID(congregation_id)
                context["tenant_id"] = context["congregation_id"]
                context["tenant_type"] = "congregation"
            except ValueError:
                logger.warning(f"Invalid congregation ID in header: {congregation_id}")
        
        return context

    @staticmethod
    def _extract_sub_from_bearer(request: Request) -> str | None:
        """Extract the ``sub`` claim from a Bearer JWT without verification.
        
        Safe because the extracted value is used only for tenant-context
        grouping, not authentication. Full token verification happens in
        the route dependency.
        
        Args:
            request: HTTP request.
            
        Returns:
            User subject string, or None if not extractable.
        """
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return None
        
        import base64
        import json
        
        try:
            token = auth_header[7:]
            payload_b64 = token.split(".")[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return payload.get("sub")
        except (IndexError, ValueError, json.JSONDecodeError):
            return None


class TenantValidationMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware for tenant validation.
    
    Registered via ``app.add_middleware()`` — Starlette calls
    ``dispatch(request, call_next)`` for each request.

    This middleware validates that authenticated users have access to
    the requested tenant resources by calling ``TenantValidationService``.
    """

    def __init__(
        self,
        app,
        exempt_paths: set[str] | None = None,
        exempt_methods: set[str] | None = None,
    ):
        """Initialize the tenant validation middleware.
        
        Args:
            app: FastAPI application instance.
            exempt_paths: Set of paths to exempt from validation.
            exempt_methods: Set of HTTP methods to exempt.
        """
        super().__init__(app)
        self.exempt_paths = exempt_paths or {"/api/health", "/api/v1/auth"}
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
        # Skip validation for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Skip validation for exempt methods
        if request.method in self.exempt_methods:
            return await call_next(request)
        
        # Skip validation for unauthenticated requests
        if not self._is_authenticated(request):
            return await call_next(request)
        
        # Get tenant context from request
        tenant_context = getattr(request.state, "tenant_context", {})
        
        # If no tenant context, allow request (will be validated at service level)
        if not tenant_context:
            return await call_next(request)
        
        user_sub = tenant_context.get("user_sub")
        tenant_id = tenant_context.get("tenant_id")
        tenant_type = tenant_context.get("tenant_type")
        
        # Only validate when we have both user and tenant context
        if user_sub and tenant_id and tenant_type:
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
                        tenant_id=(
                            uuid.UUID(tenant_id)
                            if isinstance(tenant_id, str)
                            else tenant_id
                        ),
                        tenant_type=tenant_type,
                    )
                except TenantValidationError as e:
                    logger.warning(
                        "Tenant validation denied: user=%s tenant=%s type=%s: %s",
                        user_sub,
                        tenant_id,
                        tenant_type,
                        e,
                    )
                    from starlette.responses import JSONResponse
                    from starlette.status import HTTP_403_FORBIDDEN
                    return JSONResponse(
                        status_code=HTTP_403_FORBIDDEN,
                        content={"detail": str(e)},
                    )
        
        return await call_next(request)

    def _is_authenticated(self, request: Request) -> bool:
        """Check if request is authenticated.
        
        Args:
            request: HTTP request.
            
        Returns:
            True if user is authenticated.
        """
        if hasattr(request.state, "user") and request.state.user:
            return True
        
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            return True
        
        return False
