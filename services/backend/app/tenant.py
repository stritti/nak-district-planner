"""Tenant Context Management.

Provides context variables and utilities for tenant isolation.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Optional


# Context variables for tenant information
current_tenant: ContextVar[Optional[uuid.UUID]] = ContextVar("current_tenant", default=None)
current_district: ContextVar[Optional[uuid.UUID]] = ContextVar("current_district", default=None)
current_congregation: ContextVar[Optional[uuid.UUID]] = ContextVar("current_congregation", default=None)
current_user_sub: ContextVar[Optional[str]] = ContextVar("current_user_sub", default=None)
current_user_roles: ContextVar[Optional[list[str]]] = ContextVar("current_user_roles", default=None)


class TenantContext:
    """Utility class for tenant context management."""

    @staticmethod
    def get_tenant() -> uuid.UUID | None:
        """Get current tenant ID."""
        return current_tenant.get()

    @staticmethod
    def get_district() -> uuid.UUID | None:
        """Get current district ID."""
        return current_district.get()

    @staticmethod
    def get_congregation() -> uuid.UUID | None:
        """Get current congregation ID."""
        return current_congregation.get()

    @staticmethod
    def get_user_sub() -> str | None:
        """Get current user subject (OIDC sub)."""
        return current_user_sub.get()

    @staticmethod
    def get_user_roles() -> list[str] | None:
        """Get current user roles."""
        return current_user_roles.get()

    @staticmethod
    def set_context(
        tenant_id: uuid.UUID | None = None,
        district_id: uuid.UUID | None = None,
        congregation_id: uuid.UUID | None = None,
        user_sub: str | None = None,
        user_roles: list[str] | None = None,
    ) -> None:
        """Set tenant context for current request.
        
        Args:
            tenant_id: Current tenant ID (congregation or district).
            district_id: Current district ID.
            congregation_id: Current congregation ID.
            user_sub: Current user subject (OIDC sub).
            user_roles: Current user roles.
        """
        current_tenant.set(tenant_id)
        current_district.set(district_id)
        current_congregation.set(congregation_id)
        current_user_sub.set(user_sub)
        current_user_roles.set(user_roles)

    @staticmethod
    def clear_context() -> None:
        """Clear tenant context."""
        current_tenant.set(None)
        current_district.set(None)
        current_congregation.set(None)
        current_user_sub.set(None)
        current_user_roles.set(None)

    @staticmethod
    def has_context() -> bool:
        """Check if tenant context is set."""
        return (
            current_tenant.get() is not None
            or current_district.get() is not None
            or current_user_sub.get() is not None
        )
