"""User API schemas for authentication and user info endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class MembershipOut(BaseModel):
    """Membership entry exposed by auth access endpoint."""

    role: str = Field(description="Role name")
    scope_type: str = Field(description="Scope type: DISTRICT or CONGREGATION")
    scope_id: str = Field(description="Scope UUID")


class AccessContextOut(BaseModel):
    """Current effective access context for authenticated user."""

    status: Literal["ACTIVE", "PENDING_APPROVAL"]
    memberships: list[MembershipOut] = Field(default_factory=list)


class UserOut(BaseModel):
    """User information response schema."""

    sub: str = Field(description="OIDC subject (user ID from identity provider)")
    email: str = Field(description="Email address")
    username: str = Field(description="Username (preferred_username or email)")
    name: str | None = Field(default=None, description="Full name")
    given_name: str | None = Field(default=None, description="First name")
    family_name: str | None = Field(default=None, description="Last name")
    is_superadmin: bool = Field(default=False, description="Global superadmin flag")
