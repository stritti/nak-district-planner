"""
Tests for user authentication dependencies (get_current_user, user auto-creation).

Tests cover JWT validation, user creation, and dependency injection.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
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
    """Create a mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_credentials():
    """Create mock HTTP Bearer credentials."""
    credentials = MagicMock()
    credentials.credentials = "test-jwt-token"
    return credentials


class TestGetCurrentUserAutoCreation:
    """Test get_current_user with auto-creation of new users."""

    @pytest.mark.asyncio
    async def test_auto_create_new_user(self, mock_oidc_adapter, mock_session, mock_credentials):
        """Test that new user is automatically created on first login."""
        # Mock OIDC token validation
        token_claims = {
            "sub": "user-123",
            "email": "user@example.com",
            "preferred_username": "john.doe",
            "name": "John Doe",
            "given_name": "John",
            "family_name": "Doe",
            "exp": datetime.now(timezone.utc).timestamp() + 3600,
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
            user = await get_current_user(mock_credentials, mock_session)

            # Verify user was created
            assert user.sub == "user-123"
            assert user.email == "user@example.com"
            assert user.username == "john.doe"
            assert user.name == "John Doe"

            # Verify save was called
            mock_repo_instance.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_user(self, mock_oidc_adapter, mock_session, mock_credentials):
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

            user = await get_current_user(mock_credentials, mock_session)

            # Verify user was updated
            assert user.email == "newemail@example.com"
            assert user.username == "jane.doe"
            assert user.name == "Jane Doe"

            # Verify save was called
            mock_repo_instance.save.assert_called_once()


class TestGetCurrentUserErrors:
    """Test get_current_user error handling."""

    @pytest.mark.asyncio
    async def test_missing_bearer_token(self, mock_session):
        """Test 401 error when Bearer token is missing."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None, mock_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token(self, mock_oidc_adapter, mock_session, mock_credentials):
        """Test 401 error when token validation fails."""
        from app.adapters.auth.oidc import TokenValidationError

        mock_oidc_adapter.validate_token.side_effect = TokenValidationError("Invalid token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_adapter_not_initialized(self, mock_session, mock_credentials):
        """Test 500 error when OIDC adapter is not initialized."""
        # Reset adapter to None
        set_oidc_adapter(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_session)

        assert exc_info.value.status_code == 500


class TestUserCreationFlow:
    """Test complete user creation flow."""

    @pytest.mark.asyncio
    async def test_standard_oidc_claims_extraction(
        self, mock_oidc_adapter, mock_session, mock_credentials
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

            user = await get_current_user(mock_credentials, mock_session)

            # Verify minimal user was created
            assert user.sub == "user-789"
            assert user.email == "user@example.com"
            assert user.username == "user@example.com"
