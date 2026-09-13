"""Tests for user authentication dependencies (get_current_user, user auto-creation).

Tests cover JWT validation, user creation, and dependency injection.
"""

from datetime import UTC, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user, set_oidc_adapter
from app.adapters.auth.oidc import OIDCAdapter
from app.adapters.db.orm_models.user import UserORM
from app.domain.models.user import User


@pytest.fixture
def mock_oidc_adapter():
    """Create a mock OIDCAdapter."""
    adapter = AsyncMock(spec=OIDCAdapter)
    set_oidc_adapter(adapter)
    return adapter


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_credentials():
    """Create mock HTTP Bearer credentials."""
    credentials = MagicMock(spec=HTTPAuthorizationCredentials)
    credentials.credentials = "test-jwt-token"
    return credentials


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request."""
    return MagicMock(spec=Request)


class TestGetCurrentUserAutoCreation:
    """Test get_current_user with auto-creation of new users."""

    @pytest.mark.asyncio
    async def test_auto_create_new_user(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """Test that new user is automatically created on first login."""
        # Mock OIDC token validation
        token_claims = {
            "sub": "user-123",
            "email": "user@example.com",
            "preferred_username": "john.doe",
            "name": "John Doe",
            "given_name": "John",
            "family_name": "Doe",
            "exp": datetime.now(UTC).timestamp() + 3600,
            "iss": "https://oidc.example.com",
        }
        mock_oidc_adapter.validate_token.return_value = token_claims
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "user-123",
            "email": "user@example.com",
            "username": "john.doe",
            "name": "John Doe",
            "given_name": "John",
            "family_name": "Doe",
        }

        # Mock repository to return None (user doesn't exist)
        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = None
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            # Call the dependency
            user = await get_current_user(mock_request, mock_credentials, mock_session)

            # Verify user was created
            assert user.sub == "user-123"
            assert user.email == "user@example.com"
            assert user.username == "john.doe"
            assert user.name == "John Doe"

            # Verify save was called
            mock_repo_instance.save.assert_called_once()

    def test_user_orm_superadmin_uses_server_default_not_python_default(self):
        column = UserORM.__table__.c.is_superadmin

        assert column.default is None
        assert column.server_default is not None

    def test_trusted_function_uses_owner_allowlist_and_db_conditions_not_gucs(self):
        migration_sql = Path("alembic/versions/0017_first_user_superadmin_function.py").read_text()
        function_sql = migration_sql[
            migration_sql.index("CREATE OR REPLACE FUNCTION grant_trusted_superadmin_bootstrap") :
            migration_sql.index("DROP POLICY IF EXISTS leaders_tenant_isolation_policy")
        ]

        assert "superadmin_bootstrap_subjects" in migration_sql
        assert "SUPERADMIN_SUB" in migration_sql
        assert "grant_trusted_superadmin_bootstrap" in migration_sql
        assert "LOCK TABLE users" in migration_sql
        assert "(SELECT COUNT(*) FROM users) = 1" in migration_sql
        assert "u.sub <> p_user_sub" in migration_sql
        assert "sbs.subject = p_user_sub" in migration_sql
        assert "GRANT EXECUTE ON FUNCTION grant_trusted_superadmin_bootstrap" in migration_sql
        assert "GRANT SELECT" not in migration_sql
        assert "current_setting('app.current_user_sub'" not in function_sql

    @pytest.mark.asyncio
    async def test_update_existing_user(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """Test that existing user is updated with latest token info."""
        token_claims = {
            "sub": "user-456",
            "email": "newemail@example.com",
            "preferred_username": "jane.doe",
            "name": "Jane Doe",
            "given_name": "Jane",
            "family_name": "Doe",
        }
        mock_oidc_adapter.validate_token.return_value = token_claims
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "user-456",
            "email": "newemail@example.com",
            "username": "jane.doe",
            "name": "Jane Doe",
            "given_name": "Jane",
            "family_name": "Doe",
        }

        # Mock existing user
        existing_user = User(
            sub="user-456",
            email="oldemail@example.com",
            username="jane.smith",
        )

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = existing_user
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            user = await get_current_user(mock_request, mock_credentials, mock_session)

            # Verify user was updated
            assert user.email == "newemail@example.com"
            assert user.username == "jane.doe"
            assert user.name == "Jane Doe"

            # Verify save was called
            mock_repo_instance.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_first_user_bootstrap_uses_trusted_reconciliation_function(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        token_claims = {"sub": "bootstrap-sub", "email": "root@example.com"}
        mock_oidc_adapter.validate_token.return_value = token_claims
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "bootstrap-sub",
            "email": "root@example.com",
            "username": "root",
            "name": None,
            "given_name": None,
            "family_name": None,
        }

        with (
            patch("app.adapters.api.deps.settings") as mock_settings,
            patch("app.adapters.api.deps.SqlUserRepository") as MockRepo,
        ):
            mock_settings.superadmin_sub = None
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = None
            mock_repo_instance.has_any_user.return_value = False
            async def save_unprivileged_user(user: User) -> None:
                assert user.is_superadmin is False

            mock_repo_instance.save = AsyncMock(side_effect=save_unprivileged_user)
            MockRepo.return_value = mock_repo_instance
            mock_session.execute.return_value = MagicMock(scalar=MagicMock(return_value=True))

            user = await get_current_user(mock_request, mock_credentials, mock_session)

            assert user.is_superadmin is True
            superadmin_calls = [
                call for call in mock_session.execute.call_args_list
                if "grant_trusted_superadmin_bootstrap" in str(call.args[0])
            ]
            assert len(superadmin_calls) == 1
            assert superadmin_calls[0].args[1] == {"user_sub": "bootstrap-sub"}

    @pytest.mark.asyncio
    async def test_superadmin_sub_calls_trusted_function_after_unprivileged_save(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        mock_oidc_adapter.validate_token.return_value = {"sub": "configured-sub", "email": "root@example.com"}
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "configured-sub",
            "email": "root@example.com",
            "username": "root",
            "name": None,
            "given_name": None,
            "family_name": None,
        }

        with (
            patch("app.adapters.api.deps.settings") as mock_settings,
            patch("app.adapters.api.deps.SqlUserRepository") as MockRepo,
        ):
            mock_settings.superadmin_sub = "configured-sub"
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = None
            mock_repo_instance.has_any_user.return_value = True
            async def save_unprivileged_user(user: User) -> None:
                assert user.is_superadmin is False

            mock_repo_instance.save = AsyncMock(side_effect=save_unprivileged_user)
            MockRepo.return_value = mock_repo_instance
            mock_session.execute.return_value = MagicMock(scalar=MagicMock(return_value=True))

            user = await get_current_user(mock_request, mock_credentials, mock_session)

            assert user.is_superadmin is True
            superadmin_calls = [
                call for call in mock_session.execute.call_args_list
                if "grant_trusted_superadmin_bootstrap" in str(call.args[0])
            ]
            assert len(superadmin_calls) == 1
            assert superadmin_calls[0].args[1] == {"user_sub": "configured-sub"}

    @pytest.mark.asyncio
    async def test_arbitrary_non_configured_non_first_user_does_not_call_trusted_function(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        mock_oidc_adapter.validate_token.return_value = {"sub": "ordinary-sub", "email": "u@example.com"}
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "ordinary-sub",
            "email": "u@example.com",
            "username": "ordinary",
            "name": None,
            "given_name": None,
            "family_name": None,
        }

        with (
            patch("app.adapters.api.deps.settings") as mock_settings,
            patch("app.adapters.api.deps.SqlUserRepository") as MockRepo,
        ):
            mock_settings.superadmin_sub = "configured-sub"
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = None
            mock_repo_instance.has_any_user.return_value = True
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            user = await get_current_user(mock_request, mock_credentials, mock_session)

            assert user.is_superadmin is False
            assert all(
                "grant_trusted_superadmin_bootstrap" not in str(call.args[0])
                for call in mock_session.execute.call_args_list
            )


class TestGetCurrentUserErrors:
    """Test get_current_user error handling."""

    @pytest.mark.asyncio
    async def test_missing_bearer_token(self, mock_session, mock_request):
        """Test 401 error when Bearer token is missing."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, None, mock_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """Test 401 error when token validation fails."""
        from app.adapters.auth.oidc import TokenValidationError

        mock_oidc_adapter.validate_token.side_effect = TokenValidationError("Invalid token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_credentials, mock_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_adapter_not_initialized(self, mock_session, mock_credentials, mock_request):
        """Test 500 error when OIDC adapter is not initialized."""
        # Reset adapter to None
        set_oidc_adapter(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_credentials, mock_session)

        assert exc_info.value.status_code == 500


class TestUserCreationFlow:
    """Test complete user creation flow."""

    @pytest.mark.asyncio
    async def test_standard_oidc_claims_extraction(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """Test that standard OIDC claims are properly extracted."""
        # Minimal claims (only required fields)
        token_claims = {
            "sub": "user-789",
            "email": "user@example.com",
        }
        mock_oidc_adapter.validate_token.return_value = token_claims
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "user-789",
            "email": "user@example.com",
            "username": "user@example.com",  # Falls back to email
            "name": None,
            "given_name": None,
            "family_name": None,
        }

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = None
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            user = await get_current_user(mock_request, mock_credentials, mock_session)

            # Verify minimal user was created
        assert user.sub == "user-789"
        assert user.email == "user@example.com"
        assert user.username == "user@example.com"


class TestGetCurrentUserWithMemberships:
    @pytest.mark.asyncio
    async def test_links_single_approved_unlinked_registration_by_email(self):
        from app.adapters.api.deps import get_current_user_with_memberships

        user = User(sub="oidc|u1", email="link@example.com", username="link")

        class _MappingResult:
            def one_or_none(self):
                return {
                    "candidate_count": 1,
                    "granted_role": "PLANNER",
                    "granted_scope_type": "DISTRICT",
                    "granted_scope_id": __import__("uuid").uuid4(),
                }

        class _FunctionResult:
            def mappings(self):
                return _MappingResult()

        session = AsyncMock()
        session.execute.return_value = _FunctionResult()

        with (
            patch("app.adapters.api.deps.SqlMembershipRepository") as MemRepo,
        ):
            mem_repo = AsyncMock()
            # First call returns empty list (no memberships initially)
            # Second call returns a mock membership with role attribute
            mock_membership = MagicMock()
            mock_membership.role = MagicMock()
            mock_membership.role.value = "PLANNER"
            mem_repo.get_all_by_user.side_effect = [[], [mock_membership]]
            MemRepo.return_value = mem_repo

            ctx = await get_current_user_with_memberships(user=user, session=session)

            assert session.execute.call_count == 3
            linker_call = session.execute.call_args_list[0]
            assert "link_approved_registration" in str(linker_call.args[0])
            assert linker_call.args[1] == {"user_sub": "oidc|u1", "email": "link@example.com"}
            assert len(ctx.memberships) == 1
