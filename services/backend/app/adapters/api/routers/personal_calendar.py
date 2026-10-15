# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Authenticated, district-scoped personal calendar adapter."""

import uuid
from datetime import date
from types import SimpleNamespace

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.adapters.api.deps import CurrentUserWithMemberships, DbSession
from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.orm_models.user import UserORM
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.membership import SqlMembershipRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.application.personal_calendar import PersonalCalendarEvent, project_personal_events

router = APIRouter(prefix="/api/v1/personal-calendar", tags=["personal-calendar"])


def allowed_personal_scopes(auth, district_id, congregation_ids):
    from app.domain.models.role import Role

    memberships = [m for m in auth.memberships if getattr(m, "role", None) in set(Role)]
    district_access = auth.user.is_superadmin or any(
        m.scope_type == "DISTRICT" and m.scope_id == district_id for m in memberships
    )
    congregations = {
        m.scope_id
        for m in memberships
        if m.scope_type == "CONGREGATION" and m.scope_id in congregation_ids
    }
    return district_access, congregations


async def personal_subject_context(session, subject_sub, district_id):
    """Resolve an existing OIDC subject and its current DB memberships every time."""
    user = (
        await session.execute(select(UserORM).where(UserORM.sub == subject_sub))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "Persönlicher Kalender nicht verfügbar")
    memberships = await SqlMembershipRepository(session).get_all_by_user(subject_sub)
    congregations = set(
        (
            await session.execute(
                select(CongregationORM.id).where(CongregationORM.district_id == district_id)
            )
        ).scalars()
    )
    auth = SimpleNamespace(user=user, memberships=memberships)
    district_access, congregation_access = allowed_personal_scopes(auth, district_id, congregations)
    if not district_access and not congregation_access:
        raise HTTPException(404, "Persönlicher Kalender nicht verfügbar")
    return district_access, congregation_access


async def load_personal_events(session, subject_sub, district_id, from_date, to_date):
    from app.adapters.db.repositories.event_duties import SqlEventDutiesRepository

    district_access, congregation_access = await personal_subject_context(
        session, subject_sub, district_id
    )
    slots = await SqlPlanningSlotRepository(session).list_for_date_range(
        district_id=district_id, from_date=from_date, to_date=to_date
    )
    slots = [s for s in slots if district_access or s.congregation_id in congregation_access]
    ids = [s.id for s in slots]
    instances = await SqlEventInstanceRepository(session).list_by_planning_slots(ids) if ids else []
    assignments = (
        await SqlServiceAssignmentRepository(session).list_by_planning_slots(ids) if ids else []
    )
    leaders = await SqlLeaderRepository(session).list_by_district(district_id)
    duties = await SqlEventDutiesRepository(session).list_assignments(ids) if ids else []
    return project_personal_events(
        subject_sub, district_id, slots, instances, leaders, assignments, duties
    )


@router.get("/events", response_model=list[PersonalCalendarEvent])
async def personal_events(
    auth: CurrentUserWithMemberships,
    session: DbSession,
    district_id: uuid.UUID,
    from_date: date,
    to_date: date,
):
    if to_date < from_date or (to_date - from_date).days > 1096:
        raise HTTPException(422, "Ungültiger Zeitraum")
    return await load_personal_events(session, auth.user_sub, district_id, from_date, to_date)
