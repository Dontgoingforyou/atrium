"""Запись специалиста на доске воронки конкретного менеджера."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
    from app.infrastructure.db.models.portal_specialist_status import PortalSpecialistStatus
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalManagerSpecialist(Base):
    """Специалист, добавленный менеджером на свою доску воронки.

    Связь manager_sub → specialist_sub уникальна:
    один специалист не может дважды оказаться на доске одного менеджера.
    """

    __tablename__ = "portal_manager_specialist"
    __table_args__ = (
        UniqueConstraint("manager_sub", "specialist_sub", name="uq_portal_manager_specialist_pair"),
        Index("ix_portal_manager_specialist_board", "manager_sub", "column_key", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manager_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    specialist_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    column_key: Mapped[str] = mapped_column(String(100), nullable=False, default="new", server_default="new")
    position: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, server_default="0")
    version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1, server_default="1")
    status_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_specialist_status.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # lazy="noload": отношения не загружаются автоматически при SELECT через API.
    # SQLAdmin загружает их явно через selectinload в list_query / details_query
    # (см. portal_specialists/admin/board.py → PortalManagerSpecialistAdmin).
    status: Mapped[PortalSpecialistStatus | None] = relationship(
        "PortalSpecialistStatus",
        foreign_keys=[status_id],
        lazy="noload",
    )
    manager_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalManagerSpecialist.manager_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="noload",
        overlaps="specialist_profile",
    )
    specialist_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalManagerSpecialist.specialist_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="noload",
        overlaps="manager_profile",
    )
    column_obj: Mapped[PortalSpecialistColumn | None] = relationship(
        "PortalSpecialistColumn",
        primaryjoin="PortalManagerSpecialist.column_key == foreign(PortalSpecialistColumn.key)",
        viewonly=True,
        lazy="noload",
    )

    def __str__(self) -> str:
        mgr = self.__dict__.get("manager_profile")
        spec = self.__dict__.get("specialist_profile")
        mgr_name = (mgr.full_name or mgr.email) if mgr else self.manager_sub[:12] + "…"
        spec_name = (spec.full_name or spec.email) if spec else self.specialist_sub[:12] + "…"
        return f"{mgr_name} → {spec_name} [{self.column_key}]"
