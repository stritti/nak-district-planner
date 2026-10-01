"""Alert district administrators when calendar synchronisation keeps failing.

The Celery task retries a failing sync with exponential backoff. Only when all
retries are exhausted does it raise an alert, so transient provider hiccups do
not produce notifications. Alerts are de-duplicated against unread alerts for
the same integration because Celery beat keeps re-dispatching an integration
until it syncs successfully.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from app.domain.models.notification import Notification, NotificationType
from app.domain.ports.repositories import CalendarIntegrationRepository, NotificationRepository

logger = logging.getLogger(__name__)

SYNC_FAILURE_ALERT_KIND = "calendar_sync_failure"

# Newest unread notifications inspected for an existing alert. A district with
# more unread notifications than this may receive a duplicate, which is an
# acceptable trade-off compared to an unbounded scan.
DEDUPLICATION_WINDOW = 50


@dataclass(frozen=True, slots=True)
class SyncFailure:
    """Provider-neutral description of a sync that exhausted all retries."""

    integration_id: uuid.UUID
    error_class: str
    attempts: int


class SyncFailureAlerter:
    """Create one SYSTEM notification per unresolved integration failure."""

    def __init__(
        self,
        integrations: CalendarIntegrationRepository,
        notifications: NotificationRepository,
    ) -> None:
        self._integrations = integrations
        self._notifications = notifications

    async def alert(self, failure: SyncFailure) -> Notification | None:
        """Persist an alert and return it, or ``None`` when no alert was needed."""
        integration = await self._integrations.get(failure.integration_id)
        if integration is None:
            logger.warning(
                "Sync failure alert skipped: integration_id=%s not found",
                failure.integration_id,
                extra={"integration_id": str(failure.integration_id)},
            )
            return None
        if await self._has_unread_alert(integration.district_id, failure.integration_id):
            return None

        notification = Notification.create(
            district_id=integration.district_id,
            congregation_id=integration.congregation_id,
            type=NotificationType.SYSTEM,
            title=f"Kalender-Synchronisation fehlgeschlagen: {integration.name}",
            body=(
                f"Die Synchronisation ist nach {failure.attempts} Versuchen fehlgeschlagen "
                f"({failure.error_class}). Bitte Zugangsdaten und Erreichbarkeit der "
                "Kalenderquelle prüfen."
            ),
            payload={
                "kind": SYNC_FAILURE_ALERT_KIND,
                "integration_id": str(failure.integration_id),
                "error_class": failure.error_class,
                "attempts": failure.attempts,
            },
        )
        await self._notifications.save(notification)
        return notification

    async def _has_unread_alert(self, district_id: uuid.UUID, integration_id: uuid.UUID) -> bool:
        unread, _ = await self._notifications.list_by_district(
            district_id, unread_only=True, limit=DEDUPLICATION_WINDOW
        )
        return any(_is_alert_for(notification, integration_id) for notification in unread)


def _is_alert_for(notification: Notification, integration_id: uuid.UUID) -> bool:
    payload = notification.payload or {}
    return (
        notification.type == NotificationType.SYSTEM
        and payload.get("kind") == SYNC_FAILURE_ALERT_KIND
        and payload.get("integration_id") == str(integration_id)
    )
