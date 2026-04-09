from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters.db.repositories.calendar_integration import (
    SqlCalendarIntegrationRepository,
    _domain_to_orm as ci_domain_to_orm,
    _orm_to_domain as ci_orm_to_domain,
)
from app.adapters.db.repositories.congregation import (
    SqlCongregationRepository,
    _orm_to_domain as cong_orm_to_domain,
)
from app.adapters.db.repositories.congregation_group import (
    SqlCongregationGroupRepository,
    _orm_to_domain as group_orm_to_domain,
)
from app.adapters.db.repositories.district import (
    SqlDistrictRepository,
    _orm_to_domain as district_orm_to_domain,
)
from app.adapters.db.repositories.event import (
    SqlEventRepository,
    _domain_to_orm as event_domain_to_orm,
    _orm_to_domain as event_orm_to_domain,
)
from app.adapters.db.repositories.export_token import (
    SqlExportTokenRepository,
    _orm_to_domain as token_orm_to_domain,
)
from app.adapters.db.repositories.invitation_overwrite_request import (
    SqlInvitationOverwriteRequestRepository,
    _orm_to_domain as overwrite_orm_to_domain,
)
from app.adapters.db.repositories.leader import (
    SqlLeaderRepository,
    _orm_to_domain as leader_orm_to_domain,
)
from app.adapters.db.repositories.membership import (
    SqlMembershipRepository,
    _domain_to_orm as membership_domain_to_orm,
    _orm_to_domain as membership_orm_to_domain,
)
from app.adapters.db.repositories.service_assignment import (
    SqlServiceAssignmentRepository,
    _orm_to_domain as assignment_orm_to_domain,
)
from app.adapters.db.repositories.user import (
    SqlUserRepository,
    _domain_to_orm as user_domain_to_orm,
    _orm_to_domain as user_orm_to_domain,
)
from app.domain.models.calendar_integration import (
    CalendarCapability,
    CalendarIntegration,
    CalendarType,
)
from app.domain.models.congregation import Congregation
from app.domain.models.congregation_group import CongregationGroup
from app.domain.models.district import District
from app.domain.models.event import Event, EventStatus
from app.domain.models.export_token import ExportToken, TokenType
from app.domain.models.invitation import InvitationOverwriteRequest, OverwriteDecisionStatus
from app.domain.models.leader import Leader
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment
from app.domain.models.user import User


def _row(**kwargs):
    return type("Row", (), kwargs)()


