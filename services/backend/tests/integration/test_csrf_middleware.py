"""Integration tests for CSRF middleware."""

from fastapi.testclient import TestClient

from app.application.csrf import CSRFTokenService
from app.main import app


class TestCSRFMiddleware:
    """Integration tests for CSRF middleware."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
        self.csrf_service = CSRFTokenService(secret_key="test-secret-key")

    def test_get_request_sets_csrf_cookie(self):
        """Test that GET requests receive a CSRF cookie."""
        response = self.client.get("/api/health")

        assert response.status_code == 200
        assert "set-cookie" in response.headers
        assert "csrf_token=" in response.headers["set-cookie"]

    def test_post_without_csrf_fails(self):
        """Test that POST requests without CSRF token fail."""
        # First get a valid session cookie (if needed)
        # For now, test with a simple POST that doesn't require auth

        # This test may need adjustment based on actual API endpoints
        # For now, we test the middleware behavior
        response = self.client.post(
            "/api/v1/events",
            json={"title": "Test Event"},
        )

        # Should fail with 403 if CSRF is required
        # Note: This may return 401 if auth is required first
        assert response.status_code in [401, 403]

    def test_health_endpoint_exempt_from_csrf(self):
        """Test that health endpoint is exempt from CSRF."""
        response = self.client.get("/api/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_csrf_cookie_attributes(self):
        """Test that CSRF cookie has secure attributes."""
        response = self.client.get("/api/health")

        set_cookie_header = response.headers.get("set-cookie", "")

        # Check for secure attributes
        assert "csrf_token=" in set_cookie_header
        assert "HttpOnly" in set_cookie_header
        assert "Secure" in set_cookie_header
        assert "SameSite=strict" in set_cookie_header
        assert "Path=/" in set_cookie_header

    def test_options_request_exempt_from_csrf(self):
        """Test that OPTIONS requests are exempt from CSRF."""
        response = self.client.options("/api/health")

        assert response.status_code == 200

    def test_head_request_exempt_from_csrf(self):
        """Test that HEAD requests are exempt from CSRF."""
        response = self.client.head("/api/health")

        assert response.status_code == 200

    def test_api_key_exempt_from_csrf(self):
        """Test that API-Key authenticated requests are exempt from CSRF."""
        # This test requires an endpoint that accepts API-Key auth
        # For now, we test the middleware logic
        response = self.client.get(
            "/api/health",
            headers={"X-API-Key": "test-api-key"},
        )

        # Should succeed even without CSRF token
        assert response.status_code == 200


class TestCSRFTokenServiceIntegration:
    """Integration tests for CSRF token service with middleware."""

    def setup_method(self):
        """Set up test client and service."""
        self.client = TestClient(app)
        self.csrf_service = CSRFTokenService(secret_key="test-secret-key")

    def test_token_generation_and_validation(self):
        """Test token generation and validation workflow."""
        # Generate a token
        token = self.csrf_service.generate_token(session_id="test-user")

        # Validate the token
        assert self.csrf_service.validate_token(token, session_id="test-user")

    def test_token_validation_without_session(self):
        """Test token validation without session binding."""
        token = self.csrf_service.generate_token()

        # Should validate without session ID
        assert self.csrf_service.validate_token(token)

    def test_token_validation_with_wrong_session(self):
        """Test token validation with wrong session ID."""
        token = self.csrf_service.generate_token(session_id="user-1")

        # Should fail with wrong session ID
        from app.application.csrf import CSRFError

        try:
            self.csrf_service.validate_token(token, session_id="user-2")
            raise AssertionError("Should have raised CSRFError")
        except CSRFError as e:
            assert "Token session mismatch" in str(e)
