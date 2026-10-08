"""User domain model — represents an authenticated user in the system.

Extracted from OIDC token claims (sub, email, preferred_username, etc.)
"""

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class User:
    """User entity extracted from OIDC token claims.

    Attributes:
        sub: Subject identifier from OIDC token (unique user ID from IDP)
        email: Email address
        username: Username (preferred_username or email)
        name: Full name (optional)
        given_name: First name (optional)
        family_name: Last name (optional)
        created_at: When user was first created in the system
        email_verified: True only when the current token carried an ``email``
            claim with ``email_verified`` == boolean ``true`` (per request,
            not persisted). Required for registration auto-linking (#461).
    """

    sub: str
    email: str
    username: str
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    is_superadmin: bool = False
    created_at: datetime | None = None
    email_verified: bool = False

    def __post_init__(self) -> None:
        """Ensure created_at is set to now if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
