# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Export tokens are stored hashed; the plaintext secret is shown once."""

from app.domain.models.export_token import (
    ExportToken,
    TokenType,
    hash_export_token,
    is_hashed_export_token,
)


def _create(**overrides):
    kwargs = dict(
        label="Feed",
        token_type=TokenType.INTERNAL,
        district_id="d",
        congregation_id=None,
    )
    kwargs.update(overrides)
    return ExportToken.create(**kwargs)


def test_create_returns_plaintext_once_and_stores_hash():
    token, raw_secret = _create()
    assert token.token != raw_secret
    assert token.token == hash_export_token(raw_secret)
    assert is_hashed_export_token(token.token)
    assert not is_hashed_export_token(raw_secret)


def test_hash_is_deterministic_and_salted_by_token_value():
    token_a, raw_a = _create()
    token_b, raw_b = _create()
    assert raw_a != raw_b
    assert token_a.token != token_b.token
    assert hash_export_token(raw_a) == hash_export_token(raw_a)


def test_hashed_marker_requires_full_prefix_and_length():
    assert not is_hashed_export_token("sha256")
    assert not is_hashed_export_token("plaintext-token")
    assert is_hashed_export_token(hash_export_token("x"))


def test_legacy_plaintext_tokens_are_distinguished():
    assert not is_hashed_export_token("legacy-secret")
    assert is_hashed_export_token(hash_export_token("legacy-secret"))
