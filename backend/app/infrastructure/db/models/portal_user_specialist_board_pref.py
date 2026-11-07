"""Персональный порядок колонок канбана специалистов."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint

from app.infrastructure.db.base import Base


class PortalUserSpecialistBoardPref(Base):
    __tablename__ = "portal_user_specialist_board_pref"
    __table_args__ = (UniqueConstraint("user_sub", name="uq_portal_user_specialist_board_pref_user"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    column_order: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    hidden_column_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )
