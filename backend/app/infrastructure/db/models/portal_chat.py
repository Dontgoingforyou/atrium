from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalChat(Base):
    __tablename__ = "portal_chat"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    canonical_dm_key: Mapped[str | None] = mapped_column(String(511), nullable=True, unique=True)
    avatar_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    avatar_focal_x: Mapped[float | None] = mapped_column(Float(), nullable=True)
    avatar_focal_y: Mapped[float | None] = mapped_column(Float(), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    members: Mapped[list[PortalChatMember]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    messages: Mapped[list[PortalChatMessage]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="PortalChatMessage.created_at",
    )
    created_by_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalChat.created_by_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )

    def __str__(self) -> str:
        return self.title or str(self.id)


class PortalChatMember(Base):
    __tablename__ = "portal_chat_member"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_sub: Mapped[str] = mapped_column(String(255), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chat: Mapped[PortalChat] = relationship(back_populates="members", foreign_keys=[chat_id])
    user_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalChatMember.user_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )

    def __str__(self) -> str:
        return self.user_sub


class PortalChatMessage(Base):
    __tablename__ = "portal_chat_message"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_for_all_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    reply_to_message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat_message.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reply_quote_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    forwarded_from_message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat_message.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    forwarded_from_author_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # default=list — вызываемый объект SQLAlchemy; новый список на каждую вставку (см. portal_task.mentions).
    mentions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    # Индекс составной (chat_id, pinned_at) заведён в миграции 0078_chat_message_pin —
    # не дублируем index=True здесь, чтобы не создавать одноимённый одноколоночный индекс.
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pinned_by_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)

    chat: Mapped[PortalChat] = relationship(back_populates="messages", foreign_keys=[chat_id])
    reply_to: Mapped[PortalChatMessage | None] = relationship(
        "PortalChatMessage",
        remote_side="PortalChatMessage.id",
        foreign_keys=[reply_to_message_id],
        lazy="select",
    )
    author_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalChatMessage.author_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )

    attachments: Mapped[list[PortalChatAttachment]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="PortalChatAttachment.created_at",
    )
    reactions: Mapped[list[PortalChatMessageReaction]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __str__(self) -> str:
        body = self.body or ""
        return body[:60] + ("…" if len(body) > 60 else "")


class PortalChatMessageReaction(Base):
    """Реакция пользователя на сообщение (эмодзи как строка Unicode)."""

    __tablename__ = "portal_chat_message_reaction"

    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat_message.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_sub: Mapped[str] = mapped_column(String(255), primary_key=True)
    emoji: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    message: Mapped[PortalChatMessage] = relationship(
        back_populates="reactions",
        foreign_keys=[message_id],
    )

    def __str__(self) -> str:
        return f"{self.emoji}@{self.user_sub}"


class PortalChatMessageHidden(Base):
    """Сообщение, скрытое для пользователя («удалить только у меня»)."""

    __tablename__ = "portal_chat_message_hidden"

    user_sub: Mapped[str] = mapped_column(String(255), primary_key=True)
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat_message.id", ondelete="CASCADE"),
        primary_key=True,
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    message: Mapped[PortalChatMessage] = relationship(foreign_keys=[message_id], lazy="select")


class PortalChatAttachment(Base):
    """Файловое вложение к сообщению чата (хранится в MinIO/S3)."""

    __tablename__ = "portal_chat_attachment"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat_message.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploader_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    voice_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    voice_waveform: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    voice_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    message: Mapped[PortalChatMessage | None] = relationship(back_populates="attachments", foreign_keys=[message_id])

    def __str__(self) -> str:
        return self.original_filename