@pytest.mark.asyncio
async def test_repository_mapping_helpers() -> None:
    now = datetime.now(timezone.utc)
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    user_id = uuid.uuid4()

    d = district_orm_to_domain(
        _row(id=district_id, name="D", state_code="BY", created_at=now, updated_at=now)
    )
    assert d.name == "D"

    c = cong_orm_to_domain(
        _row(
            id=congregation_id,
            name="C",
            district_id=district_id,
            service_times=[{"weekday": 6, "time": "09:30"}],
            created_at=now,
            updated_at=now,
            group_id=None,
            invitation_target_type=None,
            invitation_target_congregation_id=None,
            invitation_external_note=None,
        )
    )
    assert c.name == "C"

    g = group_orm_to_domain(
        _row(id=uuid.uuid4(), name="G", district_id=district_id, created_at=now, updated_at=now)
    )
    assert g.name == "G"

    e = Event.create(
        title="Gottesdienst",
        start_at=now,
        end_at=now,
        district_id=district_id,
        congregation_id=congregation_id,
        status=EventStatus.DRAFT,
    )
    e2 = event_orm_to_domain(
        _row(
            id=e.id,
            title=e.title,
            description=e.description,
            start_at=e.start_at,
            end_at=e.end_at,
            district_id=e.district_id,
            congregation_id=e.congregation_id,
            category=e.category,
            source=e.source,
            status=e.status,
            visibility=e.visibility,
            audiences=e.audiences,
            applicability=e.applicability,
            external_uid=None,
            calendar_integration_id=None,
            content_hash=None,
            generation_slot_key=None,
            invitation_source_congregation_id=None,
            invitation_source_event_id=None,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
    )
    assert e2.id == e.id
    orm = event_domain_to_orm(e)
    assert orm.id == e.id

    leader = Leader.create(name="L", district_id=district_id)
    l2 = leader_orm_to_domain(
        _row(
            id=leader.id,
            name=leader.name,
            district_id=leader.district_id,
            congregation_id=leader.congregation_id,
            rank=leader.rank,
            special_role=leader.special_role,
            user_sub=leader.user_sub,
            email=leader.email,
            phone=leader.phone,
            notes=leader.notes,
            is_active=leader.is_active,
            created_at=leader.created_at,
            updated_at=leader.updated_at,
        )
    )
    assert l2.name == "L"

    membership = Membership.create(
        user_sub="oidc|u1",
        role=Role.PLANNER,
        scope_type=ScopeType.DISTRICT,
        scope_id=district_id,
    )
    m2 = membership_orm_to_domain(
        _row(
            id=membership.id,
            user_sub=membership.user_sub,
            role=membership.role.value,
            scope_type=membership.scope_type.value,
            scope_id=membership.scope_id,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
        )
    )
    assert m2.role == Role.PLANNER
    assert membership_domain_to_orm(membership).id == membership.id

    integration = CalendarIntegration.create(
        district_id=district_id,
        name="I",
        type=CalendarType.ICS,
        credentials_enc="enc",
        capabilities=[CalendarCapability.READ],
    )
    ci2 = ci_orm_to_domain(
        _row(
            id=integration.id,
            district_id=integration.district_id,
            congregation_id=None,
            name=integration.name,
            type=integration.type,
            credentials_enc=integration.credentials_enc,
            sync_interval=integration.sync_interval,
            capabilities=[CalendarCapability.READ.value],
            is_active=integration.is_active,
            last_synced_at=None,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
            default_category=None,
        )
    )
    assert ci2.type == CalendarType.ICS
    assert ci_domain_to_orm(integration).id == integration.id

    token = ExportToken.create(
        label="T",
        token_type=TokenType.PUBLIC,
        district_id=district_id,
        congregation_id=congregation_id,
    )
    t2 = token_orm_to_domain(
        _row(
            id=token.id,
            token=token.token,
            label=token.label,
            token_type=token.token_type,
            district_id=token.district_id,
            congregation_id=token.congregation_id,
            leader_id=token.leader_id,
            created_at=token.created_at,
        )
    )
    assert t2.token == token.token

    assignment = ServiceAssignment.create(
        event_id=e.id,
        leader_name="Pr. X",
        status=AssignmentStatus.ASSIGNED,
    )
    a2 = assignment_orm_to_domain(
        _row(
            id=assignment.id,
            event_id=assignment.event_id,
            leader_id=assignment.leader_id,
            leader_name=assignment.leader_name,
            status=assignment.status,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
        )
    )
    assert a2.status == AssignmentStatus.ASSIGNED

    overwrite = InvitationOverwriteRequest.create(
        invitation_id=uuid.uuid4(),
        source_event_id=e.id,
        target_event_id=e.id,
        proposed_title="N",
        proposed_start_at=now,
        proposed_end_at=now,
        proposed_description=None,
        proposed_category=None,
    )
    o2 = overwrite_orm_to_domain(
        _row(
            id=overwrite.id,
            invitation_id=overwrite.invitation_id,
            source_event_id=overwrite.source_event_id,
            target_event_id=overwrite.target_event_id,
            proposed_title=overwrite.proposed_title,
            proposed_start_at=overwrite.proposed_start_at,
            proposed_end_at=overwrite.proposed_end_at,
            proposed_description=None,
            proposed_category=None,
            status=overwrite.status.value,
            decided_at=None,
            created_at=overwrite.created_at,
            updated_at=overwrite.updated_at,
        )
    )
    assert o2.status == OverwriteDecisionStatus.PENDING_OVERWRITE

    user = User(sub="oidc|u", email="u@example.com", username="u")
    uo = user_domain_to_orm(user)
    assert uo.sub == "oidc|u"
    ud = user_orm_to_domain(
        _row(
            sub="oidc|u",
            email="u@example.com",
            username="u",
            name=None,
            given_name=None,
            family_name=None,
            is_superadmin=False,
            created_at=now,
        )
    )
    assert ud.email == "u@example.com"


@pytest.mark.asyncio
async def test_repository_methods_with_mocked_session() -> None:
    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()

    # district
    district_repo = SqlDistrictRepository(session)
    assert await district_repo.get(uuid.uuid4()) is None
    session.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=lambda: []))
    )
    assert await district_repo.list_all() == []
    await district_repo.save(District.create(name="D"))

    # congregation/group
    cong_repo = SqlCongregationRepository(session)
    assert await cong_repo.list_by_ids([]) == []
    await cong_repo.save(Congregation.create(name="C", district_id=uuid.uuid4()))

    group_repo = SqlCongregationGroupRepository(session)
    await group_repo.delete(uuid.uuid4())

    # event repository
    event_repo = SqlEventRepository(session)
    await event_repo.list()
    session.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=lambda: []))
    )
    await event_repo.list_linked_by_source_event(uuid.uuid4())
    session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    await event_repo.get_by_generation_slot_key(
        district_id=uuid.uuid4(), congregation_id=uuid.uuid4(), generation_slot_key="k"
    )
    session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    await event_repo.get_matching_draft_service_slot(
        district_id=uuid.uuid4(),
        congregation_id=uuid.uuid4(),
        start_at=datetime.now(timezone.utc),
        end_at=datetime.now(timezone.utc),
    )

    # export token
    token_repo = SqlExportTokenRepository(session)
    await token_repo.list_by_district(uuid.uuid4())
    await token_repo.list_all()
    await token_repo.delete(uuid.uuid4())

    # overwrite requests
    overwrite_repo = SqlInvitationOverwriteRequestRepository(session)
    await overwrite_repo.list_open_by_district(uuid.uuid4())
    await overwrite_repo.list_open_by_source_event(uuid.uuid4())
    assert await overwrite_repo.set_status(uuid.uuid4(), OverwriteDecisionStatus.ACCEPTED) is None

    # leader
    leader_repo = SqlLeaderRepository(session)
    await leader_repo.list_by_district(uuid.uuid4(), active_only=True)
    session.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(first=lambda: None))
    )
    await leader_repo.get_by_user_sub("oidc|u", district_id=uuid.uuid4())
    await leader_repo.delete(uuid.uuid4())

    # assignment
    assignment_repo = SqlServiceAssignmentRepository(session)
    assert await assignment_repo.list_by_events([]) == []

    # user
    user_repo = SqlUserRepository(session)
    session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    assert await user_repo.get_by_sub("missing") is None
    assert await user_repo.get_by_email("missing") is None

    u = User(sub="oidc|u", email="u@example.com", username="u")
    await user_repo.save(u)
    await user_repo.has_any_user()

    # membership
    membership_repo = SqlMembershipRepository(session)
    await membership_repo.get_all_by_user("oidc|u")
    await membership_repo.get_all_by_scope(ScopeType.DISTRICT, uuid.uuid4())
    await membership_repo.delete(uuid.uuid4())
