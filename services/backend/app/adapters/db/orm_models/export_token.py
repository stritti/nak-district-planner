from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base
from app.domain.models.export_token import TokenType

_TokenTypeEnum = sa.Enum(TokenType, name="tokentype", create_type=False)


class ExportTokenORM(Base):
    __tablename__ = "export_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(sa.String(64), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    token_type: Mapped[TokenType] = mapped_column(_TokenTypeEnum, nullable=False)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("districts.id", ondelete="CASCADE"),
        nullable=False,
    )
    congregation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("congregations.id", ondelete="CASCADE"),
        nullable=True,
    )
    leader_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("leaders.id", ondelete="CASCADE"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
