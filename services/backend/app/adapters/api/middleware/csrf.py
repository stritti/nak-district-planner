"""CSRF Middleware for FastAPI.

This module provides middleware for CSRF protection using the Double-Submit Pattern.
"""

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_403_FORBIDDEN

from app.application.csrf import CSRFError, CSRFTokenService

logger = logging.getLogger(__name__)


class CSRFMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware for CSRF protection.

    Implements the Double-Submit Pattern for CSRF protection:
    - CSRF token is sent both as a cookie and in a custom header
    - Token is validated on state-changing requests (POST, PUT, DELETE, PATCH)
    - Token is automatically rotated on each response
    """

    def __init__(
        self,
        app,
        csrf_service: CSRFTokenService,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        exempt_paths: set[str] | None = None,
        exempt_methods: set[str] | None = None,
    ):
        """Initialize the CSRF middleware.

        Args:
            app: FastAPI application instance.
            csrf_service: CSRF token service for generation and validation.
            cookie_name: Name of the CSRF token cookie (default: 'csrf_token').
            header_name: Name of the CSRF token header (default: 'X-CSRF-Token').
            exempt_paths: Set of paths to exempt from CSRF protection.
            exempt_methods: Set of HTTP methods to exempt (default: GET, HEAD, OPTIONS).
        """
        super().__init__(app)
        self.csrf_service = csrf_service
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.exempt_paths = exempt_paths or {"/api/health"}
        self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS"}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process a request through the middleware.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.

        Returns:
            HTTP response, potentially with CSRF cookie set.
        """
        # Skip CSRF for safe methods (GET, HEAD, OPTIONS)
        if request.method in self.exempt_methods:
            response = await call_next(request)
            return self._add_csrf_cookie(response, request)

        # Skip CSRF for exempt paths
        if request.url.path in self.exempt_paths:
            response = await call_next(request)
            return self._add_csrf_cookie(response, request)

        # Skip CSRF for API-Key authentication
        if request.headers.get("X-API-Key"):
            response = await call_next(request)
            return response

        # Validate CSRF token for state-changing requests
        try:
            csrf_token = self._get_csrf_token(request)
            session_id = self._get_session_id(request)

            if not csrf_token:
                raise CSRFError("CSRF token missing")

            self.csrf_service.validate_token(csrf_token, session_id)

        except CSRFError as e:
            logger.warning(f"CSRF validation failed for {request.method} {request.url.path}: {e}")
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={"detail": "CSRF validation failed"},
            )

        # Execute the request
        response = await call_next(request)

        # Add new CSRF token to response (token rotation)
        return self._add_csrf_cookie(response, request)

    def _get_csrf_token(self, request: Request) -> str | None:
        """Extract CSRF token from header or cookie.

        Args:
            request: HTTP request.

        Returns:
            CSRF token string, or None if not found.
        """
        # Try header first
        token = request.headers.get(self.header_name)
        if token:
            return token

        # Try cookie
        if hasattr(request, "cookies"):
            return request.cookies.get(self.cookie_name)

        return None

    def _get_session_id(self, request: Request) -> str | None:
        """Extract session ID from request.

        For JWT-based auth, uses the user's sub claim as session ID.
        For cookie-based sessions, uses the session_id cookie.

        Args:
            request: HTTP request.

        Returns:
            Session ID string, or None if not available.
        """
        # For JWT-based auth: use user sub as session ID
        if hasattr(request.state, "user"):
            user = request.state.user
            if user and hasattr(user, "sub"):
                return user.sub

        # For cookie-based session: use session_id cookie
        if hasattr(request, "cookies"):
            return request.cookies.get("session_id")

        return None

    def _add_csrf_cookie(
        self,
        response: Response,
        request: Request,
    ) -> Response:
        """Add a new CSRF token as a cookie to the response.

        Args:
            response: HTTP response.
            request: HTTP request (for session ID).

        Returns:
            Response with CSRF cookie set.
        """
        session_id = self._get_session_id(request)
        csrf_token = self.csrf_service.generate_token(session_id)

        # Set cookie with security attributes
        response.set_cookie(
            key=self.cookie_name,
            value=csrf_token,
            httponly=True,
            secure=True,  # Only send over HTTPS
            samesite="strict",  # Protection against CSRF
            max_age=int(self.csrf_service.token_lifetime.total_seconds()),
            path="/",
        )

        return response
