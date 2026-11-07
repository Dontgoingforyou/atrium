from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    Uuid,
    cast,
    func,
    select,
)
from sqlalchemy import column as sa_col
from sqlalchemy import table as sa_table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMessage
    from app.infrastructure.db.models.portal_document import PortalDocument, PortalTag
    from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
    from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalTaskColumn(Base):
    """Кастомная колонка канбана: заголовок, цвет, статус-ключ, порядок."""

    __tablename__ = "portal_task_column"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    color: Mapped[str] = mapped_column(String(32), nullable=False, server_default="#6131cf")
    status_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    exclude_from_kpi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    jira_status_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    def __str__(self) -> str:
        return self.title


class PortalTaskComment(Base):
    """Комментарий к задаче портала."""

    __tablename__ = "portal_task_comment"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task_comment.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    author_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mentions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    jira_comment_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[PortalTask] = relationship(back_populates="comments", lazy="select")
    replies: Mapped[list[PortalTaskComment]] = relationship(
        "PortalTaskComment",
        primaryjoin="PortalTaskComment.id == foreign(PortalTaskComment.parent_id)",
        lazy="noload",
        order_by="PortalTaskComment.created_at",
    )
    parent: Mapped[PortalTaskComment | None] = relationship(
        "PortalTaskComment",
        primaryjoin="foreign(PortalTaskComment.parent_id) == PortalTaskComment.id",
        viewonly=True,
        lazy="noload",
        overlaps="replies",
    )
    author_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalTaskComment.author_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
        overlaps="author_user",
    )
    author_user: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="foreign(PortalTaskComment.author_sub) == PortalUserProfile.sub",
        lazy="noload",
        overlaps="author_profile",
    )

    comment_media: Mapped[list[PortalTaskCommentMedia]] = relationship(
        "PortalTaskCommentMedia",
        back_populates="comment",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="PortalTaskCommentMedia.created_at",
    )

    @property
    def media(self) -> list[PortalRichMedia]:
        """Список PortalRichMedia, привязанных к этому комментарию через comment_media."""
        return [cm.rich_media for cm in (self.comment_media or []) if cm.rich_media is not None]

    def __str__(self) -> str:
        profile = self.__dict__.get("author_profile")
        name = (profile.full_name or profile.email or profile.username) if profile else None
        return f"Комментарий от {name or self.author_sub[:8]}"


class PortalTaskCommentMedia(Base):
    """Связь комментария задачи с вложением rich-media (изображением)."""

    __tablename__ = "portal_task_comment_media"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task_comment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_rich_media.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    comment: Mapped[PortalTaskComment] = relationship(
        "PortalTaskComment",
        back_populates="comment_media",
    )
    rich_media: Mapped[PortalRichMedia | None] = relationship(
        "PortalRichMedia",
        primaryjoin="PortalTaskCommentMedia.media_id == foreign(PortalRichMedia.id)",
        lazy="selectin",
        viewonly=True,
    )


# Lightweight table clause для portal_user_profile (без ORM-импорта, только для column_property)
_pup_clause = sa_table(
    "portal_user_profile",
    sa_col("sub"),
    sa_col("full_name"),
    sa_col("email"),
    sa_col("username"),
)

# Deferred computed column: резолвит author_sub упомянутых пользователей в читаемые имена.
# Выполняется как кореллированный подзапрос только при явном запросе (details view).
PortalTaskComment.mentioned_names = column_property(
    select(
        func.string_agg(
            func.coalesce(
                _pup_clause.c.full_name,
                _pup_clause.c.email,
                _pup_clause.c.username,
                _pup_clause.c.sub,
            ),
            ", ",
        )
    )
    .select_from(_pup_clause)
    .where(
        _pup_clause.c.sub.in_(
            select(func.jsonb_array_elements_text(cast(PortalTaskComment.mentions, JSONB))).correlate(PortalTaskComment)
        )
    )
    .correlate(PortalTaskComment)
    .scalar_subquery(),
    deferred=True,
)


