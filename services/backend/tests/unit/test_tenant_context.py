"""Unit tests for Tenant Context management."""

import uuid

import pytest

from app.tenant import TenantContext, current_congregation, current_district, current_tenant, current_user_roles, current_user_sub


class TestTenantContextGet:
    """Tests for TenantContext getter methods."""

    def test_get_tenant_default(self):
        """Test get_tenant returns None by default."""
        assert TenantContext.get_tenant() is None

    def test_get_district_default(self):
        """Test get_district returns None by default."""
        assert TenantContext.get_district() is None

    def test_get_congregation_default(self):
        """Test get_congregation returns None by default."""
        assert TenantContext.get_congregation() is None

    def test_get_user_sub_default(self):
        """Test get_user_sub returns None by default."""
        assert TenantContext.get_user_sub() is None

    def test_get_user_roles_default(self):
        """Test get_user_roles returns None by default."""
        assert TenantContext.get_user_roles() is None


class TestTenantContextSetAndGet:
    """Tests for TenantContext set_context and getter methods."""

    def test_set_and_get_tenant(self):
        """Test setting and getting tenant ID."""
        tenant_id = uuid.uuid4()
        TenantContext.set_context(tenant_id=tenant_id)
        assert TenantContext.get_tenant() == tenant_id
        TenantContext.clear_context()

    def test_set_and_get_district(self):
        """Test setting and getting district ID."""
        district_id = uuid.uuid4()
        TenantContext.set_context(district_id=district_id)
        assert TenantContext.get_district() == district_id
        TenantContext.clear_context()

    def test_set_and_get_congregation(self):
        """Test setting and getting congregation ID."""
        congregation_id = uuid.uuid4()
        TenantContext.set_context(congregation_id=congregation_id)
        assert TenantContext.get_congregation() == congregation_id
        TenantContext.clear_context()

    def test_set_and_get_user_sub(self):
        """Test setting and getting user sub."""
        TenantContext.set_context(user_sub="user-123")
        assert TenantContext.get_user_sub() == "user-123"
        TenantContext.clear_context()

    def test_set_and_get_user_roles(self):
        """Test setting and getting user roles."""
        roles = ["admin", "planner"]
        TenantContext.set_context(user_roles=roles)
        assert TenantContext.get_user_roles() == roles
        TenantContext.clear_context()

    def test_set_all_context(self):
        """Test setting all context values at once."""
        tenant_id = uuid.uuid4()
        district_id = uuid.uuid4()
        congregation_id = uuid.uuid4()
        TenantContext.set_context(
            tenant_id=tenant_id,
            district_id=district_id,
            congregation_id=congregation_id,
            user_sub="user-456",
            user_roles=["viewer"],
        )
        assert TenantContext.get_tenant() == tenant_id
        assert TenantContext.get_district() == district_id
        assert TenantContext.get_congregation() == congregation_id
        assert TenantContext.get_user_sub() == "user-456"
        assert TenantContext.get_user_roles() == ["viewer"]
        TenantContext.clear_context()

    def test_set_context_partial(self):
        """Test setting only some context values."""
        TenantContext.set_context(tenant_id=uuid.uuid4())
        assert TenantContext.get_tenant() is not None
        assert TenantContext.get_district() is None
        assert TenantContext.get_congregation() is None
        assert TenantContext.get_user_sub() is None
        assert TenantContext.get_user_roles() is None
        TenantContext.clear_context()


class TestTenantContextClear:
    """Tests for TenantContext.clear_context method."""

    def test_clear_context_resets_all(self):
        """Test clear_context resets all context variables to None."""
        TenantContext.set_context(
            tenant_id=uuid.uuid4(),
            user_sub="test-user",
        )
        TenantContext.clear_context()
        assert TenantContext.get_tenant() is None
        assert TenantContext.get_district() is None
        assert TenantContext.get_congregation() is None
        assert TenantContext.get_user_sub() is None
        assert TenantContext.get_user_roles() is None


class TestTenantContextHasContext:
    """Tests for TenantContext.has_context method."""

    def test_has_context_false_when_none_set(self):
        """Test has_context returns False when no context is set."""
        TenantContext.clear_context()
        assert TenantContext.has_context() is False

    def test_has_context_true_with_tenant(self):
        """Test has_context returns True when tenant is set."""
        TenantContext.set_context(tenant_id=uuid.uuid4())
        assert TenantContext.has_context() is True
        TenantContext.clear_context()

    def test_has_context_true_with_district(self):
        """Test has_context returns True when district is set."""
        TenantContext.set_context(district_id=uuid.uuid4())
        assert TenantContext.has_context() is True
        TenantContext.clear_context()

    def test_has_context_true_with_user_sub(self):
        """Test has_context returns True when user_sub is set."""
        TenantContext.set_context(user_sub="user-789")
        assert TenantContext.has_context() is True
        TenantContext.clear_context()

    def test_has_context_false_with_only_congregation(self):
        """Test has_context returns False when only congregation is set."""
        # has_context checks tenant, district, user_sub — not congregation alone
        TenantContext.set_context(congregation_id=uuid.uuid4())
        assert TenantContext.has_context() is False
        TenantContext.clear_context()

    def test_has_context_false_with_only_roles(self):
        """Test has_context returns False when only user_roles is set."""
        TenantContext.set_context(user_roles=["admin"])
        assert TenantContext.has_context() is False
        TenantContext.clear_context()


class TestContextVarIsolation:
    """Tests that each context variable is independent."""

    def test_tenant_does_not_affect_district(self):
        """Test that setting tenant doesn't affect district."""
        TenantContext.clear_context()
        tenant_id = uuid.uuid4()
        TenantContext.set_context(tenant_id=tenant_id)
        assert TenantContext.get_district() is None
        TenantContext.clear_context()

    def test_user_sub_does_not_affect_roles(self):
        """Test that setting user_sub doesn't affect user_roles."""
        TenantContext.clear_context()
        TenantContext.set_context(user_sub="test")
        assert TenantContext.get_user_roles() is None
        TenantContext.clear_context()
