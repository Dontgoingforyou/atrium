"""Статусы специалистов — глобальный справочник (аналог тегов)."""

from __future__ import annotations

import uuid

from sqlalchemy import String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class PortalSpecialistStatus(Base):
    """Статус специалиста на доске воронки.

    Глобальный справочник: любой менеджер может создать новый статус,
    редактировать/удалять — только администратор портала.
    """

    __tablename__ = "portal_specialist_status"
    __table_args__ = (UniqueConstraint("title", name="uq_portal_specialist_status_title"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(30), nullable=False, default="#888888", server_default="#888888")

    def __str__(self) -> str:
        return self.title
