"""Колонки воронки специалистов (глобальный справочник, управляет только администратор)."""

from __future__ import annotations

import uuid

from sqlalchemy import Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class PortalSpecialistColumn(Base):
    """Этап воронки специалистов.

    Глобальный справочник: все менеджеры видят одинаковый набор колонок.
    Создавать / редактировать / удалять может только администратор портала.
    """

    __tablename__ = "portal_specialist_column"
    __table_args__ = (UniqueConstraint("key", name="uq_portal_specialist_column_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    color: Mapped[str] = mapped_column(String(30), nullable=False, default="#888888", server_default="#888888")
    position: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, server_default="0", index=True)
    jira_status_id: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True, index=True)
