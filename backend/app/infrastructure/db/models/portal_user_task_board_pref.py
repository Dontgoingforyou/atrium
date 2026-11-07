"""Персональные настройки отображения канбана задач (порядок, скрытие, подписи)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint

from app.infrastructure.db.base import Base


class PortalUserTaskBoardPref(Base):
    """Настройки доски канбана задач на пользователя (единая глобальная доска)."""

    __tablename__ = "portal_user_task_board_pref"
    __table_args__ = (UniqueConstraint("user_sub", name="uq_portal_user_task_board_pref_user"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    column_order: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    hidden_status_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    title_overrides: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    subtasks_flat: Mapped[bool] = mapped_column(default=False, nullable=False)
    hide_subtasks: Mapped[bool] = mapped_column(default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )
