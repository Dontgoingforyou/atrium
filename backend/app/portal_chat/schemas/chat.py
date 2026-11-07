from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.portal_chat.constants import CHAT_MESSAGE_BODY_MAX_LENGTH, CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    content_type: str
    file_size: int
    download_url: str
    created_at: datetime
    voice_duration_seconds: float | None = None
    voice_waveform: list[float] | None = None
    transcript: str | None = Field(default=None, description="Текст транскрибации голосового сообщения (Whisper)")
    message_id: uuid.UUID | None = Field(
        default=None,
        description="Сообщение, к которому привязано вложение (для перехода из галереи)",
    )


class PortalChatCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    member_subs: list[str] = Field(
        default_factory=list,
        description="Дополнительные участники (sub); создатель добавляется автоматически",
    )


class PortalChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    created_by_sub: str
    created_at: datetime
    updated_at: datetime
    is_direct: bool = Field(
        default=False,
        description="True — личный диалог (DM); иначе групповой чат",
    )

    member_subs: list[str] = Field(default_factory=list, description="Список sub участников чата")
    unread_count: int = Field(default=0, description="Непрочитанных сообщений от других участников")

    avatar_url: str | None = Field(
        default=None,
        description="Группа — presigned MinIO; DM — signed photo пира (EA proxy)",
    )
    avatar_focal_x: float | None = Field(default=None, description="Фокус кадра аватара 0–1")
    avatar_focal_y: float | None = Field(default=None, description="Фокус кадра аватара 0–1")
    version: int = Field(default=1, description="Версия для optimistic locking (CAS)")


class PortalChatPatch(BaseModel):
    """Смена названия группового чата (только создатель)."""

    expected_version: int = Field(..., ge=1, description="Версия чата, прочитанная клиентом (CAS)")
    title: str = Field(min_length=1, max_length=255)


class PortalChatMemberInvite(BaseModel):
    """Приглашение участника в групповой чат."""

    user_sub: str = Field(min_length=1, max_length=255)


class PortalDirectChatCreate(BaseModel):
    other_user_sub: str = Field(description="sub второго участника прямого чата")


class PortalChatWsTicketRead(BaseModel):
    """Одноразовый тикет для ``GET /chats/{id}/ws?ticket=...`` (30 с, вместо JWT в query)."""

    ticket: str


class PortalInboxWsTicketRead(BaseModel):
    """Одноразовый тикет для ``/portal/inbox/ws?ticket=...`` (30 с)."""

    ticket: str


class PortalChatMessageReplyPreview(BaseModel):
    """Краткое представление сообщения, на которое дан ответ."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_sub: str
    body: str = Field(description="Текст цитируемого сообщения или выделенный фрагмент (усечённый)")
    deleted_for_all_at: datetime | None = None
    quote_text: str | None = Field(
        default=None,
        description="Выделенный фрагмент при «ответить с цитатой»; None — цитата всего сообщения",
    )


class PortalChatMessageReactionAgg(BaseModel):
    """Сводка реакций по одному эмодзи."""

    emoji: str
    count: int
    reacted_by_me: bool = False


class PortalChatMessageReactionToggle(BaseModel):
    """Тело запроса: добавить или снять реакцию (toggle)."""

    emoji: str = Field(min_length=1, max_length=32)


class MessageReactorItem(BaseModel):
    """Участник, поставивший реакцию с данным эмодзи."""

    user_sub: str
    reacted_at: datetime = Field(description="Когда поставлена реакция (UTC)")


class MessageReactorsResponse(BaseModel):
    """Список пользователей, поставивших реакцию на сообщение.

    Набор ограничен участниками чата (реакции ставит только member) —
    без PagedResponse, как у readers.
    """

    message_id: uuid.UUID
    emoji: str
    reactors: list[MessageReactorItem]


class PortalChatMessageForward(BaseModel):
    """Переслать сообщение из другого чата в ``chat_id`` из пути (целевой чат)."""

    from_chat_id: uuid.UUID
    message_id: uuid.UUID


class PortalChatMessageForwardFrom(BaseModel):
    """Метаданные пересланного сообщения (автор исходного текста)."""

    author_sub: str
    source_message_id: uuid.UUID | None = Field(
        default=None,
        description="Исходное сообщение в БД; NULL если удалено (ON DELETE SET NULL)",
    )


class PortalChatMessageCreate(BaseModel):
    body: str = Field(default="", max_length=CHAT_MESSAGE_BODY_MAX_LENGTH)
    attachment_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    reply_to_message_id: uuid.UUID | None = None
    reply_quote_text: str | None = Field(
        default=None,
        max_length=CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH,
        description="Выделенный фрагмент целевого сообщения («ответить с цитатой»)",
    )
    mentions: list[str] = Field(
        default_factory=list,
        max_length=32,
        description="sub упомянутых участников чата (не включая автора)",
    )

    @model_validator(mode="after")
    def require_body_or_attachments(self) -> PortalChatMessageCreate:
        if not self.body.strip() and not self.attachment_ids:
            raise ValueError("Необходимо указать текст сообщения или хотя бы одно вложение")
        if self.reply_quote_text is not None and self.reply_to_message_id is None:
            raise ValueError("Цитата допустима только вместе с reply_to_message_id")
        return self


class PortalChatMessageUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=CHAT_MESSAGE_BODY_MAX_LENGTH)


class MessageReaderItem(BaseModel):
    """Участник чата, прочитавший сообщение."""

    user_sub: str
    read_at: datetime = Field(description="Время, когда участник последний раз читал чат (last_read_at)")


class MessageReadersResponse(BaseModel):
    """Список участников, прочитавших конкретное сообщение."""

    message_id: uuid.UUID
    readers: list[MessageReaderItem]


class PortalChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chat_id: uuid.UUID
    author_sub: str
    body: str
    created_at: datetime
    updated_at: datetime | None = None
    deleted_for_all_at: datetime | None = None
    receipt: Literal["sent", "read"] | None = Field(
        default=None,
        description="Статус доставки/прочтения (только для автора, по last_read_at остальных участников)",
    )
    attachments: list[AttachmentRead] = Field(default_factory=list)
    reply_to_message_id: uuid.UUID | None = None
    reply_quote_text: str | None = Field(
        default=None,
        description="Выделенный фрагмент при ответе с цитатой",
    )
    reply_to: PortalChatMessageReplyPreview | None = None
    reactions: list[PortalChatMessageReactionAgg] = Field(default_factory=list)
    forwarded_from: PortalChatMessageForwardFrom | None = None
    mentions: list[str] = Field(default_factory=list, description="Упомянутые участники (sub)")
    pinned_at: datetime | None = Field(default=None, description="Когда сообщение было закреплено (UTC)")
    pinned_by_sub: str | None = Field(default=None, description="Кто закрепил сообщение")
