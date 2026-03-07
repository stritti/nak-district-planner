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

from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    raw_key = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw_key))


def encrypt_credentials(data: dict) -> str:
    """Serialize *data* to JSON and return a Fernet token (str)."""
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_credentials(token: str) -> dict:
    """Decrypt a Fernet token and return the original dict."""
    return json.loads(_fernet().decrypt(token.encode()))
