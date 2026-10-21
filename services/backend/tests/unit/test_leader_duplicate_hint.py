# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Creating a leader whose normalised name is already known asks for confirmation (step 2)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import leaders as leaders_router
from app.adapters.api.schemas.leader import LeaderCreate
from app.domain.models.district import District
from app.domain.models.leader import Leader, LeaderRank, person_match_key


@pytest.mark.parametrize(
    "variant",
    ["Hans Müller", "  hans   MÜLLER ", "Hans Muller", "Br. Hans Müller", "Ev. Hans Müller", "Dr. Hans Müller"],
)
def test_person_match_key_ignores_case_spacing_accents_and_titles(variant: str) -> None:
    assert person_match_key(variant) == person_match_key("Hans Müller")


@pytest.mark.parametrize(
    ("typed", "other"),
    [
        ("D'Angelo", "DAngelo"),
        ("D’Angelo", "d angelo"),
        ("O'Neil", "ONeil"),
        ("Anna-Lena Weber", "Anna Lena Weber"),
        ("Anna_Lena Weber", "AnnaLena Weber"),
        ("Hans  Müller.", "Hans Müller"),
    ],
)
def test_person_match_key_treats_punctuation_and_spacing_the_same_way(typed: str, other: str) -> None:
    assert person_match_key(typed) == person_match_key(other)


@pytest.mark.parametrize("other", ["Hans Meier", "Hans", "Johann Müller", "Müller Hans"])
def test_person_match_key_keeps_different_names_apart(other: str) -> None:
    assert person_match_key(other) != person_match_key("Hans Müller")


def test_person_match_key_of_only_a_title_is_not_empty() -> None:
    assert person_match_key("Br.") != ""


def _existing(district_id, name="Hans Müller", rank=LeaderRank.EVANGELIST, active=True):
    return Leader.create(
        name=name, district_id=district_id, rank=rank, congregation_id=uuid.uuid4(),
        email="geheim@example.org", phone="0123", is_active=active,
    )


async def _create(district_id, body, existing):
    districts = AsyncMock()
    districts.get.return_value = District.create(name="B")
    repo = AsyncMock()
    repo.list_by_district.return_value = existing
    with patch("app.adapters.api.routers.leaders.require_role_in_district"):
        result = await leaders_router.create_leader(
            district_id, body, object(), AsyncMock(), districts=districts, leaders_repo=repo,
        )
    return result, repo


@pytest.mark.asyncio
@pytest.mark.parametrize("active", [True, False])
async def test_a_known_name_is_rejected_with_the_matching_people(active: bool) -> None:
    district_id = uuid.uuid4()
    known = _existing(district_id, active=active)
    with pytest.raises(HTTPException) as err:
        await _create(district_id, LeaderCreate(name="hans  müller"), [known])
    assert err.value.status_code == 409
    detail = err.value.detail
    assert detail["code"] == "LEADER_DUPLICATE"
    assert detail["matches"] == [
        {"id": str(known.id), "name": known.name, "congregation_id": str(known.congregation_id),
         "is_active": active}
    ]
    assert "geheim@example.org" not in str(detail) and "0123" not in str(detail)


@pytest.mark.asyncio
async def test_explicit_confirmation_creates_a_namesake() -> None:
    district_id = uuid.uuid4()
    known = _existing(district_id)
    result, repo = await _create(
        district_id, LeaderCreate(name="Hans Müller", confirm_duplicate=True), [known]
    )
    assert result.name == "Hans Müller" and result.id != known.id
    repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_a_new_name_needs_no_confirmation() -> None:
    district_id = uuid.uuid4()
    result, repo = await _create(district_id, LeaderCreate(name="Anna Beispiel"), [_existing(district_id)])
    assert result.name == "Anna Beispiel"
    repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_the_rejection_saves_nothing() -> None:
    district_id = uuid.uuid4()
    districts = AsyncMock()
    districts.get.return_value = District.create(name="B")
    repo = AsyncMock()
    repo.list_by_district.return_value = [_existing(district_id)]
    with patch("app.adapters.api.routers.leaders.require_role_in_district"):
        with pytest.raises(HTTPException):
            await leaders_router.create_leader(
                district_id, LeaderCreate(name="Hans Müller"), object(), AsyncMock(),
                districts=districts, leaders_repo=repo,
            )
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_check_and_the_save_are_serialised_per_district() -> None:
    """Two concurrent creations must not both pass the duplicate check (advisory lock)."""
    district_id = uuid.uuid4()
    events: list[str] = []
    districts = AsyncMock()
    districts.get.return_value = District.create(name="B")
    repo = AsyncMock()
    repo.list_by_district.side_effect = lambda *_: events.append("check") or []
    repo.save.side_effect = lambda *_: events.append("save")

    async def lock(_db, key):
        events.append(f"lock:{key == district_id}")

    with (
        patch("app.adapters.api.routers.leaders.require_role_in_district"),
        patch("app.adapters.api.routers.leaders.acquire_advisory_xact_lock", side_effect=lock),
    ):
        await leaders_router.create_leader(
            district_id, LeaderCreate(name="Neu Person"), object(), AsyncMock(),
            districts=districts, leaders_repo=repo,
        )
    assert events == ["lock:True", "check", "save"]

