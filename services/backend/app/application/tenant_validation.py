"""Tenant Validation Service.

Provides validation and isolation for multi-tenant operations.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.orm_models.district import DistrictORM
from app.adapters.db.orm_models.membership import MembershipORM
from app.adapters.db.orm_models.user import UserORM
from app.domain.models.membership import ScopeType
from app.domain.models.role import Role

logger = logging.getLogger(__name__)


class TenantValidationError(Exception):
    """Raised when tenant validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class TenantValidationService:
    """Service for validating tenant access and memberships.
    
    Provides methods to:
    - Validate user membership in a tenant
    - Check role-based access
    - Validate cross-tenant access
    - Extract tenant context from requests
    """

    def __init__(self, session: AsyncSession):
        """Initialize the service.
        
        Args:
            session: Async SQLAlchemy session.
        """
        self.session = session

    async def validate_user_in_district(
        self,
        user_sub: str,
        district_id: uuid.UUID,
        required_role: Role | None = None,
    ) -> bool:
        """Validate that a user has access to a district.
        
        Args:
            user_sub: User subject (OIDC sub).
            district_id: District ID to check.
            required_role: Optional minimum role required.
            
        Returns:
            True if user has access to the district.
            
        Raises:
            TenantValidationError: If validation fails.
        """
        # Check if user is superadmin
        result = await self.session.execute(
            select(UserORM.is_superadmin).where(UserORM.sub == user_sub)
        )
        is_superadmin = result.scalar_one_or_none()
        
        if is_superadmin:
            return True
        
        # Check user's memberships in the district
        result = await self.session.execute(
            select(MembershipORM)
            .where(
                and_(
                    MembershipORM.user_sub == user_sub,
                    MembershipORM.scope_type == ScopeType.DISTRICT.value,
                    MembershipORM.scope_id == district_id,
                )
            )
        )
        memberships = result.scalars().all()
        
        if not memberships:
            raise TenantValidationError(
                f"User {user_sub} has no membership in district {district_id}",
                {"user_sub": user_sub, "district_id": str(district_id)},
            )
        
        # Check required role
        if required_role:
            for membership in memberships:
                # membership.role is a plain DB string — wrap in Role for comparison
                if Role(membership.role) >= required_role:
                    return True

            raise TenantValidationError(
                f"User {user_sub} requires role {required_role.value} in district {district_id}",
                {
                    "user_sub": user_sub,
                    "district_id": str(district_id),
                    "required_role": required_role.value,
                    "actual_roles": [m.role for m in memberships],
                },
            )
        
        return True

    async def validate_user_in_congregation(
        self,
        user_sub: str,
        congregation_id: uuid.UUID,
        required_role: Role | None = None,
    ) -> bool:
        """Validate that a user has access to a congregation.
        
        Args:
            user_sub: User subject (OIDC sub).
            congregation_id: Congregation ID to check.
            required_role: Optional minimum role required.
            
        Returns:
            True if user has access to the congregation.
            
        Raises:
            TenantValidationError: If validation fails.
        """
        # Check if user is superadmin
        result = await self.session.execute(
            select(UserORM.is_superadmin).where(UserORM.sub == user_sub)
        )
        is_superadmin = result.scalar_one_or_none()
        
        if is_superadmin:
            return True
        
        # Check user's memberships in the congregation
        result = await self.session.execute(
            select(MembershipORM)
            .where(
                and_(
                    MembershipORM.user_sub == user_sub,
                    MembershipORM.scope_type == ScopeType.CONGREGATION.value,
                    MembershipORM.scope_id == congregation_id,
                )
            )
        )
        memberships = result.scalars().all()
        
        if not memberships:
            raise TenantValidationError(
                f"User {user_sub} has no membership in congregation {congregation_id}",
                {"user_sub": user_sub, "congregation_id": str(congregation_id)},
            )
        
        # Check required role
        if required_role:
            for membership in memberships:
                # membership.role is a plain DB string — wrap in Role for comparison
                if Role(membership.role) >= required_role:
                    return True

            raise TenantValidationError(
                f"User {user_sub} requires role {required_role.value} in congregation {congregation_id}",
                {
                    "user_sub": user_sub,
                    "congregation_id": str(congregation_id),
                    "required_role": required_role.value,
                    "actual_roles": [m.role for m in memberships],
                },
            )
        
        return True

    async def validate_user_in_tenant(
        self,
        user_sub: str,
        tenant_id: uuid.UUID,
        tenant_type: str,
        required_role: Role | None = None,
    ) -> bool:
        """Validate that a user has access to a tenant (district or congregation).
        
        Args:
            user_sub: User subject (OIDC sub).
            tenant_id: Tenant ID to check.
            tenant_type: Type of tenant ("district" or "congregation").
            required_role: Optional minimum role required.
            
        Returns:
            True if user has access to the tenant.
            
        Raises:
            TenantValidationError: If validation fails.
        """
        if tenant_type == "district":
            return await self.validate_user_in_district(
                user_sub, tenant_id, required_role
            )
        elif tenant_type == "congregation":
            return await self.validate_user_in_congregation(
                user_sub, tenant_id, required_role
            )
        else:
            raise TenantValidationError(
                f"Unknown tenant type: {tenant_type}",
                {"tenant_type": tenant_type},
            )

    async def get_user_districts(
        self,
        user_sub: str,
    ) -> list[uuid.UUID]:
        """Get all districts a user has access to.
        
        Args:
            user_sub: User subject (OIDC sub).
            
        Returns:
            List of district IDs.
        """
        # Check if user is superadmin
        result = await self.session.execute(
            select(UserORM.is_superadmin).where(UserORM.sub == user_sub)
        )
        is_superadmin = result.scalar_one_or_none()
        
        if is_superadmin:
            # Superadmin has access to all districts
            result = await self.session.execute(select(DistrictORM.id))
            return [row[0] for row in result.all()]
        
        # Get user's district memberships
        result = await self.session.execute(
            select(MembershipORM.scope_id)
            .where(
                and_(
                    MembershipORM.user_sub == user_sub,
                    MembershipORM.scope_type == ScopeType.DISTRICT.value,
                )
            )
            .distinct()
        )
        return [row[0] for row in result.all()]

    async def get_user_congregations(
        self,
        user_sub: str,
        district_id: uuid.UUID | None = None,
    ) -> list[uuid.UUID]:
        """Get all congregations a user has access to.
        
        Args:
            user_sub: User subject (OIDC sub).
            district_id: Optional district filter.
            
        Returns:
            List of congregation IDs.
        """
        # Check if user is superadmin
        result = await self.session.execute(
            select(UserORM.is_superadmin).where(UserORM.sub == user_sub)
        )
        is_superadmin = result.scalar_one_or_none()
        
        if is_superadmin:
            # Superadmin has access to all congregations
            query = select(CongregationORM.id)
            if district_id:
                query = query.where(CongregationORM.district_id == district_id)
            result = await self.session.execute(query)
            return [row[0] for row in result.all()]
        
        # Get user's congregation memberships
        result = await self.session.execute(
            select(MembershipORM.scope_id).where(
                and_(
                    MembershipORM.user_sub == user_sub,
                    MembershipORM.scope_type == ScopeType.CONGREGATION.value,
                )
            )
            .distinct()
        )
        
        congregation_ids = [row[0] for row in result.all()]
        
        if district_id and congregation_ids:
            # Filter by district — join with congregation to check district_id
            result = await self.session.execute(
                select(CongregationORM.id)
                .where(
                    and_(
                        CongregationORM.id.in_(congregation_ids),
                        CongregationORM.district_id == district_id,
                    )
                )
            )
            return [row[0] for row in result.all()]
        
        return congregation_ids

    async def get_tenant_district(
        self,
        tenant_id: uuid.UUID,
        tenant_type: str,
    ) -> uuid.UUID | None:
        """Get the district ID for a tenant.
        
        Args:
            tenant_id: Tenant ID (district or congregation).
            tenant_type: Type of tenant.
            
        Returns:
            District ID, or None if not found.
        """
        if tenant_type == "district":
            return tenant_id
        
        if tenant_type == "congregation":
            result = await self.session.execute(
                select(CongregationORM.district_id).where(CongregationORM.id == tenant_id)
            )
            return result.scalar_one_or_none()
        
        return None

    async def validate_cross_tenant_access(
        self,
        user_sub: str,
        resource_tenant_id: uuid.UUID,
        resource_tenant_type: str,
        access_tenant_id: uuid.UUID | None = None,
        access_tenant_type: str | None = None,
    ) -> bool:
        """Validate that a user can access a resource across tenants.
        
        This checks if the user has access to both the resource's tenant
        and the access tenant (if specified).
        
        Args:
            user_sub: User subject (OIDC sub).
            resource_tenant_id: Tenant ID of the resource.
            resource_tenant_type: Type of the resource's tenant.
            access_tenant_id: Optional tenant ID to check access through.
            access_tenant_type: Optional type of the access tenant.
            
        Returns:
            True if access is allowed.
            
        Raises:
            TenantValidationError: If access is denied.
        """
        # If no access tenant specified, use resource tenant
        if access_tenant_id is None:
            access_tenant_id = resource_tenant_id
            access_tenant_type = resource_tenant_type
        
        # Validate user has access to the access tenant
        await self.validate_user_in_tenant(
            user_sub, access_tenant_id, access_tenant_type
        )
        
        # If access tenant is the same as resource tenant, we're done
        if access_tenant_id == resource_tenant_id:
            return True
        
        # Check if access tenant is a parent of resource tenant
        # (e.g., district can access congregation resources)
        if access_tenant_type == "district" and resource_tenant_type == "congregation":
            # Check if congregation belongs to district
            result = await self.session.execute(
                select(CongregationORM.district_id).where(
                    CongregationORM.id == resource_tenant_id
                )
            )
            congregation_district_id = result.scalar_one_or_none()
            
            if congregation_district_id == access_tenant_id:
                return True
        
        # Access denied
        raise TenantValidationError(
            f"User {user_sub} cannot access {resource_tenant_type} {resource_tenant_id} "
            f"through {access_tenant_type} {access_tenant_id}",
            {
                "user_sub": user_sub,
                "resource_tenant_id": str(resource_tenant_id),
                "resource_tenant_type": resource_tenant_type,
                "access_tenant_id": str(access_tenant_id),
                "access_tenant_type": access_tenant_type,
            },
        )
