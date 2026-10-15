# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Pure subject-owned calendar projection; no name-based identity inference."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta

from app.domain.models.event_duty import SERVICE_LEADER_LABEL


@dataclass(frozen=True)
class PersonalCalendarEvent:
    planning_slot_id: uuid.UUID
    uid: str
    title: str
    start_at: datetime
    end_at: datetime
    status: str
    approval_status: str | None
    duties: list[str]
    congregation_id: uuid.UUID | None
    updated_at: datetime


def project_personal_events(
    subject_sub, district_id, slots, instances, leaders, assignments, duties
):
    """Merge verified leader and same-scope duty links into one entry per slot."""
    leader_ids = {
        leader.id
        for leader in leaders
        if leader.user_sub == subject_sub and leader.district_id == district_id
    }
    leader_slots = {
        assignment.planning_slot_id or assignment.event_id
        for assignment in assignments
        if assignment.leader_id in leader_ids
    }
    instances_by_slot = {instance.planning_slot_id: instance for instance in instances}
    result = []
    for slot in slots:
        if slot.district_id != district_id:
            continue
        own_duties = [
            duty
            for duty in duties
            if duty.planning_slot_id == slot.id
            and duty.linked_user_sub == subject_sub
            and duty.district_id == slot.district_id
            and duty.congregation_id == slot.congregation_id
        ]
        labels = sorted({duty.duty_label for duty in own_duties})
        if slot.id in leader_slots:
            labels.insert(0, SERVICE_LEADER_LABEL)
        if not labels:
            continue
        instance = instances_by_slot.get(slot.id)
        start = (
            instance.actual_start_at
            if instance
            else datetime.combine(slot.planning_date, slot.planning_time or time(), tzinfo=UTC)
        )
        end = instance.actual_end_at if instance else start + timedelta(hours=2)
        revisions = [
            slot.updated_at,
            *[d.updated_at for d in own_duties],
        ]
        if instance:
            revisions.append(instance.updated_at)
        status = (
            "CANCELLED"
            if slot.status == "CANCELLED"
            else "TENTATIVE"
            if slot.approval_status == "PLANNED"
            else "ACTIVE"
        )
        result.append(
            PersonalCalendarEvent(
                slot.id,
                f"{slot.id}@nak-bezirksplaner",
                instance.title if instance else slot.title or "Gottesdienst",
                start,
                end,
                status,
                slot.approval_status,
                labels,
                slot.congregation_id,
                max(revisions),
            )
        )
    return result
