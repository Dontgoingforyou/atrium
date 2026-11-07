from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from app.core.enums import TaskPriority
from app.portal_documents.schemas.document import PortalDocumentListItem


class PortalSearchChatBrief(BaseModel):
    id: uuid.UUID
    title: str | None


class PortalSearchChatMessageItem(BaseModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    author_sub: str
    body_excerpt: str
    created_at: datetime


class PortalSearchHitDocument(BaseModel):
    entity_type: Literal["document"] = "document"
    document: PortalDocumentListItem = Field(description="Краткая карточка документа")


class PortalSearchHitChatMessage(BaseModel):
    entity_type: Literal["chat_message"] = "chat_message"
    chat: PortalSearchChatBrief
    message: PortalSearchChatMessageItem


class PortalSearchTaskItem(BaseModel):
    id: uuid.UUID
    title: str
    description_excerpt: str | None
    status: str
    priority: TaskPriority
    creator_sub: str
    assignee_sub: str | None
    created_at: datetime


class PortalSearchHitTask(BaseModel):
    entity_type: Literal["task"] = "task"
    task: PortalSearchTaskItem


class PortalSearchSpecialistItem(BaseModel):
    sub: str
    full_name: str | None
    email: str | None


class PortalSearchHitSpecialist(BaseModel):
    entity_type: Literal["specialist"] = "specialist"
    specialist: PortalSearchSpecialistItem


class PortalSearchCalendarEventItem(BaseModel):
    id: uuid.UUID
    calendar_id: uuid.UUID
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    calendar_title: str
    location: str | None = None


class PortalSearchHitCalendarEvent(BaseModel):
    entity_type: Literal["calendar_event"] = "calendar_event"
    calendar_event: PortalSearchCalendarEventItem


PortalSearchHit = Annotated[
    PortalSearchHitDocument
    | PortalSearchHitChatMessage
    | PortalSearchHitTask
    | PortalSearchHitSpecialist
    | PortalSearchHitCalendarEvent,
    Field(discriminator="entity_type"),
]

PortalSearchHitResponseUnion = (
    PortalSearchHitDocument
    | PortalSearchHitChatMessage
    | PortalSearchHitTask
    | PortalSearchHitSpecialist
    | PortalSearchHitCalendarEvent
)


class PortalSemanticHit(BaseModel):
    """Результат семантического поиска — одна сущность с её релевантностью."""

    entity_type: str = Field(
        description=(
            "Тип сущности: document, task, chat_message, agreement, learning_material, "
            "specialist, specialist_note, calendar_event"
        )
    )
    entity_id: str = Field(description="Строковый UUID или ID сущности")
    text_excerpt: str = Field(description="Начало текста, по которому построен эмбеддинг (до 300 символов)")
    similarity_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Косинусная похожесть запроса и документа (0–1); пусто — хит только из полнотекста, без вектора в выборке"
        ),
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Метаданные сущности (author_sub и т.п.)",
    )


class PortalSemanticSearchResponse(BaseModel):
    query: str
    results: list[PortalSemanticHit]
    total_found: int = Field(
        description=("Число hits после RBAC/пост-фильтров в пределах выборки top_k, не полный count по индексу")
    )
