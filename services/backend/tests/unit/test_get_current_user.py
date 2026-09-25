"""Tests for user authentication dependencies (get_current_user, user auto-creation).

Tests cover JWT validation, user creation, and dependency injection.
"""

from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import get_current_user, set_oidc_adapter
from app.adapters.auth.oidc import OIDCAdapter
from app.domain.models.user import User


@pytest.fixture
def mock_oidc_adapter():
    """Create a mock OIDCAdapter."""
    adapter = AsyncMock(spec=OIDCAdapter)
    set_oidc_adapter(adapter)
    return adapter


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession with a deterministic no-grant result."""
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalar_one_or_none.return_value = False
    session.execute = AsyncMock(return_value=result)
    return session


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

    @pytest.mark.asyncio
    async def test_first_login_persists_bootstrap_superadmin(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """The database grant result (owner-provisioned subject) is kept in
        memory for the in-session user object; the app passes only the
        authenticated subject and no authorization facts.
        """
        token_claims = {
            "sub": "first-user",
            "email": "first@example.com",
            "preferred_username": "first",
            "name": "First User",
        }
        mock_oidc_adapter.validate_token.return_value = token_claims
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "first-user",
            "email": "first@example.com",
            "username": "first",
            "name": "First User",
            "given_name": None,
            "family_name": None,
        }

        grant_result = MagicMock()
        grant_result.scalar_one_or_none.return_value = True
        mock_session.execute = AsyncMock(return_value=grant_result)

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = None
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            user = await get_current_user(
                mock_request, mock_credentials, mock_session
            )

        assert user.is_superadmin is True
        grant_call = mock_session.execute.await_args_list[-1]
        assert "grant_bootstrap_superadmin" in str(grant_call.args[0])
        # Authorization facts are derived from owner-controlled database
        # state; the app must not pass configured subjects or login hints.
        assert grant_call.args[1] == {"user_sub": "first-user"}

    @pytest.mark.asyncio
    async def test_existing_user_with_grant_keeps_flag(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """An existing user the database grants the flag keeps it, and the
        reconciliation function is invoked on every login so rotations of
        the configured subject also revoke stale persisted grants.
        """
        token_claims = {
            "sub": "configured-admin",
            "email": "admin@example.com",
            "preferred_username": "admin",
            "name": "Admin",
        }
        mock_oidc_adapter.validate_token.return_value = token_claims
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "configured-admin",
            "email": "admin@example.com",
            "username": "admin",
            "name": "Admin",
            "given_name": None,
            "family_name": None,
        }
        existing_user = User(
            sub="configured-admin",
            email="admin@example.com",
            username="admin",
            is_superadmin=False,
        )

        grant_result = MagicMock()
        grant_result.scalar_one_or_none.return_value = True
        mock_session.execute = AsyncMock(return_value=grant_result)

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = existing_user
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            user = await get_current_user(
                mock_request, mock_credentials, mock_session
            )

        assert user.is_superadmin is True
        grant_call = mock_session.execute.await_args_list[-1]
        assert "grant_bootstrap_superadmin" in str(grant_call.args[0])
        assert grant_call.args[1] == {"user_sub": "configured-admin"}

    @pytest.mark.asyncio
    async def test_later_login_without_grant_keeps_flag_false(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """A later first-time login without configuration receives no grant."""
        token_claims = {
            "sub": "later-user",
            "email": "later@example.com",
            "preferred_username": "later",
            "name": "Later User",
        }
        mock_oidc_adapter.validate_token.return_value = token_claims
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "later-user",
            "email": "later@example.com",
            "username": "later",
            "name": "Later User",
            "given_name": None,
            "family_name": None,
        }

        grant_result = MagicMock()
        grant_result.scalar_one_or_none.return_value = False
        mock_session.execute = AsyncMock(return_value=grant_result)

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = None
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            user = await get_current_user(
                mock_request, mock_credentials, mock_session
            )

        assert user.is_superadmin is False

    @pytest.mark.asyncio
    async def test_existing_user_keeps_stored_flag(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """Existing users keep the stored owner-controlled flag untouched."""
        token_claims = {
            "sub": "user-456",
            "email": "newemail@example.com",
            "preferred_username": "jane.doe",
            "name": "Jane Doe",
        }
        mock_oidc_adapter.validate_token.return_value = token_claims
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": "user-456",
            "email": "newemail@example.com",
            "username": "jane.doe",
            "name": "Jane Doe",
            "given_name": None,
            "family_name": None,
        }

        existing_user = User(
            sub="user-456",
            email="oldemail@example.com",
            username="jane.smith",
            is_superadmin=True,
        )

        grant_result = MagicMock()
        grant_result.scalar_one_or_none.return_value = True
        mock_session.execute = AsyncMock(return_value=grant_result)

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = existing_user
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            user = await get_current_user(
                mock_request, mock_credentials, mock_session
            )

        assert user.is_superadmin is True
        grant_call = mock_session.execute.await_args_list[-1]
        assert "grant_bootstrap_superadmin" in str(grant_call.args[0])
        assert grant_call.args[1] == {"user_sub": "user-456"}

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


class TestBootstrapReconciliation:
    """Negative-path tests for the superadmin reconciliation dependency flow."""

    @staticmethod
    def _oidc_mock(mock_oidc_adapter, sub="newbie", email="newbie@example.com"):
        mock_oidc_adapter.validate_token.return_value = {"sub": sub}
        mock_oidc_adapter.extract_user_info.return_value = {
            "sub": sub,
            "email": email,
            "username": sub,
            "name": sub,
            "given_name": None,
            "family_name": None,
        }

    @pytest.mark.asyncio
    async def test_grant_failure_propagates_as_500(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """A failing reconciliation call must not silently default to false:
        the exception propagates so the request is rejected, never a
        half-authenticated session with an unset superadmin flag.
        """
        self._oidc_mock(mock_oidc_adapter)
        mock_session.execute = AsyncMock(side_effect=RuntimeError("db down"))

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = None
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    mock_request, mock_credentials, mock_session
                )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_unconfigured_installation_mints_no_superadmin(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """Without an owner-provisioned subject the function only reports the
        persisted state: a fresh login stays non-superadmin.
        """
        self._oidc_mock(mock_oidc_adapter)
        grant_result = MagicMock()
        grant_result.scalar_one_or_none.return_value = False
        mock_session.execute = AsyncMock(return_value=grant_result)

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = None
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            user = await get_current_user(
                mock_request, mock_credentials, mock_session
            )

        assert user.is_superadmin is False

    @pytest.mark.asyncio
    async def test_guc_installed_with_verified_subject_before_grant(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """The verified token subject must be installed as session GUC right
        before the reconciliation call, independent of middleware state.
        """
        self._oidc_mock(mock_oidc_adapter, sub="verified-sub")
        grant_result = MagicMock()
        grant_result.scalar_one_or_none.return_value = False
        mock_session.execute = AsyncMock(return_value=grant_result)

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = None
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            await get_current_user(mock_request, mock_credentials, mock_session)

        execute_calls = mock_session.execute.await_args_list
        guc_call = execute_calls[-2]
        assert "set_config" in str(guc_call.args[0])
        assert "app.current_user_sub" in str(guc_call.args[0])
        assert guc_call.args[1] == {"user_sub": "verified-sub"}
        grant_call = execute_calls[-1]
        assert "grant_bootstrap_superadmin" in str(grant_call.args[0])
        assert grant_call.args[1] == {"user_sub": "verified-sub"}

    @pytest.mark.asyncio
    async def test_revoked_superadmin_flag_synced_in_memory(
        self, mock_oidc_adapter, mock_session, mock_credentials, mock_request
    ):
        """After an owner rotation the former superadmin must lose the flag in
        memory too: the reconciliation result overwrites the stale domain
        object state instead of keeping the outdated in-memory value.
        """
        self._oidc_mock(mock_oidc_adapter, sub="former-admin")
        existing_user = User(
            sub="former-admin",
            email="former@example.com",
            username="former",
            is_superadmin=True,
        )
        grant_result = MagicMock()
        grant_result.scalar_one_or_none.return_value = False
        mock_session.execute = AsyncMock(return_value=grant_result)

        with patch("app.adapters.api.deps.SqlUserRepository") as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_sub.return_value = existing_user
            mock_repo_instance.save = AsyncMock()
            MockRepo.return_value = mock_repo_instance

            user = await get_current_user(
                mock_request, mock_credentials, mock_session
            )

        assert user.is_superadmin is False


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
        session = AsyncMock()
        link_result = MagicMock()
        link_result.mappings.return_value.one_or_none.return_value = {
            "candidate_count": 1,
            "granted_role": "PLANNER",
            "granted_scope_type": "DISTRICT",
            "granted_scope_id": __import__("uuid").uuid4(),
        }
        session.execute = AsyncMock(return_value=link_result)

        with patch("app.adapters.api.deps.SqlMembershipRepository") as MemRepo:
            mem_repo = AsyncMock()
            mock_membership = MagicMock()
            mock_membership.role = MagicMock()
            mock_membership.role.value = "PLANNER"
            mem_repo.get_all_by_user.side_effect = [[], [mock_membership]]
            MemRepo.return_value = mem_repo

            ctx = await get_current_user_with_memberships(user=user, session=session)

            assert session.execute.await_count >= 1
            linking_call = session.execute.await_args_list[0]
            assert "link_approved_registration" in str(linking_call.args[0])
            assert linking_call.args[1] == {
                "user_sub": "oidc|u1",
                "email": "link@example.com",
            }
            assert mem_repo.get_all_by_user.await_count == 2
            assert len(ctx.memberships) == 1

    @pytest.mark.asyncio
    async def test_user_without_email_skips_registration_link(self):
        """Users without an email claim must not invoke the linking function."""
        from app.adapters.api.deps import get_current_user_with_memberships

        user = User(sub="oidc|no-email", email="", username="no-email")
        session = AsyncMock()
        with patch("app.adapters.api.deps.SqlMembershipRepository") as MemRepo:
            mem_repo = AsyncMock()
            mem_repo.get_all_by_user.return_value = []
            MemRepo.return_value = mem_repo
            ctx = await get_current_user_with_memberships(user=user, session=session)
            for call in session.execute.await_args_list:
                assert "link_approved_registration" not in str(call.args[0])
            assert ctx.memberships == []

    @pytest.mark.asyncio
    async def test_multiple_registration_candidates_skip_auto_link(self):
        """Ambiguous registrations (candidate_count > 1) must not link and
        must keep the previously loaded memberships instead of granting.
        """
        from app.adapters.api.deps import get_current_user_with_memberships

        user = User(sub="oidc|amb", email="amb@example.com", username="amb")
        session = AsyncMock()
        link_result = MagicMock()
        link_result.mappings.return_value.one_or_none.return_value = {
            "candidate_count": 2,
            "granted_role": None,
            "granted_scope_type": None,
            "granted_scope_id": None,
        }
        session.execute = AsyncMock(return_value=link_result)
        with patch("app.adapters.api.deps.SqlMembershipRepository") as MemRepo:
            mem_repo = AsyncMock()
            mock_membership = MagicMock()
            mock_membership.role.value = "VIEWER"
            mem_repo.get_all_by_user.return_value = [mock_membership]
            MemRepo.return_value = mem_repo
            ctx = await get_current_user_with_memberships(user=user, session=session)
            assert len(ctx.memberships) == 1

    @pytest.mark.asyncio
    async def test_require_membership_access_rejects_membershipless_user(self):
        """Non-superadmin without memberships gets 403 (approval pending)."""
        from app.adapters.api.deps import CurrentUserContext, require_membership_access

        user = User(sub="oidc|pending", email="p@example.com", username="p")
        ctx = CurrentUserContext(user=user, memberships=[])
        with pytest.raises(HTTPException) as exc_info:
            await require_membership_access(auth=ctx)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_membership_access_allows_superadmin_without_memberships(self):
        """Superadmins bypass the membership gate by design."""
        from app.adapters.api.deps import CurrentUserContext, require_membership_access

        user = User(sub="oidc|root", email="root@example.com", username="root",
                    is_superadmin=True)
        ctx = CurrentUserContext(user=user, memberships=[])
        result = await require_membership_access(auth=ctx)
        assert result.user.sub == "oidc|root"
