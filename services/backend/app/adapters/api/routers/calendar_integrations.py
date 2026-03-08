from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.adapters.api.deps import ApiKeyGuard, DbSession
from app.adapters.api.schemas.calendar_integration import (
    CalendarIntegrationCreate,
    CalendarIntegrationListResponse,
    CalendarIntegrationResponse,
    CalendarIntegrationUpdate,
    SyncResult,
)
from app.adapters.db.repositories.calendar_integration import SqlCalendarIntegrationRepository
from app.application.crypto import CryptoError, encrypt_credentials
from app.application.sync_service import run_sync
from app.domain.models.calendar_integration import CalendarIntegration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/calendar-integrations", tags=["calendar-integrations"])


def _to_response(integration: CalendarIntegration) -> CalendarIntegrationResponse:
    return CalendarIntegrationResponse(
        id=integration.id,
        district_id=integration.district_id,
        congregation_id=integration.congregation_id,
        name=integration.name,
        type=integration.type,
        sync_interval=integration.sync_interval,
        capabilities=integration.capabilities,
        is_active=integration.is_active,
        last_synced_at=integration.last_synced_at,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
        default_category=integration.default_category,
    )


@router.post("", response_model=CalendarIntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_integration(
    body: CalendarIntegrationCreate,
    _: ApiKeyGuard,
    db: DbSession,
) -> CalendarIntegrationResponse:
    credentials_enc = encrypt_credentials(body.credentials)
    integration = CalendarIntegration.create(
        district_id=body.district_id,
        congregation_id=body.congregation_id,
        name=body.name,
        type=body.type,
        credentials_enc=credentials_enc,
        sync_interval=body.sync_interval,
        capabilities=body.capabilities,
        default_category=body.default_category,
    )
    repo = SqlCalendarIntegrationRepository(db)
    await repo.save(integration)
    return _to_response(integration)


@router.get("", response_model=CalendarIntegrationListResponse)
async def list_calendar_integrations(
    _: ApiKeyGuard,
    db: DbSession,
    district_id: uuid.UUID | None = None,
) -> CalendarIntegrationListResponse:
    repo = SqlCalendarIntegrationRepository(db)
    if district_id is not None:
        items = await repo.list_by_district(district_id)
    else:
        items = await repo.list_active()
    return CalendarIntegrationListResponse(
        items=[_to_response(i) for i in items],
        total=len(items),
    )


@router.post("/{integration_id}/sync", response_model=SyncResult)
async def trigger_sync(
    integration_id: uuid.UUID,
    _: ApiKeyGuard,
    db: DbSession,
) -> SyncResult:
    """Trigger an immediate synchronisation for one integration (UC-02).

    Runs synchronously in the request context so the caller receives the
    result directly.  For large feeds prefer dispatching via Celery:
    `sync_calendar_integration.delay(str(integration_id))`.
    """
    repo = SqlCalendarIntegrationRepository(db)
    integration = await repo.get(integration_id)
    if integration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

    try:
        summary = await run_sync(integration_id, db)
    except (ValueError, CryptoError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SyncResult(
        integration_id=integration_id,
        created=summary["created"],
        updated=summary["updated"],
        cancelled=summary["cancelled"],
    )


@router.patch("/{integration_id}", response_model=CalendarIntegrationResponse)
async def update_calendar_integration(
    integration_id: uuid.UUID,
    body: CalendarIntegrationUpdate,
    _: ApiKeyGuard,
    db: DbSession,
) -> CalendarIntegrationResponse:
    repo = SqlCalendarIntegrationRepository(db)
    integration = await repo.get(integration_id)
    if integration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Integration nicht gefunden"
        )

    fields = body.model_fields_set
    if "name" in fields and body.name is not None:
        integration.name = body.name
    if "credentials" in fields and body.credentials is not None:
        integration.credentials_enc = encrypt_credentials(body.credentials)
    if "sync_interval" in fields and body.sync_interval is not None:
        integration.sync_interval = body.sync_interval
    if "capabilities" in fields and body.capabilities is not None:
        integration.capabilities = body.capabilities
    if "default_category" in fields:
        integration.default_category = body.default_category

    integration.updated_at = datetime.now(timezone.utc)
    await repo.save(integration)
    return _to_response(integration)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_integration(
    integration_id: uuid.UUID,
    _: ApiKeyGuard,
    db: DbSession,
) -> None:
    repo = SqlCalendarIntegrationRepository(db)
    if not await repo.get(integration_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Integration nicht gefunden"
        )
    await repo.delete(integration_id)
