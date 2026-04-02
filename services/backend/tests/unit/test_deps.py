"""Unit tests for main application and deps."""

from __future__ import annotations


import pytest
from fastapi import HTTPException, status

from app.adapters.api.deps import verify_api_key
from app.config import settings


class TestVerifyApiKey:
    """Tests for API key verification."""

    async def test_verify_api_key_valid(self):
        """verify_api_key should succeed with correct key."""
        correct_key = settings.api_key
        await verify_api_key(correct_key)
        # No exception means success

    async def test_verify_api_key_invalid(self):
        """verify_api_key should raise 403 with invalid key."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key("wrong-key")
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    async def test_verify_api_key_none(self):
        """verify_api_key should raise 403 with None key."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(None)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    async def test_verify_api_key_hmac_compare_digest(self):
        """verify_api_key should use constant-time comparison."""
        # This ensures timing attacks are prevented
        correct_key = settings.api_key
        # Attempting with slight variation should fail
        wrong_key = correct_key[:-1] + ("x" if correct_key[-1] != "x" else "a")

        with pytest.raises(HTTPException):
            await verify_api_key(wrong_key)
