"""CSRF Token Service for NAK District Planner.

This module provides HMAC-SHA256 based CSRF token generation and validation
using the Double-Submit Pattern for protection against Cross-Site Request Forgery.
"""

import hmac
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional

from app.config import settings


class CSRFError(Exception):
    """Raised when CSRF validation fails."""

    pass


class CSRFTokenService:
    """Service for CSRF token generation and validation.
    
    Uses HMAC-SHA256 for cryptographic signing of tokens with optional
    session binding for additional security.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        token_lifetime_seconds: int = 86400,
    ):
        """Initialize the CSRF token service.
        
        Args:
            secret_key: Secret key for token signing. If None, uses settings.secret_key.
            token_lifetime_seconds: Lifetime of tokens in seconds (default: 24 hours).
        """
        self.secret_key = (secret_key or settings.secret_key).encode()
        self.token_lifetime = timedelta(seconds=token_lifetime_seconds)

    def generate_token(self, session_id: Optional[str] = None) -> str:
        """Generate a new CSRF token.
        
        Args:
            session_id: Optional session ID for token binding.
            
        Returns:
            CSRF token as a signed string.
        """
        # Generate random bytes for token uniqueness
        random_bytes = secrets.token_bytes(32)
        timestamp = int(datetime.now(UTC).timestamp())
        
        # Create token data
        token_data = f"{random_bytes.hex()}:{timestamp}"
        if session_id:
            token_data += f":{session_id}"
        
        # Sign the token
        signature = hmac.new(
            self.secret_key,
            token_data.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        # Combine data and signature
        return f"{token_data}:{signature}"

    def validate_token(
        self,
        token: str,
        session_id: Optional[str] = None,
    ) -> bool:
        """Validate a CSRF token.
        
        Args:
            token: CSRF token string to validate.
            session_id: Optional session ID for validation.
            
        Returns:
            True if token is valid.
            
        Raises:
            CSRFError: If token is invalid, expired, or tampered with.
        """
        try:
            # Split token into parts
            parts = token.split(":")
            if len(parts) < 3:
                raise CSRFError("Invalid token format")
            
            # Extract components
            random_hex = parts[0]
            timestamp_str = parts[1]
            signature = parts[2]
            token_session_id = parts[3] if len(parts) > 3 else None
            
            # Validate timestamp (lifetime check)
            timestamp = int(timestamp_str)
            token_time = datetime.fromtimestamp(timestamp, UTC)
            now = datetime.now(UTC)
            
            if now - token_time > self.token_lifetime:
                raise CSRFError("Token expired")
            
            # Validate session ID binding
            if session_id and token_session_id != session_id:
                raise CSRFError("Token session mismatch")
            
            # Reconstruct token data for signature verification
            token_data = f"{random_hex}:{timestamp_str}"
            if token_session_id:
                token_data += f":{token_session_id}"
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret_key,
                token_data.encode(),
                hashlib.sha256,
            ).hexdigest()
            
            # Use constant-time comparison to prevent timing attacks
            if not hmac.compare_digest(signature, expected_signature):
                raise CSRFError("Invalid token signature")
            
            return True
            
        except ValueError as e:
            raise CSRFError(f"CSRF validation failed: {e}") from e
        except IndexError as e:
            raise CSRFError(f"CSRF validation failed: {e}") from e

    def get_token_age(self, token: str) -> timedelta:
        """Get the age of a token.
        
        Args:
            token: CSRF token string.
            
        Returns:
            Age of the token as a timedelta.
        """
        try:
            parts = token.split(":")
            if len(parts) < 2:
                return timedelta(0)
            
            timestamp = int(parts[1])
            token_time = datetime.fromtimestamp(timestamp, UTC)
            return datetime.now(UTC) - token_time
        except (ValueError, IndexError):
            return timedelta(0)


# Global instance for dependency injection
csrf_service = CSRFTokenService()
