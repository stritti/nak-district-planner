"""Small adapter keeping the #375 sync state machine independent of candidate flow."""

from __future__ import annotations

from app.adapters.db.repositories.external_event_candidate import SqlExternalEventCandidateRepository
from app.adapters.db.repositories.notification import SqlNotificationRepository
from app.application.external_candidate_ingestion import ingest_unlinked_event


async def import_candidate_or_match(*, raw, context, new_content_hash) -> bool:
    """Return true only for a safe automatic mapping.

    The enclosing integration sync transaction owns candidate, event and
    notification writes, preserving idempotency across duplicate deliveries.
    """
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
