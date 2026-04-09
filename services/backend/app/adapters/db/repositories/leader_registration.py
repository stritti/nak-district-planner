from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.leader_registration import LeaderRegistrationORM
from app.domain.models.leader import LeaderRank, SpecialRole
from app.domain.models.membership import ScopeType
from app.domain.models.leader_registration import LeaderRegistration, RegistrationStatus
from app.domain.models.role import Role
from app.domain.ports.repositories import LeaderRegistrationRepository


def _orm_to_domain(row: LeaderRegistrationORM) -> LeaderRegistration:
    return LeaderRegistration(
        id=row.id,
        district_id=row.district_id,
        name=row.name,
        email=row.email,
        rank=LeaderRank(row.rank) if row.rank else None,
        congregation_id=row.congregation_id,
        special_role=SpecialRole(row.special_role) if row.special_role else None,
        phone=row.phone,
        notes=row.notes,
        status=RegistrationStatus(row.status),
        rejection_reason=row.rejection_reason,
        user_sub=row.user_sub,
        assigned_role=Role(row.assigned_role) if row.assigned_role else None,
        assigned_scope_type=ScopeType(row.assigned_scope_type) if row.assigned_scope_type else None,
        assigned_scope_id=row.assigned_scope_id,
        approved_by_sub=row.approved_by_sub,
        approved_at=row.approved_at,
        idp_provision_status=row.idp_provision_status,
        idp_provision_error=row.idp_provision_error,
        idp_provisioned_at=row.idp_provisioned_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlLeaderRegistrationRepository(LeaderRegistrationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, registration_id: uuid.UUID) -> LeaderRegistration | None:
        row = await self._session.get(LeaderRegistrationORM, registration_id)
        return _orm_to_domain(row) if row else None

    async def list_by_district(
        self,
        district_id: uuid.UUID,
        status: RegistrationStatus | None = None,
    ) -> list[LeaderRegistration]:
        stmt = select(LeaderRegistrationORM).where(LeaderRegistrationORM.district_id == district_id)
        if status is not None:
            stmt = stmt.where(LeaderRegistrationORM.status == status.value)
        stmt = stmt.order_by(LeaderRegistrationORM.created_at.desc())
        result = await self._session.execute(stmt)
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def count_by_district(
        self,
        district_id: uuid.UUID,
        status: RegistrationStatus | None = None,
    ) -> int:
        stmt = select(func.count(LeaderRegistrationORM.id)).where(
            LeaderRegistrationORM.district_id == district_id
        )
        if status is not None:
            stmt = stmt.where(LeaderRegistrationORM.status == status.value)
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def save(self, registration: LeaderRegistration) -> None:
        existing = await self._session.get(LeaderRegistrationORM, registration.id)
        if existing is None:
            row = LeaderRegistrationORM()
            self._session.add(row)
        else:
            row = existing
        row.id = registration.id
        row.district_id = registration.district_id
        row.name = registration.name
        row.email = registration.email
        row.rank = registration.rank.value if registration.rank else None
        row.congregation_id = registration.congregation_id
        row.special_role = registration.special_role.value if registration.special_role else None
        row.phone = registration.phone
        row.notes = registration.notes
        row.status = registration.status.value
        row.rejection_reason = registration.rejection_reason
        row.user_sub = registration.user_sub
        row.assigned_role = registration.assigned_role.value if registration.assigned_role else None
        row.assigned_scope_type = (
            registration.assigned_scope_type.value if registration.assigned_scope_type else None
        )
        row.assigned_scope_id = registration.assigned_scope_id
        row.approved_by_sub = registration.approved_by_sub
        row.approved_at = registration.approved_at
        row.idp_provision_status = registration.idp_provision_status
        row.idp_provision_error = registration.idp_provision_error
        row.idp_provisioned_at = registration.idp_provisioned_at
        row.created_at = registration.created_at
        row.updated_at = registration.updated_at
        await self._session.flush()

    async def delete(self, registration_id: uuid.UUID) -> None:
        row = await self._session.get(LeaderRegistrationORM, registration_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()

    async def list_approved_unlinked_by_email(self, email: str) -> list[LeaderRegistration]:
        result = await self._session.execute(
            select(LeaderRegistrationORM).where(
                and_(
                    LeaderRegistrationORM.status == RegistrationStatus.APPROVED.value,
                    LeaderRegistrationORM.user_sub.is_(None),
                    func.lower(LeaderRegistrationORM.email) == email.strip().lower(),
                )
            )
        )
        rows = result.scalars().all()
        return [_orm_to_domain(row) for row in rows]
