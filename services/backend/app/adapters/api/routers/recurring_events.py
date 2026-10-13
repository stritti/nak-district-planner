# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Opt-in recurring-event templates and explicitly controlled monthly checklist."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
from app.adapters.api.recurring_event_policy import (
    _is_congregation_admin,
    _require_read,
    _require_write,
    _visible,
)
from app.adapters.api.schemas.recurring_events import (
    BulkOccurrenceAcceptRequest,
    BulkOccurrenceResponse,
    BulkOccurrenceResult,
    ChecklistItemResponse,
    ChecklistResponse,
    OccurrenceAcceptRequest,
    OccurrenceActionRequest,
    OccurrenceActionResult,
    OccurrenceResolveRequest,
    RecurringTemplateCreate,
    RecurringTemplatePatch,
    RecurringTemplateResponse,
    TemplateListResponse,
)
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.recurring_event import SqlRecurringEventRepository
from app.application.recurring_event_service import (
    InvalidOccurrenceError,
    OccurrenceConflictError,
    RecurringEventService,
    StaleTemplateError,
)
from app.domain.models.recurring_event_template import (
    AmbiguousLocalTimeError,
    ChecklistStatus,
    NonexistentLocalTimeError,
    RecurringEventDecision,
    RecurringEventTemplate,
)

router = APIRouter(prefix="/api/v1/districts/{district_id}", tags=["recurring-events"])


def _repository(session: AsyncSession) -> SqlRecurringEventRepository:
    return SqlRecurringEventRepository(session)


def _service(session: AsyncSession) -> RecurringEventService:
    return RecurringEventService(
        session,
        _repository(session),
        SqlPlanningSlotRepository(session),
        SqlEventInstanceRepository(session),
        integrity_error_type=IntegrityError,
    )


async def _validate_congregation(
    session: AsyncSession,
    district_id: uuid.UUID,
    congregation_id: uuid.UUID | None,
) -> None:
    if congregation_id is not None:
        congregation = await SqlCongregationRepository(session).get(congregation_id)
        if congregation is None or congregation.district_id != district_id:
            raise HTTPException(status_code=403, detail="Gemeinde gehört nicht zum Bezirk.")


async def _validate_distribution(
    session: AsyncSession,
    entry: RecurringEventTemplate,
) -> None:
    if entry.congregation_id is not None:
        return
    if not entry.applicability or entry.applicability == ("all",):
        return
    allowed = {
        congregation.id
        for congregation in await SqlCongregationRepository(session).list_by_district(
            entry.district_id
        )
    }
    if {uuid.UUID(value) for value in entry.applicability} - allowed:
        raise HTTPException(status_code=403, detail="Verteilung enthält fremde Gemeinden.")


def _response(entry: RecurringEventTemplate) -> RecurringTemplateResponse:
    return RecurringTemplateResponse.model_validate(entry, from_attributes=True)


def _occurrence_response(
    decision: RecurringEventDecision | None,
    template_id: uuid.UUID,
    occurrence_day: date,
) -> OccurrenceActionResult:
    return OccurrenceActionResult(
        template_id=template_id,
        occurrence_local_date=occurrence_day,
        status=ChecklistStatus(decision.status.value) if decision else ChecklistStatus.OPEN,
        planning_slot_id=decision.planning_slot_id if decision else None,
    )


def _handle_occurrence_error(exc: ValueError) -> HTTPException:
    if isinstance(
        exc, (
            OccurrenceConflictError,
            StaleTemplateError,
            InvalidOccurrenceError,
            AmbiguousLocalTimeError,
            NonexistentLocalTimeError,
        ),
    ):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


def _bulk_error_code(exc: ValueError) -> str:
    """Return a stable public error code, never exception or database details."""
    if isinstance(exc, StaleTemplateError):
        return "STALE_TEMPLATE"
    if isinstance(exc, OccurrenceConflictError):
        return "OCCURRENCE_CONFLICT"
    if isinstance(exc, InvalidOccurrenceError):
        return "INVALID_OCCURRENCE"
    if isinstance(exc, AmbiguousLocalTimeError):
        return "AMBIGUOUS_LOCAL_TIME"
    if isinstance(exc, NonexistentLocalTimeError):
        return "NONEXISTENT_LOCAL_TIME"
    return "INVALID_INPUT"


async def _mutable_entry(
    repo: SqlRecurringEventRepository,
    district_id: uuid.UUID,
    template_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
) -> RecurringEventTemplate:
    entry = await repo.get_template(template_id)
    if entry is None or entry.district_id != district_id:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")
    _require_write(auth, district_id, entry.congregation_id)
    return entry


@router.get("/recurring-event-templates", response_model=TemplateListResponse)
async def list_recurring_templates(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TemplateListResponse:
    allowed = await _require_read(auth, district_id, session)
    rows, total = await _repository(session).list_visible_templates_page(
        district_id, visible_congregation_ids=allowed, limit=limit, offset=offset,
    )
    return TemplateListResponse(
        items=[_response(entry) for entry in rows], total=total, limit=limit, offset=offset,
    )


@router.post(
    "/recurring-event-templates",
    response_model=RecurringTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recurring_template(
    district_id: uuid.UUID,
    body: RecurringTemplateCreate,
    auth: CurrentUserWithMemberships,
    session: DbSession,
) -> RecurringTemplateResponse:
    _require_write(auth, district_id, body.congregation_id)
    await _validate_congregation(session, district_id, body.congregation_id)
    try:
        entry = RecurringEventTemplate(
            id=uuid.uuid4(),
            district_id=district_id,
            title=body.title,
            category=body.category,
            start_time=body.start_time,
            duration_minutes=body.duration_minutes,
            recurrence=body.recurrence.to_domain(),
            congregation_id=body.congregation_id,
            description=body.description,
            applicability=tuple(body.applicability),
            excluded_dates=tuple(body.excluded_dates),
            active_from=body.active_from,
            active_until=body.active_until,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await _validate_distribution(session, entry)
    await _repository(session).save_template(entry)
    return _response(entry)


@router.patch(
    "/recurring-event-templates/{template_id}", response_model=RecurringTemplateResponse
)
async def update_recurring_template(
    district_id: uuid.UUID,
    template_id: uuid.UUID,
    body: RecurringTemplatePatch,
    auth: CurrentUserWithMemberships,
    session: DbSession,
) -> RecurringTemplateResponse:
    repo = _repository(session)
    entry = await repo.get_template(template_id, for_update=True)
    if entry is None or entry.district_id != district_id:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")
    _require_write(auth, district_id, entry.congregation_id)
    if body.expected_revision != entry.revision:
        raise HTTPException(status_code=409, detail="Vorlage wurde geändert.")
    changes = {
        key: getattr(body, key)
        for key in body.model_fields_set
        if key != "expected_revision"
    }
    for key, value in changes.items():
        if value is None and key not in ("description", "active_from", "active_until"):
            raise HTTPException(status_code=422, detail=f"{key} darf nicht null sein.")
    if "recurrence" in changes:
        changes["recurrence"] = body.recurrence.to_domain()
    if "applicability" in changes:
        changes["applicability"] = tuple(body.applicability)
    if "excluded_dates" in changes:
        changes["excluded_dates"] = tuple(body.excluded_dates)
    try:
        updated = replace(entry, **changes, revision=entry.revision + 1)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await _validate_distribution(session, updated)
    await repo.save_template(updated)
    return _response(updated)


@router.get("/recurring-event-checklist", response_model=ChecklistResponse)
async def list_recurring_checklist(
    district_id: uuid.UUID,
    auth: CurrentUserWithMemberships,
    session: DbSession,
    year: int = Query(ge=1900, le=9999),
    month: int = Query(ge=1, le=12),
    congregation_id: uuid.UUID | None = None,
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=255),
    approval_status: ChecklistStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ChecklistResponse:
    allowed = await _require_read(auth, district_id, session)
    await _validate_congregation(session, district_id, congregation_id)
    if congregation_id is not None and allowed is not None and congregation_id not in allowed:
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diese Gemeinde.")
    entries = [
        entry for entry in await _repository(session).list_templates(district_id)
        if _visible(auth, entry)
    ]
    if congregation_id is not None:
        entries = [
            entry for entry in entries
            if entry.congregation_id == congregation_id
            or (
                entry.congregation_id is None
                and (
                    "all" in entry.applicability
                    or str(congregation_id) in entry.applicability
                )
            )
        ]
    page = await _service(session).list_month(
        district_id, year, month, templates=entries, query=q, category=category,
        status_filter=approval_status, limit=limit, offset=offset,
    )
    return ChecklistResponse(
        items=[
            ChecklistItemResponse(
                template_id=row.template.id,
                district_id=row.template.district_id,
                congregation_id=row.template.congregation_id,
                title=row.template.title,
                description=row.template.description,
                category=row.template.category,
                occurrence_local_date=row.occurrence_local_date,
                start_time=row.template.start_time,
                duration_minutes=row.template.duration_minutes,
                template_revision=row.template.revision,
                status=row.status,
                decision_status=row.decision_status,
                planning_slot_id=row.planning_slot_id,
                reason=row.reason,
            ) for row in page.items
        ],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
        counts=page.counts,
    )


@router.post(
    "/recurring-event-checklist/accept", response_model=OccurrenceActionResult
)
async def accept_recurring_occurrence(
    district_id: uuid.UUID,
    body: OccurrenceAcceptRequest,
    auth: CurrentUserWithMemberships,
    session: DbSession,
) -> OccurrenceActionResult:
    entry = await _mutable_entry(_repository(session), district_id, body.template_id, auth)
    try:
        decision = await _service(session).accept(
            entry, body.occurrence_local_date,
            expected_revision=body.template_revision, created_by=auth.user_sub,
            local_date_override=body.local_date_override,
            local_time_override=body.local_time_override,
            title_override=body.title_override,
            description_override=body.description_override,
            duration_minutes_override=body.duration_minutes_override,
            fold=body.fold,
        )
    except ValueError as exc:
        raise _handle_occurrence_error(exc) from exc
    return _occurrence_response(decision, entry.id, body.occurrence_local_date)


@router.post("/recurring-event-checklist/skip", response_model=OccurrenceActionResult)
async def skip_recurring_occurrence(
    district_id: uuid.UUID,
    body: OccurrenceActionRequest,
    auth: CurrentUserWithMemberships,
    session: DbSession,
) -> OccurrenceActionResult:
    entry = await _mutable_entry(_repository(session), district_id, body.template_id, auth)
    try:
        decision = await _service(session).skip(
            entry, body.occurrence_local_date,
            expected_revision=body.template_revision, created_by=auth.user_sub,
        )
    except ValueError as exc:
        raise _handle_occurrence_error(exc) from exc
    return _occurrence_response(decision, entry.id, body.occurrence_local_date)


@router.post("/recurring-event-checklist/reopen", response_model=OccurrenceActionResult)
async def reopen_recurring_occurrence(
    district_id: uuid.UUID,
    body: OccurrenceActionRequest,
    auth: CurrentUserWithMemberships,
    session: DbSession,
) -> OccurrenceActionResult:
    entry = await _mutable_entry(_repository(session), district_id, body.template_id, auth)
    try:
        await _service(session).reopen(
            entry, body.occurrence_local_date, expected_revision=body.template_revision
        )
    except ValueError as exc:
        raise _handle_occurrence_error(exc) from exc
    return _occurrence_response(None, entry.id, body.occurrence_local_date)


@router.post("/recurring-event-checklist/resolve", response_model=OccurrenceActionResult)
async def resolve_recurring_occurrence(
    district_id: uuid.UUID,
    body: OccurrenceResolveRequest,
    auth: CurrentUserWithMemberships,
    session: DbSession,
) -> OccurrenceActionResult:
    entry = await _mutable_entry(_repository(session), district_id, body.template_id, auth)
    try:
        decision = await _service(session).resolve_missing_slot(
            entry, body.occurrence_local_date,
            expected_revision=body.template_revision,
            action=body.action, slot_id=body.planning_slot_id,
        )
    except ValueError as exc:
        raise _handle_occurrence_error(exc) from exc
    return _occurrence_response(decision, entry.id, body.occurrence_local_date)


@router.post(
    "/recurring-event-checklist/bulk-accept",
    response_model=BulkOccurrenceResponse,
)
async def bulk_accept_recurring_occurrences(
    district_id: uuid.UUID,
    body: BulkOccurrenceAcceptRequest,
    auth: CurrentUserWithMemberships,
    session: DbSession,
) -> BulkOccurrenceResponse:
    repo = _repository(session)
    # Authorize the entire selection before committing any of its items.
    entries = {
        item.template_id: await _mutable_entry(
            repo, district_id, item.template_id, auth
        ) for item in body.items
    }
    service = _service(session)
    results = []
    for item in body.items:
        try:
            decision = await service.accept(
                entries[item.template_id], item.occurrence_local_date,
                expected_revision=item.template_revision,
                created_by=auth.user_sub,
                local_date_override=item.local_date_override,
                local_time_override=item.local_time_override,
                title_override=item.title_override,
                description_override=item.description_override,
                duration_minutes_override=item.duration_minutes_override,
                fold=item.fold,
            )
            results.append(
                BulkOccurrenceResult(
                    template_id=item.template_id,
                    occurrence_local_date=item.occurrence_local_date,
                    status=ChecklistStatus.ACCEPTED,
                    planning_slot_id=decision.planning_slot_id,
                )
            )
        except ValueError as exc:
            results.append(
                BulkOccurrenceResult(
                    template_id=item.template_id,
                    occurrence_local_date=item.occurrence_local_date,
                    status=None, error=_bulk_error_code(exc),
                )
            )
    return BulkOccurrenceResponse(results=results)
