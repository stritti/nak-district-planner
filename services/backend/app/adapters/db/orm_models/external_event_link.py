# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/db/orm_models/external_event_link.py: Module."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base


class ExternalEventLinkORM(Base):
    """ORM model for ExternalEventLink — sync provenance mapping."""

    __tablename__ = "external_event_links"
    __table_args__ = (
        Index(
            "ix_external_event_links_provider_integration_event",
            "provider",
            "external_event_id",
            "calendar_integration_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_instances.id", ondelete="CASCADE"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(500), nullable=False)
    calendar_integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calendar_integrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    last_synced_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revision_marker: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    last_synced_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider_resource_id: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    deletion_origin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deletion_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tombstoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
