"""Candidate ingestion failures must be rolled back without stopping other events."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.external_candidate_sync_adapter import (
    CandidateIngestionError,
    import_candidate_or_match,
)
from app.application.sync_service import run_sync
from app.domain.models.calendar_integration import CalendarIntegration, CalendarType
from app.domain.models.raw_calendar_event import RawCalendarEvent

START = datetime(2026, 7, 1, 10, tzinfo=UTC)


def raw(uid: str) -> RawCalendarEvent:
    return RawCalendarEvent(
        uid=uid, title="External", start_at=START,
        end_at=START + timedelta(hours=1), description=None,
        content_hash="provider", is_cancelled=False,
    )


def integration() -> CalendarIntegration:
    return CalendarIntegration.create(
        district_id=uuid4(), type=CalendarType.ICS,
        name="External", credentials_enc="encrypted",
    )


def context():
    session = MagicMock()
    savepoint = MagicMock()
    savepoint.__aenter__ = AsyncMock(return_value=None)
    savepoint.__aexit__ = AsyncMock(return_value=False)
    session.begin_nested.return_value = savepoint
    return SimpleNamespace(
        session=session, integration=integration(),
        instance_repo=AsyncMock(), link_repo=AsyncMock(),
    ), savepoint


async def test_savepoint_is_used_and_successful_candidate_can_be_processed():
    ctx, savepoint = context()
    with (
        patch("app.application.external_candidate_sync_adapter.SqlExternalEventCandidateRepository"),
        patch("app.application.external_candidate_sync_adapter.SqlNotificationRepository"),
        patch(
            "app.application.external_candidate_sync_adapter.ingest_unlinked_event",
            new_callable=AsyncMock, return_value=False,
        ) as ingest,
    ):
        assert await import_candidate_or_match(
            raw=raw("one"), context=ctx, new_content_hash="hash"
        ) is False
    ctx.session.begin_nested.assert_called_once_with()
    savepoint.__aexit__.assert_awaited_once()
    ingest.assert_awaited_once()


async def test_candidate_failure_exits_savepoint_with_exception():
    ctx, savepoint = context()
    with (
        patch("app.application.external_candidate_sync_adapter.SqlExternalEventCandidateRepository"),
        patch("app.application.external_candidate_sync_adapter.SqlNotificationRepository"),
        patch(
            "app.application.external_candidate_sync_adapter.ingest_unlinked_event",
            new_callable=AsyncMock, side_effect=ValueError("untrusted provider value"),
        ),
        pytest.raises(CandidateIngestionError, match="Individual candidate ingestion failed"),
    ):
        await import_candidate_or_match(
            raw=raw("broken"), context=ctx, new_content_hash="hash"
        )
    exit_args = savepoint.__aexit__.await_args.args
    assert exit_args[0] is ValueError
    assert str(exit_args[1]) == "untrusted provider value"


async def test_one_failed_candidate_does_not_abort_later_events():
    config = integration()
    session = AsyncMock()
    integration_repo = AsyncMock()
    integration_repo.get.return_value = config
    link_repo = AsyncMock()
    link_repo.get_by_external_event.return_value = None
    connector = MagicMock()
    connector.fetch_events = AsyncMock(return_value=[raw("broken"), raw("healthy")])
    connector.authoritative_snapshot = False
    with (
        patch("app.application.sync_service.SqlCalendarIntegrationRepository", return_value=integration_repo),
        patch("app.application.sync_service.SqlEventInstanceRepository", return_value=AsyncMock()),
        patch("app.application.sync_service.SqlPlanningSlotRepository", return_value=AsyncMock()),
        patch("app.application.sync_service.SqlExternalEventLinkRepository", return_value=link_repo),
        patch("app.application.sync_service.decrypt_credentials", return_value={}),
        patch("app.application.sync_service._get_connector", return_value=connector),
        patch(
            "app.application.sync_service.import_candidate_or_match",
            new_callable=AsyncMock,
            side_effect=[CandidateIngestionError("redacted"), False],
        ) as ingest,
    ):
        result = await run_sync(config.id, session)
    assert result.failed == 1
    assert result.skipped == 1
    assert ingest.await_count == 2
    assert config.last_sync_error == "1 calendar event(s) failed during partial sync"
