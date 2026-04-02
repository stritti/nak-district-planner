"""
User API schemas for authentication and user info endpoints.
"""

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    """User information response schema."""

    sub: str = Field(description="OIDC subject (user ID from identity provider)")
    email: str = Field(description="Email address")
    username: str = Field(description="Username (preferred_username or email)")
    name: str | None = Field(default=None, description="Full name")
    given_name: str | None = Field(default=None, description="First name")
    family_name: str | None = Field(default=None, description="Last name")
