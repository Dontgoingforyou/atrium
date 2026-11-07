from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_calendar import PortalCalendar, PortalCalendarEvent
    from app.infrastructure.db.models.portal_document import PortalDocument
    from app.infrastructure.db.models.portal_document_comment import PortalDocumentComment
    from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskComment
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile

_NOTIFICATION_TYPE_MENTION = "task_mention"


class PortalNotification(Base):
    """Уведомления: задачи, документы, календарь."""

    __tablename__ = "portal_notification"
    __table_args__ = (
        CheckConstraint(
            "(type IN ('task_mention', 'task_assigned', 'task_comment', 'task_due_soon', 'task_overdue') AND "
            "task_id IS NOT NULL AND document_id IS NULL AND "
            "document_comment_id IS NULL AND calendar_event_id IS NULL AND calendar_id IS NULL AND "
            "(type != 'task_mention' OR comment_id IS NOT NULL) AND "
            "(type != 'task_comment' OR comment_id IS NOT NULL) AND "
            "(type NOT IN ('task_assigned', 'task_due_soon', 'task_overdue') OR comment_id IS NULL)) OR "
            "(type = 'document_mention' AND task_id IS NULL AND comment_id IS NULL AND "
            "document_id IS NOT NULL AND document_comment_id IS NOT NULL AND "
            "calendar_event_id IS NULL AND calendar_id IS NULL) OR "
            "(type = 'document_trashed' AND task_id IS NULL AND comment_id IS NULL AND "
            "document_id IS NOT NULL AND document_comment_id IS NULL AND "
            "calendar_event_id IS NULL AND calendar_id IS NULL) OR "
            "(type IN ('calendar_invite', 'calendar_reminder', 'calendar_event_updated') AND "
            "calendar_event_id IS NOT NULL AND calendar_id IS NULL AND task_id IS NULL AND comment_id IS NULL AND "
            "document_id IS NULL AND document_comment_id IS NULL) OR "
            "(type = 'calendar_event_cancelled' AND calendar_id IS NULL AND task_id IS NULL AND comment_id IS NULL AND "
            "document_id IS NULL AND document_comment_id IS NULL) OR "
            "(type IN ('calendar_share', 'calendar_share_revoked') AND calendar_id IS NOT NULL AND "
            "calendar_event_id IS NULL AND task_id IS NULL AND comment_id IS NULL AND "
            "document_id IS NULL AND document_comment_id IS NULL)",
            name="ck_portal_notification_context",
        ),
        Index(
            "uq_portal_notif_recipient_task_comment",
            "recipient_sub",
            "comment_id",
            unique=True,
            sqlite_where=text("comment_id IS NOT NULL"),
            postgresql_where=text("comment_id IS NOT NULL"),
        ),
        Index(
            "uq_portal_notif_recipient_document_comment",
            "recipient_sub",
            "document_comment_id",
            unique=True,
            sqlite_where=text("document_comment_id IS NOT NULL"),
            postgresql_where=text("document_comment_id IS NOT NULL"),
        ),
        Index("ix_portal_notification_recipient_read_at", "recipient_sub", "read_at"),
        Index("ix_portal_notification_recipient_sub_created_at", "recipient_sub", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, default=_NOTIFICATION_TYPE_MENTION)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    comment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task_comment.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    document_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document_comment.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    calendar_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    calendar_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    context_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calendar_occurrence_starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    author_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped[PortalTask | None] = relationship(foreign_keys=[task_id], lazy="select")
    comment: Mapped[PortalTaskComment | None] = relationship(foreign_keys=[comment_id], lazy="noload")
    document: Mapped[PortalDocument | None] = relationship(foreign_keys=[document_id], lazy="noload")
    document_comment: Mapped[PortalDocumentComment | None] = relationship(
        foreign_keys=[document_comment_id],
        lazy="noload",
    )
    calendar_event: Mapped[PortalCalendarEvent | None] = relationship(
        "PortalCalendarEvent",
        primaryjoin="PortalNotification.calendar_event_id == PortalCalendarEvent.id",
        foreign_keys=[calendar_event_id],
        lazy="select",
        viewonly=True,
    )
    calendar: Mapped[PortalCalendar | None] = relationship(
        "PortalCalendar",
        primaryjoin="PortalNotification.calendar_id == PortalCalendar.id",
        foreign_keys=[calendar_id],
        lazy="select",
        viewonly=True,
    )
    author_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalNotification.author_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )

    def __str__(self) -> str:
        if self.task_id:
            return f"Уведомление для {self.recipient_sub} о задаче {self.task_id}"
        if self.document_id:
            return f"Уведомление для {self.recipient_sub} о комментарии к документу {self.document_id}"
        if self.calendar_event_id:
            return f"Уведомление для {self.recipient_sub} о событии {self.calendar_event_id}"
        if self.calendar_id:
            return f"Уведомление для {self.recipient_sub} о календаре {self.calendar_id}"
        return f"Уведомление {self.id}"
