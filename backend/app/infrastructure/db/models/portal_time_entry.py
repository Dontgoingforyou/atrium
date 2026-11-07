from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_task import PortalTask
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalTimeEntry(Base):
    """Учёт затраченного времени (таймшит): календарный день, длительность в минутах, опционально задача."""

    __tablename__ = "portal_time_entry"
    __table_args__ = (
        CheckConstraint("minutes > 0 AND minutes <= 1440", name="ck_portal_time_entry_minutes_range"),
        Index("ix_portal_time_entry_user_sub_worked_on", "user_sub", "worked_on"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    worked_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_tour_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[PortalTask | None] = relationship(foreign_keys=[task_id], lazy="select")
    user_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalTimeEntry.user_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
        overlaps="user_user",
    )
    user_user: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="foreign(PortalTimeEntry.user_sub) == PortalUserProfile.sub",
        lazy="noload",
        overlaps="user_profile",
    )

    def __str__(self) -> str:
        return f"{self.worked_on} {self.minutes}m ({self.user_sub})"