class PortalTaskTag(Base):
    """Связь многие-ко-многим задача ↔ тег."""

    __tablename__ = "portal_task_tag"

    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_tag.id", ondelete="CASCADE"),
        primary_key=True,
    )


class PortalTask(Base):
    __tablename__ = "portal_task"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number: Mapped[int | None] = mapped_column(Integer, Identity(always=True), nullable=True, index=True, unique=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    creator_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    assignee_sub: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=TaskStatus.TODO,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        Enum(TaskPriority, native_enum=False, length=16),
        nullable=False,
        server_default=TaskPriority.MEDIUM,
        index=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat_message.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chat_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0", index=True)
    jira_issue_key: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True, index=True)
    jira_issue_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    jira_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    jira_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_tour_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tags: Mapped[list[PortalTag]] = relationship(
        secondary="portal_task_tag",
        back_populates="tasks",
        lazy="selectin",
        viewonly=False,
    )
    history: Mapped[list[PortalTaskHistory]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="PortalTaskHistory.changed_at",
    )
    comments: Mapped[list[PortalTaskComment]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="noload",
        order_by="PortalTaskComment.created_at",
    )
    document: Mapped[PortalDocument | None] = relationship(foreign_keys=[document_id], lazy="select")
    source_message: Mapped[PortalChatMessage | None] = relationship(foreign_keys=[source_message_id], lazy="select")
    chat: Mapped[PortalChat | None] = relationship(foreign_keys=[chat_id], lazy="select")
    creator_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalTask.creator_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
        overlaps="creator_user",
    )
    creator_user: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="foreign(PortalTask.creator_sub) == PortalUserProfile.sub",
        lazy="noload",
        overlaps="creator_profile",
    )
    assignee_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalTask.assignee_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
        overlaps="assignee_user",
    )
    assignee_user: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="foreign(PortalTask.assignee_sub) == PortalUserProfile.sub",
        lazy="noload",
        overlaps="assignee_profile",
    )
    subtasks: Mapped[list[PortalTask]] = relationship(
        "PortalTask",
        primaryjoin="PortalTask.id == foreign(PortalTask.parent_task_id)",
        lazy="noload",
        order_by="PortalTask.created_at",
    )
    parent_task: Mapped[PortalTask | None] = relationship(
        "PortalTask",
        primaryjoin="foreign(PortalTask.parent_task_id) == PortalTask.id",
        viewonly=True,
        lazy="noload",
        overlaps="subtasks",
    )
    task_assignees: Mapped[list[PortalTaskAssignee]] = relationship(
        "PortalTaskAssignee",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    links: Mapped[list[PortalTaskLink]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="noload",
        order_by="PortalTaskLink.created_at",
    )
    files: Mapped[list[PortalTaskFile]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="noload",
        order_by="PortalTaskFile.created_at",
    )

    def __str__(self) -> str:
        return self.title or str(self.id)


class PortalTaskLink(Base):
    """Ссылка, прикреплённая к задаче."""

    __tablename__ = "portal_task_link"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_by_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[PortalTask] = relationship(back_populates="links", lazy="select")

    def __str__(self) -> str:
        return self.title or self.url


class PortalTaskFile(Base):
    """Файл, прикреплённый к задаче (хранится в MinIO)."""

    __tablename__ = "portal_task_file"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    jira_attachment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[PortalTask] = relationship(back_populates="files", lazy="select")

    def __str__(self) -> str:
        return self.original_filename


class PortalTaskHistory(Base):
    __tablename__ = "portal_task_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_by_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    diff: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    task: Mapped[PortalTask] = relationship(back_populates="history")
    changed_by_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalTaskHistory.changed_by_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )

    def __str__(self) -> str:
        return f"Изменение задачи от {str(self.changed_at)[:16]}"
