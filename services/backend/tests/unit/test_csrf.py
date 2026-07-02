"""Unit tests for CSRF protection module."""

import time
from datetime import timedelta

import pytest

from app.application.csrf import CSRFError, CSRFTokenService


class TestCSRFTokenService:
    """Tests for CSRFTokenService class."""

    def test_generate_token_creates_valid_token(self):
        """Test that generated tokens are valid."""
        service = CSRFTokenService(secret_key="test-secret-key")
        token = service.generate_token()
        
        assert isinstance(token, str)
        assert ":" in token  # Should contain separators
        assert len(token.split(":")) >= 3  # Should have at least 3 parts

    def test_generate_token_with_session_id(self):
        """Test token generation with session binding."""
        service = CSRFTokenService(secret_key="test-secret-key")
        token = service.generate_token(session_id="user-123")
        
        parts = token.split(":")
        assert len(parts) == 4  # random:timestamp:session_id:signature
        assert parts[2] == "user-123"
        
        # Verify that the timestamp is set
        assert parts[1] is not None

    def test_validate_token_success(self):
        """Test successful token validation."""
        service = CSRFTokenService(secret_key="test-secret-key")
        token = service.generate_token()
        
        assert service.validate_token(token) is True

    def test_validate_token_with_session_id_success(self):
        """Test successful token validation with session binding."""
        service = CSRFTokenService(secret_key="test-secret-key")
        token = service.generate_token(session_id="user-123")
        
        assert service.validate_token(token, session_id="user-123") is True

    def test_validate_token_session_mismatch(self):
        """Test token validation fails with wrong session ID."""
        service = CSRFTokenService(secret_key="test-secret-key")
        token = service.generate_token(session_id="user-123")
        
        with pytest.raises(CSRFError, match="Token session mismatch"):
            service.validate_token(token, session_id="user-456")

    def test_validate_token_invalid_signature(self):
        """Test token validation fails with tampered token."""
        service = CSRFTokenService(secret_key="test-secret-key")
        token = service.generate_token()
        
        # Tamper with the token
        parts = token.split(":")
        tampered_token = ":".join(parts[:-1]) + ":invalid-signature"
        
        with pytest.raises(CSRFError, match="Invalid token signature"):
            service.validate_token(tampered_token)

    def test_validate_token_invalid_format(self):
        """Test token validation fails with invalid format."""
        service = CSRFTokenService(secret_key="test-secret-key")
        
        with pytest.raises(CSRFError, match="Invalid token format"):
            service.validate_token("invalid-token")

    def test_validate_token_expired(self):
        """Test token validation fails when token is expired."""
        service = CSRFTokenService(
            secret_key="test-secret-key",
            token_lifetime_seconds=1,  # 1 second lifetime
        )
        token = service.generate_token()
        
        # Wait for token to expire
        time.sleep(1.1)
        
        with pytest.raises(CSRFError, match="Token expired"):
            service.validate_token(token)

    def test_get_token_age(self):
        """Test token age calculation."""
        service = CSRFTokenService(secret_key="test-secret-key")
        token = service.generate_token()
        
        age = service.get_token_age(token)
        assert isinstance(age, timedelta)
        assert age.total_seconds() >= 0
        assert age.total_seconds() < 1  # Should be very recent

    def test_get_token_age_invalid_token(self):
        """Test token age returns 0 for invalid tokens."""
        service = CSRFTokenService(secret_key="test-secret-key")
        
        age = service.get_token_age("invalid-token")
        assert age == timedelta(0)

    def test_different_secrets_produce_different_tokens(self):
        """Test that different secrets produce incompatible tokens."""
        service1 = CSRFTokenService(secret_key="secret-1")
        service2 = CSRFTokenService(secret_key="secret-2")
        
        token1 = service1.generate_token()
        
        # Token from service1 should be invalid for service2
        with pytest.raises(CSRFError):
            service2.validate_token(token1)

    def test_token_uniqueness(self):
        """Test that each generated token is unique."""
        service = CSRFTokenService(secret_key="test-secret-key")
        
        tokens = [service.generate_token() for _ in range(100)]
        assert len(set(tokens)) == 100  # All tokens should be unique

    def test_token_contains_timestamp(self):
        """Test that tokens contain a valid timestamp."""
        service = CSRFTokenService(secret_key="test-secret-key")
        token = service.generate_token()
        
        parts = token.split(":")
        timestamp_str = parts[1]
        
        # Should be a valid integer timestamp
        timestamp = int(timestamp_str)
        assert timestamp > 0

    def test_token_contains_signature(self):
        """Test that tokens contain a valid HMAC-SHA256 signature."""
        service = CSRFTokenService(secret_key="test-secret-key")
        token = service.generate_token()

        parts = token.split(":")
        signature = parts[-1]

        # HMAC-SHA256 produces 64 hex characters
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)

    def test_validate_token_bad_base64_padding(self):
        """Test token validation fails with bad base64 padding."""
        service = CSRFTokenService(secret_key="test-secret-key")
        token = service.generate_token()

        # Tamper with the token to have bad base64 padding
        tampered_token = token + "="

        with pytest.raises(CSRFError):
            service.validate_token(tampered_token)

    def test_validate_token_missing_parts(self):
        """Test token validation fails with missing parts."""
        service = CSRFTokenService(secret_key="test-secret-key")

        # Create a token with missing parts
        bad_token = "random_hex:timestamp"

        with pytest.raises(CSRFError):
            service.validate_token(bad_token)

    def test_validate_token_unparseable_timestamp(self):
        """Test token validation fails with unparseable timestamp (ValueError path)."""
        service = CSRFTokenService(secret_key="test-secret-key")

        # Create a token with bad timestamp that triggers ValueError in int()
        bad_token = "random_hex:not-a-number:signature"

        with pytest.raises(CSRFError, match="CSRF validation failed"):
            service.validate_token(bad_token)

    def test_get_token_age_less_than_two_parts(self):
        """Test get_token_age returns timedelta(0) for tokens with less than 2 parts."""
        service = CSRFTokenService(secret_key="test-secret-key")

        # Create a token with less than 2 parts
        bad_token = "random_hex"

        age = service.get_token_age(bad_token)
        assert age == timedelta(0)

    def test_get_token_age_unparseable_timestamp(self):
        """Test get_token_age returns timedelta(0) for tokens with unparseable timestamp."""
        service = CSRFTokenService(secret_key="test-secret-key")

        # Create a token with unparseable timestamp
        bad_token = "random_hex:not-a-timestamp:signature"

        age = service.get_token_age(bad_token)
        assert age == timedelta(0)



class TestCSRFError:
    """Tests for CSRFError exception."""

    def test_csrf_error_is_exception(self):
        """Test that CSRFError is an Exception."""
        assert issubclass(CSRFError, Exception)

    def test_csrf_error_can_be_raised(self):
        """Test that CSRFError can be raised and caught."""
        with pytest.raises(CSRFError):
            raise CSRFError("Test error")

    def test_csrf_error_with_message(self):
        """Test that CSRFError carries a message."""
        error = CSRFError("Test error message")
        assert str(error) == "Test error message"
