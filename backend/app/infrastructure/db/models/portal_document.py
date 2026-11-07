from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    column,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_document_comment import PortalDocumentComment
    from app.infrastructure.db.models.portal_task import PortalTask
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalTag(Base):
    """Тег для классификации документов портала."""

    __tablename__ = "portal_tag"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_portal_tag_slug"),
        # uniqueness: lower(trim(name)) — дублирует Alembic-миграцию для Base.metadata.create_all в тестах (SQLite)
        Index(
            "uq_portal_tag_name_lower",
            func.lower(func.trim(column("name"))),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(110), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, server_default="#3B82F6")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    documents: Mapped[list[PortalDocument]] = relationship(
        secondary="portal_document_tag",
        back_populates="tags",
    )
    tasks: Mapped[list[PortalTask]] = relationship(
        secondary="portal_task_tag",
        back_populates="tags",
    )

    def __str__(self) -> str:
        return self.name


class PortalDocument(Base):
    """Документ портала — базовый объект унифицированной модели контента."""

    __tablename__ = "portal_document"
    __table_args__ = (
        Index("ix_portal_document_deleted_at", "deleted_at"),
        Index("ix_portal_document_parent_sort", "parent_document_id", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    icon_emoji: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parent_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    author_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    author_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_sub: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_tour_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deleted_by_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deleted_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tags: Mapped[list[PortalTag]] = relationship(
        secondary="portal_document_tag",
        back_populates="documents",
        lazy="selectin",
    )
    history: Mapped[list[PortalDocumentHistory]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="PortalDocumentHistory.changed_at",
    )
    parent: Mapped[PortalDocument | None] = relationship(
        "PortalDocument",
        remote_side="PortalDocument.id",
        foreign_keys=[parent_document_id],
        back_populates="children",
    )
    children: Mapped[list[PortalDocument]] = relationship(
        "PortalDocument",
        back_populates="parent",
    )
    document_comments: Mapped[list[PortalDocumentComment]] = relationship(
        "PortalDocumentComment",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    files: Mapped[list[PortalDocumentFile]] = relationship(
        "PortalDocumentFile",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="select",
    )
    author_user: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="foreign(PortalDocument.author_sub) == PortalUserProfile.sub",
        lazy="noload",
    )
    owner_user: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="foreign(PortalDocument.owner_sub) == PortalUserProfile.sub",
        lazy="noload",
    )

    def __str__(self) -> str:
        return self.title


class PortalDocumentTag(Base):
    """Связь многие-ко-многим документ ↔ тег."""

    __tablename__ = "portal_document_tag"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_tag.id", ondelete="CASCADE"),
        primary_key=True,
    )

    document: Mapped[PortalDocument] = relationship(foreign_keys=[document_id], overlaps="documents,tags")
    tag: Mapped[PortalTag] = relationship(foreign_keys=[tag_id], overlaps="documents,tags")


class PortalDocumentHistory(Base):
    """Запись истории изменений документа (кто, когда, что поменял)."""

    __tablename__ = "portal_document_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_by_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_by_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    changed_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    diff: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    document: Mapped[PortalDocument] = relationship(back_populates="history")
    changed_by_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalDocumentHistory.changed_by_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )

    def __str__(self) -> str:
        return str(self.changed_at)


class PortalDocumentShortcut(Base):
    """Ярлык: документ, на который есть documentLink в body исходного документа.

    Не меняет parent_document_id; используется только для левого дерева навигации.
    """

    __tablename__ = "portal_document_shortcut"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id",
            "target_document_id",
            name="uq_portal_document_shortcut_source_target",
        ),
        Index("ix_portal_document_shortcut_source", "source_document_id"),
        Index("ix_portal_document_shortcut_target", "target_document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PortalDocumentFile(Base):
    """Файл-вложение документа (PDF/office/текст; хранится в MinIO)."""

    __tablename__ = "portal_document_file"
    __table_args__ = (
        Index("ix_portal_document_file_document_id", "document_id"),
        UniqueConstraint("storage_key", name="uq_portal_document_file_storage_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped[PortalDocument] = relationship(back_populates="files", lazy="select")

    def __str__(self) -> str:
        return self.original_filename
