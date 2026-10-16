# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Export tokens carry a hash digest; the plaintext secret is shown once."""

from app.domain.models.export_token import (
    ExportToken,
    TokenType,
    hash_export_token,
)


def _create(**overrides):
    kwargs: dict = {
        "label": "Feed",
        "token_type": TokenType.INTERNAL,
        "district_id": "d",
        "congregation_id": None,
    }
    kwargs.update(overrides)
    return ExportToken.create(**kwargs)


def test_create_returns_plaintext_once_and_computes_hash():
    token, raw_secret = _create()
    assert token.token == raw_secret
    assert token.token_hash == hash_export_token(raw_secret)
    assert token.token_hash != raw_secret


def test_hash_is_deterministic_and_unique_per_secret():
    token_a, raw_a = _create()
    token_b, raw_b = _create()
    assert raw_a != raw_b
    assert token_a.token_hash != token_b.token_hash
    assert hash_export_token(raw_a) == hash_export_token(raw_a)


def test_hash_is_sha256_hex_digest():
    digest = hash_export_token("secret")
    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)
