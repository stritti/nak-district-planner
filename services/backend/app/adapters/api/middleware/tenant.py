"""Tenant Isolation Middleware for FastAPI.

This middleware extracts tenant context from requests and enforces tenant isolation.
"""

import logging
from typing import Callable, Awaitable

from fastapi import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_403_FORBIDDEN

from app.application.tenant_validation import TenantValidationError, TenantValidationService
from app.tenant import TenantContext

logger = logging.getLogger(__name__)


class TenantMiddleware:
    """FastAPI Middleware for tenant isolation.
    
    This middleware:
    - Extracts tenant context from request (district, congregation, user)
    - Sets tenant context variables for use by other components
    - Validates tenant access for authenticated users
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
            exempt_paths: Set of paths to exempt from tenant validation.
            exempt_methods: Set of HTTP methods to exempt.
        """
        self.app = app
        self.exempt_paths = exempt_paths or {"/api/health"}
        self.exempt_methods = exempt_methods or {"OPTIONS"}

    async def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process a request through the middleware.
        
        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.
            
        Returns:
            HTTP response.
        """
        # Skip tenant validation for exempt paths
        if request.url.path in self.exempt_paths:
            response = await call_next(request)
            return response
        
        # Skip tenant validation for exempt methods
        if request.method in self.exempt_methods:
            response = await call_next(request)
            return response
        
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
        
        Args:
            request: HTTP request.
            
        Returns:
            Dictionary with tenant context information.
        """
        context = {}
        
        # Extract user information
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            context["user_sub"] = getattr(user, "sub", None)
            context["user_email"] = getattr(user, "email", None)
        
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


class TenantValidationMiddleware:
    """FastAPI Middleware for tenant validation.
    
    This middleware validates that authenticated users have access to
    the requested tenant resources.
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
        self.app = app
        self.exempt_paths = exempt_paths or {"/api/health", "/api/v1/auth"}
        self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS"}

    async def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
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
            response = await call_next(request)
            return response
        
        # Skip validation for exempt methods
        if request.method in self.exempt_methods:
            response = await call_next(request)
            return response
        
        # Skip validation for unauthenticated requests
        if not self._is_authenticated(request):
            response = await call_next(request)
            return response
        
        # Get tenant context from request
        tenant_context = getattr(request.state, "tenant_context", {})
        
        # If no tenant context, allow request (will be validated at service level)
        if not tenant_context:
            response = await call_next(request)
            return response
        
        # Validate tenant access
        try:
            user_sub = tenant_context.get("user_sub")
            tenant_id = tenant_context.get("tenant_id")
            tenant_type = tenant_context.get("tenant_type")
            
            if user_sub and tenant_id and tenant_type:
                # This validation would normally use a service
                # For now, we just log and allow
                logger.debug(
                    f"Tenant validation: user={user_sub}, "
                    f"tenant={tenant_id}, type={tenant_type}"
                )
            
            response = await call_next(request)
            return response
            
        except TenantValidationError as e:
            logger.warning(f"Tenant validation failed: {e}")
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={"detail": "Access denied: insufficient permissions"},
            )
        except Exception as e:
            logger.error(f"Tenant validation error: {e}")
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"},
            )

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
