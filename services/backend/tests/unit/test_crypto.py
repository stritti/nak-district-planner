"""Unit tests for crypto module."""

from __future__ import annotations

import pytest

from app.application.crypto import CryptoError, decrypt_credentials, encrypt_credentials


class TestCrypto:
    """Tests for encryption and decryption functions."""

    def test_encrypt_and_decrypt_roundtrip(self):
        """encrypt() then decrypt() should return original data."""
        original = {"api_key": "secret-key-123", "url": "https://example.com"}

        encrypted = encrypt_credentials(original)
        assert isinstance(encrypted, str)
        assert encrypted != str(original)  # Should be encrypted, not plaintext

        decrypted = decrypt_credentials(encrypted)
        assert decrypted == original

    def test_decrypt_invalid_token_raises(self):
        """decrypt() with invalid token should raise an exception."""
        with pytest.raises(Exception):
            decrypt_credentials("invalid-token")

    def test_encrypt_empty_dict(self):
        """encrypt({}) should work and round-trip."""
        original = {}
        encrypted = encrypt_credentials(original)
        decrypted = decrypt_credentials(encrypted)
        assert decrypted == original

    def test_encrypt_complex_nested_dict(self):
        """encrypt() should handle nested structures."""
        original = {
            "oauth": {
                "access_token": "token-xyz",
                "refresh_token": "refresh-abc",
                "expires_in": 3600,
            },
            "client_id": "client-123",
        }

        encrypted = encrypt_credentials(original)
        decrypted = decrypt_credentials(encrypted)
        assert decrypted == original

    def test_decrypt_non_string_input(self):
        """Test decrypting with non-string input raises CryptoError."""
        with pytest.raises(CryptoError):
            decrypt_credentials(123)

    def test_decrypt_malformed_data(self):
        """Test decrypting malformed data raises CryptoError."""
        with pytest.raises(CryptoError):
            decrypt_credentials("malformed-data")

