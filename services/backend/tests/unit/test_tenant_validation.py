"""Unit tests for Tenant Validation Service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.tenant_validation import (
    TenantValidationError,
    TenantValidationService,
)
from app.domain.models.role import Role


class TestTenantValidationError:
    """Tests for TenantValidationError exception."""

    def test_error_with_message(self):
        """Test error with message."""
        error = TenantValidationError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error with details."""
        error = TenantValidationError("Test error", {"key": "value"})
        assert error.message == "Test error"
        assert error.details == {"key": "value"}


class TestTenantValidationService:
    """Tests for TenantValidationService class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create a service instance."""
        return TenantValidationService(mock_session)

    @pytest.mark.asyncio
    async def test_validate_user_in_district_success(self, service, mock_session):
        """Test successful validation of user in district."""
        user_sub = "user-123"
        district_id = uuid.uuid4()
        
        # Mock is_superadmin check - returns False
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = False
        
        # Mock membership check - returns a membership with VIEWER role
        mock_membership = MagicMock()
        mock_membership.role = Role.VIEWER
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value.all.return_value = [mock_membership]
        
        mock_session.execute.side_effect = [mock_result1, mock_result2]
        
        result = await service.validate_user_in_district(user_sub, district_id)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_user_in_district_superadmin(self, service, mock_session):
        """Test that superadmin can access any district."""
        user_sub = "user-123"
        district_id = uuid.uuid4()
        
        # Mock is_superadmin check - returns True
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = True
        mock_session.execute.return_value = mock_result
        
        result = await service.validate_user_in_district(user_sub, district_id)
        
        assert result is True
        # Should not check memberships for superadmin
        assert mock_session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_validate_user_in_district_no_membership(self, service, mock_session):
        """Test validation fails when user has no membership."""
        user_sub = "user-123"
        district_id = uuid.uuid4()
        
        # Mock is_superadmin check - returns False
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = False
        
        # Mock membership check - returns empty list
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value.all.return_value = []
        
        mock_session.execute.side_effect = [mock_result1, mock_result2]
        
        with pytest.raises(TenantValidationError) as exc_info:
            await service.validate_user_in_district(user_sub, district_id)
        
        assert "no membership" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_user_in_district_required_role(self, service, mock_session):
        """Test validation with required role."""
        user_sub = "user-123"
        district_id = uuid.uuid4()
        
        # Mock is_superadmin check - returns False
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = False
        
        # Mock membership check - user has VIEWER role
        mock_membership = MagicMock()
        mock_membership.role = Role.VIEWER
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value.all.return_value = [mock_membership]
        
        mock_session.execute.side_effect = [mock_result1, mock_result2]
        
        # Require PLANNER role
        with pytest.raises(TenantValidationError) as exc_info:
            await service.validate_user_in_district(
                user_sub, district_id, required_role=Role.PLANNER
            )
        
        assert "requires role" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_user_in_district_sufficient_role(self, service, mock_session):
        """Test validation with sufficient role."""
        user_sub = "user-123"
        district_id = uuid.uuid4()
        
        # Mock is_superadmin check - returns False
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = False
        
        # Mock membership check - user has PLANNER role
        mock_membership = MagicMock()
        mock_membership.role = Role.PLANNER
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value.all.return_value = [mock_membership]
        
        mock_session.execute.side_effect = [mock_result1, mock_result2]
        
        # Require VIEWER role
        result = await service.validate_user_in_district(
            user_sub, district_id, required_role=Role.VIEWER
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_user_in_congregation_success(self, service, mock_session):
        """Test successful validation of user in congregation."""
        user_sub = "user-123"
        congregation_id = uuid.uuid4()
        
        # Mock is_superadmin check - returns False
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = False
        
        # Mock membership check - returns a membership
        mock_membership = MagicMock()
        mock_membership.role = Role.VIEWER
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value.all.return_value = [mock_membership]
        
        mock_session.execute.side_effect = [mock_result1, mock_result2]
        
        result = await service.validate_user_in_congregation(user_sub, congregation_id)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_user_districts_superadmin(self, service, mock_session):
        """Test getting districts for superadmin."""
        user_sub = "user-123"
        
        # Mock is_superadmin check - returns True
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = True
        
        # Mock district query
        mock_district_id = uuid.uuid4()
        mock_result2 = MagicMock()
        mock_result2.all.return_value = [(mock_district_id,)]
        
        mock_session.execute.side_effect = [mock_result1, mock_result2]
        
        districts = await service.get_user_districts(user_sub)
        
        assert mock_district_id in districts

    @pytest.mark.asyncio
    async def test_get_user_districts_regular_user(self, service, mock_session):
        """Test getting districts for regular user."""
        user_sub = "user-123"
        
        # Mock is_superadmin check - returns False
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = False
        
        # Mock membership query
        mock_district_id = uuid.uuid4()
        mock_result2 = MagicMock()
        mock_result2.all.return_value = [(mock_district_id,)]
        
        mock_session.execute.side_effect = [mock_result1, mock_result2]
        
        districts = await service.get_user_districts(user_sub)
        
        assert mock_district_id in districts

    @pytest.mark.asyncio
    async def test_get_tenant_district_district(self, service, mock_session):
        """Test getting district for a district tenant."""
        district_id = uuid.uuid4()
        
        result = await service.get_tenant_district(district_id, "district")
        
        assert result == district_id

    @pytest.mark.asyncio
    async def test_get_tenant_district_congregation(self, service, mock_session):
        """Test getting district for a congregation tenant."""
        congregation_id = uuid.uuid4()
        district_id = uuid.uuid4()
        
        # Mock congregation query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = district_id
        mock_session.execute.return_value = mock_result
        
        result = await service.get_tenant_district(congregation_id, "congregation")
        
        assert result == district_id

    @pytest.mark.asyncio
    async def test_validate_cross_tenant_access_same_tenant(self, service, mock_session):
        """Test cross-tenant access when access tenant is same as resource tenant."""
        user_sub = "user-123"
        tenant_id = uuid.uuid4()
        
        # Mock is_superadmin check - returns False
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = False
        
        # Mock membership check
        mock_membership = MagicMock()
        mock_membership.role = Role.VIEWER
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value.all.return_value = [mock_membership]
        
        mock_session.execute.side_effect = [mock_result1, mock_result2]
        
        result = await service.validate_cross_tenant_access(
            user_sub=user_sub,
            resource_tenant_id=tenant_id,
            resource_tenant_type="district",
            access_tenant_id=tenant_id,
            access_tenant_type="district",
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_cross_tenant_access_district_to_congregation(self, service, mock_session):
        """Test cross-tenant access from district to congregation."""
        user_sub = "user-123"
        district_id = uuid.uuid4()
        congregation_id = uuid.uuid4()
        
        # Mock is_superadmin check - returns False
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = False
        
        # Mock membership check - user has DISTRICT_ADMIN role
        mock_membership = MagicMock()
        mock_membership.role = Role.DISTRICT_ADMIN
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value.all.return_value = [mock_membership]
        
        # Mock congregation.district_id query
        mock_result3 = MagicMock()
        mock_result3.scalar_one_or_none.return_value = district_id
        
        mock_session.execute.side_effect = [mock_result1, mock_result2, mock_result3]
        
        result = await service.validate_cross_tenant_access(
            user_sub=user_sub,
            resource_tenant_id=congregation_id,
            resource_tenant_type="congregation",
            access_tenant_id=district_id,
            access_tenant_type="district",
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_cross_tenant_access_denied(self, service, mock_session):
        """Test cross-tenant access denied."""
        user_sub = "user-123"
        district_id = uuid.uuid4()
        other_district_id = uuid.uuid4()
        
        # Mock is_superadmin check - returns False
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = False
        
        # Mock membership check - user has DISTRICT_ADMIN role
        mock_membership = MagicMock()
        mock_membership.role = Role.DISTRICT_ADMIN
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value.all.return_value = [mock_membership]
        
        # Mock congregation.district_id query - returns different district
        mock_result3 = MagicMock()
        mock_result3.scalar_one_or_none.return_value = other_district_id
        
        mock_session.execute.side_effect = [mock_result1, mock_result2, mock_result3]
        
        with pytest.raises(TenantValidationError) as exc_info:
            await service.validate_cross_tenant_access(
                user_sub=user_sub,
                resource_tenant_id=uuid.uuid4(),
                resource_tenant_type="congregation",
                access_tenant_id=district_id,
                access_tenant_type="district",
            )
        
        assert "cannot access" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_user_in_tenant_unknown_type(self, service, mock_session):
        """Test validation with unknown tenant type."""
        with pytest.raises(TenantValidationError) as exc_info:
            await service.validate_user_in_tenant(
                user_sub="user-123",
                tenant_id=uuid.uuid4(),
                tenant_type="unknown",
            )
        
        assert "Unknown tenant type" in str(exc_info.value)
