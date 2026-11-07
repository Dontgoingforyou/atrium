from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_document import PortalDocument
    from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalDocumentComment(Base):
    """Комментарий к документу портала (треды через parent_id)."""

    __tablename__ = "portal_document_comment"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document_comment.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    author_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mentions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped[PortalDocument] = relationship(
        foreign_keys=[document_id],
        lazy="select",
        back_populates="document_comments",
    )
    replies: Mapped[list[PortalDocumentComment]] = relationship(
        "PortalDocumentComment",
        primaryjoin="PortalDocumentComment.id == foreign(PortalDocumentComment.parent_id)",
        lazy="noload",
        order_by="PortalDocumentComment.created_at",
    )
    parent: Mapped[PortalDocumentComment | None] = relationship(
        "PortalDocumentComment",
        primaryjoin="foreign(PortalDocumentComment.parent_id) == PortalDocumentComment.id",
        viewonly=True,
        lazy="noload",
        overlaps="replies",
    )
    author_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalDocumentComment.author_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )
    comment_media: Mapped[list[PortalDocumentCommentMedia]] = relationship(
        "PortalDocumentCommentMedia",
        back_populates="comment",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="PortalDocumentCommentMedia.created_at",
    )

    @property
    def media(self) -> list[PortalRichMedia]:
        """Список PortalRichMedia, привязанных к комментарию через comment_media."""
        return [cm.rich_media for cm in (self.comment_media or []) if cm.rich_media is not None]

    def __str__(self) -> str:
        profile = self.__dict__.get("author_profile")
        name = (profile.full_name or profile.email or profile.username) if profile else None
        return f"Комментарий к документу от {name or self.author_sub[:8]}"


class PortalDocumentCommentMedia(Base):
    """Связь комментария документа с вложением rich-media (изображением)."""

    __tablename__ = "portal_document_comment_media"
    __table_args__ = (
        UniqueConstraint("comment_id", "media_id", name="uq_portal_document_comment_media_comment_media"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document_comment.id", ondelete="CASCADE"),
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

    comment: Mapped[PortalDocumentComment] = relationship(
        "PortalDocumentComment",
        back_populates="comment_media",
    )
    rich_media: Mapped[PortalRichMedia | None] = relationship(
        "PortalRichMedia",
        primaryjoin="PortalDocumentCommentMedia.media_id == foreign(PortalRichMedia.id)",
        lazy="selectin",
        viewonly=True,
    )
