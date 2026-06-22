"""Audit Logging Middleware for FastAPI.

This middleware automatically logs audit events for all requests.
"""

import logging
import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.application.audit_service import AuditAction, AuditContext, AuditStatus, audit_service

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware for automatic audit logging.

    Registered via ``app.add_middleware()`` — Starlette instantiates it
    as ASGI middleware and calls ``dispatch(request, call_next)`` for
    each request.

    This middleware:
    - Generates a unique request ID for each request
    - Tracks request start time
    - Logs audit events for state-changing requests
    - Handles errors and logs failed attempts
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

        # Process request
        response = None
        error = None

        try:
            response = await call_next(request)
            return response
        except Exception as e:
            error = e
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Log audit event if needed
            # NOTE: context is extracted *after call_next* so FastAPI
            # dependency resolution (get_current_user etc.) has already
            # populated request.state.user before we read it.
            if self._should_log_audit(request):
                context = self._extract_context(
                    request,
                    request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                await self._log_audit_event(
                    request,
                    response,
                    error,
                    context,
                    request_id,
                    duration,
                )

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
        
        # Extract tenant context from path params (populated by FastAPI routing)
        path_params = getattr(request, "path_params", {}) or {}
        district_id = path_params.get("district_id", getattr(request.state, "district_id", None))
        congregation_id = path_params.get("congregation_id", getattr(request.state, "congregation_id", None))
        
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
        """Extract client IP address from request.
        
        Args:
            request: HTTP request.
            
        Returns:
            Client IP address, or None if not available.
        """
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client address
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None

    def _should_log_audit(self, request: Request) -> bool:
        """Determine if this request should be audit logged.
        
        Args:
            request: HTTP request.
            
        Returns:
            True if request should be audit logged.
        """
        # Skip exempt paths
        if request.url.path in self.exempt_paths:
            return False
        
        # Skip exempt methods
        if request.method in self.exempt_methods:
            return False
        
        return True

    async def _log_audit_event(
        self,
        request: Request,
        response: Response | None,
        error: Exception | None,
        context: AuditContext,
        request_id: str,
        duration: float,
    ) -> None:
        """Log an audit event for the request.
        
        Args:
            request: HTTP request.
            response: HTTP response (if successful).
            error: Exception (if request failed).
            context: Audit context.
            request_id: Unique request ID.
            duration: Request duration in seconds.
        """
        try:
            # Determine action based on HTTP method and path
            action = self._get_action_from_method(request.method, request.url.path)
            
            # Determine resource type from path
            resource_type = self._get_resource_type(request.url.path)
            
            # Determine status — mark as FAILED for exceptions and non-2xx/3xx responses
            status = AuditStatus.SUCCESS
            if error:
                status = AuditStatus.FAILED
            elif response and response.status_code >= 400:
                status = AuditStatus.FAILED
            error_message = str(error) if error else (
                f"HTTP {response.status_code}" if response and response.status_code >= 400 else None
            )
            
            # Extract resource ID from path if available
            resource_id = self._extract_resource_id(request.url.path)
            # For CREATE responses with no path UUID, try Location header
            if resource_id is None and action == AuditAction.CREATE and response:
                location = response.headers.get("Location")
                if location:
                    resource_id = self._extract_resource_id(location)
            
            # Log the audit event
            await self.audit_service.log(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                context=context,
                status=status,
                error_message=error_message,
                extra_metadata={
                    "http_method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code if response else None,
                    "duration_ms": round(duration * 1000, 2),
                    "user_agent": context.user_agent,
                },
            )
            
        except Exception as e:
            # Don't let audit logging failures break the request
            logger.error(f"Failed to log audit event: {e}")

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
        if re.search(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", last_segment):
            return False
        
        # Known collection names → resource create, not a command
        resource_names = {
            "events", "districts", "congregations", "leaders", "invitations",
            "service-assignments", "calendar-integrations", "memberships",
            "users", "export", "auth", "oidc", "token", "discovery",
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
                pass
        
        return None
