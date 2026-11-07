from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_task import PortalTask
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalTaskReminderSent(Base):
    """Идемпотентность уведомлений о сроке задачи (за 2 дня / просрочка)."""

    __tablename__ = "portal_task_reminder_sent"
    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "recipient_sub",
            "reminder_kind",
            "due_at_snapshot",
            name="uq_portal_task_reminder_sent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    reminder_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    due_at_snapshot: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[PortalTask] = relationship(foreign_keys=[task_id], lazy="select")
    recipient_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalTaskReminderSent.recipient_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="select",
    )

    def __str__(self) -> str:
        return f"{self.reminder_kind}:{self.task_id}:{self.recipient_sub}"
