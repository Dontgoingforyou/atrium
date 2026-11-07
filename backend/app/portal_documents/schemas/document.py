from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.portal_chat.schemas.chat import PortalChatRead
from app.portal_collab.schemas.task import PortalTaskRead
from app.schemas.tags import PortalTagRead

# ---------------------------------------------------------------------------
# Документы
# ---------------------------------------------------------------------------


def _normalize_icon_emoji(v: str | None) -> str | None:
    if v is None:
        return None
    s = v.strip()
    return s if s else None


class PortalDocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    icon_emoji: str | None = Field(default=None, max_length=32)
    parent_document_id: UUID | None = None
    body: str | None = None
    owner_sub: str | None = Field(default=None, max_length=255)
    tag_ids: list[UUID] = Field(default_factory=list)

    @field_validator("icon_emoji", mode="before")
    @classmethod
    def _icon_emoji_create(cls, v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            return _normalize_icon_emoji(v)
        raise TypeError("icon_emoji должен быть строкой или null")


class PortalDocumentQuickCreate(BaseModel):
    """Мгновенное создание документа без заголовка (Notion-паттерн).

    Создаёт документ с заголовком «Без названия».
    Может быть привязан к родительскому документу (`parent_document_id`) или быть корневым.
    """

    parent_document_id: UUID | None = None


class PortalDocumentIdResponse(BaseModel):
    """Ответ quick-create: только id нового документа для немедленного redirect."""

    id: UUID


class TourDemoDocumentEnsureRead(BaseModel):
    """Учебный документ guided tour: id и признак создания в этом вызове."""

    id: UUID
    created: bool = Field(description="True, если документ создан сейчас (не был найден ранее)")


class PortalDocumentUpdate(BaseModel):
    expected_version: int = Field(..., ge=1, description="Версия документа, прочитанная клиентом (CAS)")
    title: str | None = Field(default=None, min_length=1, max_length=512)
    icon_emoji: str | None = Field(default=None, max_length=32)
    parent_document_id: UUID | None = None
    body: str | None = None
    owner_sub: str | None = Field(default=None, max_length=255)
    tag_ids: list[UUID] | None = None

    @field_validator("icon_emoji", mode="before")
    @classmethod
    def _icon_emoji_update(cls, v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            return _normalize_icon_emoji(v)
        raise TypeError("icon_emoji должен быть строкой или null")


class DocumentBreadcrumbItem(BaseModel):
    id: UUID
    title: str


class PortalDocumentListItem(BaseModel):
    """Краткая карточка документа для списков (без body)."""

    id: UUID
    title: str
    icon_emoji: str | None = None
    parent_document_id: UUID | None
    author_sub: str
    author_email: str | None = None
    owner_sub: str | None
    owner_email: str | None = None
    version: int = Field(description="Версия для optimistic locking (CAS)")
    created_at: datetime
    updated_at: datetime
    tags: list[PortalTagRead] = []
    nav_node_slug: str | None = Field(
        default=None,
        description="Slug раздела навигации; заполняется в выдаче глобального поиска.",
    )

    model_config = {"from_attributes": True}


class PortalDocumentRead(PortalDocumentListItem):
    """Полная карточка документа с телом."""

    body: str | None
    # Цепочка от корневой страницы к прямому родителю (для крошек)
    breadcrumb: list[DocumentBreadcrumbItem] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# История изменений
# ---------------------------------------------------------------------------


class PortalDocumentReorderRequest(BaseModel):
    """Позиция между соседями: сразу перед ``before_id`` или сразу после ``after_id``."""

    before_id: UUID | None = None
    after_id: UUID | None = None

    @model_validator(mode="after")
    def _xor_neighbors(self) -> PortalDocumentReorderRequest:
        if (self.before_id is None) == (self.after_id is None):
            raise ValueError("Укажите ровно одно из полей: before_id или after_id")
        return self


class PortalDocumentTrashItem(BaseModel):
    """Элемент списка корзины (верхушка удалённого дерева)."""

    id: UUID
    title: str
    deleted_at: datetime
    deleted_by_sub: str | None = None
    deleted_by_display_name: str | None = None
    deleted_by_email: str | None = None
    auto_purge_at: datetime

    @classmethod
    def from_portal_row(cls, row: Any, *, ttl_days: int) -> PortalDocumentTrashItem:
        if row.deleted_at is None:
            raise ValueError("ожидается deleted_at")
        return cls(
            id=row.id,
            title=row.title,
            deleted_at=row.deleted_at,
            deleted_by_sub=row.deleted_by_sub,
            deleted_by_display_name=row.deleted_by_display_name,
            deleted_by_email=row.deleted_by_email,
            auto_purge_at=row.deleted_at + timedelta(days=ttl_days),
        )


class PortalDocumentHistoryRead(BaseModel):
    id: UUID
    document_id: UUID
    changed_by_sub: str
    changed_by_display_name: str | None = None
    changed_by_email: str | None = None
    changed_at: datetime
    diff: dict[str, Any]

    model_config = {"from_attributes": True}


class DocumentFileRead(BaseModel):
    """Файл-вложение документа; URL собираются в роутере."""

    id: UUID
    document_id: UUID
    original_filename: str
    content_type: str
    file_size: int
    download_url: str
    view_url: str
    uploaded_by_sub: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Связи с коллаборацией (чаты, задачи)
# ---------------------------------------------------------------------------


class PortalDocumentRelatedRead(BaseModel):
    """Чаты и задачи, привязанные к документу; видимость как у списков /chats и /tasks."""

    chats: list[PortalChatRead]
    tasks: list[PortalTaskRead]
