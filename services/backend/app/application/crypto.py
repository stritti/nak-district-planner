"""Credential encryption/decryption using Fernet symmetric encryption.

A 32-byte key is derived from settings.secret_key via SHA-256, then
base64url-encoded for use with cryptography.fernet.Fernet.

Usage:
    enc = encrypt_credentials({"url": "https://example.com/cal.ics"})
    dec = decrypt_credentials(enc)  # -> {"url": "https://..."}
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


class CryptoError(Exception):
    """Raised when decryption fails (e.g. wrong secret key)."""


def _fernet() -> Fernet:
    raw_key = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw_key))


def encrypt_credentials(data: dict) -> str:
    """Serialize *data* to JSON and return a Fernet token (str)."""
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_credentials(token: str) -> dict:
    """Decrypt a Fernet token and return the original dict."""
    try:
        return json.loads(_fernet().decrypt(token.encode()))
    except InvalidToken as e:
        logger.error("Failed to decrypt credentials. Likely SECRET_KEY mismatch.")
        raise CryptoError(
            "Entschlüsselung fehlgeschlagen. Wahrscheinlich wurde der SECRET_KEY geändert. "
            "Bitte die Zugangsdaten für diesen Kalender neu speichern."
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during decryption: {e}")
        raise CryptoError(f"Unerwarteter Fehler bei der Entschlüsselung: {e}") from e
