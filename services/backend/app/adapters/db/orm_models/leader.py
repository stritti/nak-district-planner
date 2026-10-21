# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/db/orm_models/leader.py: Module."""

from __future__ import annotations

import uuid
from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.db.base import Base


class LeaderORM(Base):
    """ORM model for leaderorm."""

    __tablename__ = "leaders"
    __table_args__ = (sa.UniqueConstraint("id", "district_id", name="uq_leaders_id_district"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("districts.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    user_sub: Mapped[str | None] = mapped_column(
        sa.String(512), sa.ForeignKey("users.sub", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    hidden_from_lists: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.false()
    )
    service_end_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    assignments: Mapped[list[LeaderAssignmentORM]] = relationship(
        "LeaderAssignmentORM",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="LeaderAssignmentORM.created_at, LeaderAssignmentORM.id",
    )


class LeaderAssignmentORM(Base):
    """A leader's service in one congregation (or on the district level) with a role."""

    __tablename__ = "leader_assignments"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["leader_id", "district_id"],
            ["leaders.id", "leaders.district_id"],
            ondelete="CASCADE",
            name="fk_leader_assignments_leader_district",
        ),
        sa.Index(
            "uq_leader_assignments_leader_congregation",
            "leader_id",
            "congregation_id",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        sa.Index(
            "uq_leader_assignments_home",
            "leader_id",
            unique=True,
            postgresql_where=sa.text("is_home"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    leader_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    district_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("congregations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    role: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    is_home: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

