# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Bridge candidate ingestion to the hardened sync's per-event failure channel."""

from __future__ import annotations

from app.adapters.db.repositories.external_event_candidate import (
    SqlExternalEventCandidateRepository,
)
from app.adapters.db.repositories.notification import SqlNotificationRepository
from app.application.external_candidate_ingestion import ingest_unlinked_event
from app.domain.ports.calendar import CalendarConnectorError


class CandidateIngestionError(CalendarConnectorError):
    """Report a rolled-back candidate as a failed calendar event.

    The hardened sync already counts ``CalendarConnectorError`` per event.
    Reuse that isolated outcome while keeping the cause and its potentially
    provider-controlled contents out of application logs.
    """


async def import_candidate_or_match(*, raw, context, new_content_hash) -> bool:
    """Persist a new external event atomically within the integration sync.

    A savepoint prevents partially written slots, mappings or notifications
    from leaking if any one provider event violates a persistence constraint.
    The enclosing integration transaction still owns commit and rollback.
    """
    try:
        async with context.session.begin_nested():
            return await ingest_unlinked_event(
                raw=raw,
                integration=context.integration,
                session=context.session,
                candidate_repo=SqlExternalEventCandidateRepository(context.session),
                instance_repo=context.instance_repo,
                link_repo=context.link_repo,
                notification_repo=SqlNotificationRepository(context.session),
                content_hash=new_content_hash,
            )
    except Exception as exc:
        raise CandidateIngestionError("Individual candidate ingestion failed") from exc
