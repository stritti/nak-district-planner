from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import external_candidates
from app.domain.errors import CandidateAlreadyReviewedError
from app.domain.models.external_event_candidate import CandidateStatus


def auth():
    return SimpleNamespace(user=SimpleNamespace(sub="admin"))


@pytest.mark.asyncio
async def test_list_requires_admin_and_filters_pending():
    district_id, repository = uuid4(), AsyncMock()
    repository.list.return_value = []
    with patch.object(external_candidates, "require_role_in_district") as require_role:
        result = await external_candidates.list_candidates(
            district_id, auth(), repository, limit=100, offset=0
        )
    assert result == []
    require_role.assert_called_once_with(auth(), external_candidates.Role.DISTRICT_ADMIN, district_id)
    repository.list.assert_awaited_once_with(district_id, CandidateStatus.PENDING, 100, 0)


@pytest.mark.asyncio
async def test_accept_maps_value_error_to_conflict_without_running_service_when_not_authorized():
    candidate_id = uuid4()
    with patch.object(
        external_candidates,
        "load_for_review",
        side_effect=HTTPException(403),
    ):
        with pytest.raises(HTTPException) as exc:
            await external_candidates.accept_candidate(
                candidate_id,
                external_candidates.AcceptCandidate(),
                auth(),
                AsyncMock(),
                repository=AsyncMock(),
                service=AsyncMock(),
            )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_accept_and_dismiss_return_conflict_for_terminal_candidate():
    candidate_id, candidate, review = uuid4(), object(), AsyncMock()
    review.accept.side_effect = CandidateAlreadyReviewedError("Kandidat wurde bereits geprüft")
    review.dismiss.side_effect = CandidateAlreadyReviewedError("Kandidat wurde bereits geprüft")
    with patch.object(external_candidates, "load_for_review", return_value=(candidate, review)):
        with pytest.raises(HTTPException) as exc:
            await external_candidates.accept_candidate(
                candidate_id,
                external_candidates.AcceptCandidate(),
                auth(),
                AsyncMock(),
                repository=AsyncMock(),
                service=review,
            )
        assert exc.value.status_code == 409
        with pytest.raises(HTTPException) as exc:
            await external_candidates.dismiss_candidate(
                candidate_id, auth(), repository=AsyncMock(), service=review
            )
        assert exc.value.status_code == 409
