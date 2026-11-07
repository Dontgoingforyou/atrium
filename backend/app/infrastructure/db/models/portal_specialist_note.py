from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalSpecialistNote(Base):
    """Комментарий о специалисте."""

    __tablename__ = "portal_specialist_note"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_sub: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("portal_user_profile.sub", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_sub: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("portal_user_profile.sub", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_specialist_note.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mentions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    author_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalSpecialistNote.author_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )
    replies: Mapped[list[PortalSpecialistNote]] = relationship(
        "PortalSpecialistNote",
        primaryjoin="PortalSpecialistNote.id == foreign(PortalSpecialistNote.parent_id)",
        lazy="noload",
        order_by="PortalSpecialistNote.created_at",
    )
    comment_media: Mapped[list[PortalSpecialistNoteMedia]] = relationship(
        "PortalSpecialistNoteMedia",
        back_populates="comment",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="PortalSpecialistNoteMedia.created_at",
    )

    @property
    def media(self) -> list[PortalRichMedia]:
        return [item.rich_media for item in (self.comment_media or []) if item.rich_media is not None]


class PortalSpecialistNoteMedia(Base):
    """Связь комментария специалиста с вложением rich-media."""

    __tablename__ = "portal_specialist_note_media"
    __table_args__ = (UniqueConstraint("comment_id", "media_id", name="uq_portal_specialist_note_media_comment_media"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_specialist_note.id", ondelete="CASCADE"),
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

    comment: Mapped[PortalSpecialistNote] = relationship(
        "PortalSpecialistNote",
        back_populates="comment_media",
    )
    rich_media: Mapped[PortalRichMedia | None] = relationship(
        "PortalRichMedia",
        primaryjoin="PortalSpecialistNoteMedia.media_id == foreign(PortalRichMedia.id)",
        lazy="selectin",
        viewonly=True,
    )
