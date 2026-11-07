from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_task import PortalTask


class PortalTaskAssignee(Base):
    __tablename__ = "portal_task_assignee"
    __table_args__ = (UniqueConstraint("task_id", "assignee_sub", name="uq_portal_task_assignee_pair"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignee_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    task: Mapped[PortalTask] = relationship(back_populates="task_assignees", lazy="select")
