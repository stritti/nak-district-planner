# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Export tokens carry a hash digest; the plaintext secret is shown once."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.adapters.api.routers.export import _token_response
from app.adapters.db.repositories.export_token import SqlExportTokenRepository
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
    assert not hasattr(token, "token")
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


@pytest.mark.parametrize("token_type", [TokenType.PUBLIC, TokenType.INTERNAL])
def test_creation_response_is_the_only_response_with_a_secret(token_type):
    token, raw = _create(token_type=token_type, district_id=uuid.uuid4())
    assert _token_response(token, raw_secret=raw).token == raw
    listed = _token_response(token).model_dump(mode="json")
    assert listed["token"] is None
    assert raw not in listed.values()
    assert token.token_hash not in listed.values()


@pytest.mark.parametrize(
    "overrides",
    [
        {"token_type": TokenType.PUBLIC},
        {"leader_id": uuid.uuid4()},
        {"congregation_id": uuid.uuid4()},
    ],
)
def test_invalid_subject_token_is_rejected(overrides):
    with pytest.raises(ValueError, match="Subject tokens require"):
        _create(subject_sub="alice", **overrides)


@pytest.mark.asyncio
async def test_unknown_secret_returns_no_token_under_the_hash_only_contract():
    session = AsyncMock()
    session.execute.return_value.scalar_one_or_none = lambda: None
    assert await SqlExportTokenRepository(session).get_by_token("unknown-secret") is None
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_resolves_only_a_sha256_digest():
    session = AsyncMock()
    session.execute.return_value.scalar_one_or_none = lambda: None
    raw_secret = "canary-plain-secret"
    await SqlExportTokenRepository(session).get_by_token(raw_secret)
    query = session.execute.await_args.args[0]
    assert hash_export_token(raw_secret) in query.compile().params.values()
    assert raw_secret not in query.compile().params.values()


@pytest.mark.asyncio
async def test_repository_never_persists_plaintext_secret():
    session = AsyncMock()
    token, raw_secret = _create(district_id=uuid.uuid4())
    await SqlExportTokenRepository(session).save(token)
    session.add.assert_called_once()
    row = session.add.call_args.args[0]
    assert row.token_hash == hash_export_token(raw_secret)
    assert not hasattr(row, "token")
    session.flush.assert_awaited_once()
