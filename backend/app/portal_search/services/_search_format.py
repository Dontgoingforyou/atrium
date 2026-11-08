"""Форматирование поисковых результатов: выписки из текста и сборка DTO.

Выделено из роутера `portal_search/routes/search.py`:
бизнес-логика, преобразование данных и запросы к БД — в сервисном слое.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import TaskPriority
from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.constants import VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG, VIRTUAL_DOCS_ROOT_SLUG
from app.portal_documents.schemas.document import PortalDocumentListItem
from app.portal_documents.services.portal_document_queries import developer_docs_readable_ids
from app.portal_search.schemas.search import (
    PortalSearchCalendarEventItem,
    PortalSearchChatBrief,
    PortalSearchChatMessageItem,
    PortalSearchHitCalendarEvent,
    PortalSearchHitChatMessage,
    PortalSearchHitDocument,
    PortalSearchHitSpecialist,
    PortalSearchHitTask,
    PortalSearchSpecialistItem,
    PortalSearchTaskItem,
)


def excerpt(text: str | None, max_len: int = 240) -> str:
    """Обрезать текст до max_len символов с многоточием."""
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


async def nav_slug_map_for_documents(
    session: AsyncSession,
    document_ids: set[uuid.UUID],
) -> dict[uuid.UUID, str]:
    """Вернуть соответствие id документа → виртуальный slug раздела сайдбара для ссылок в поиске."""
    if not document_ids:
        return {}
    dev_ids = set(await developer_docs_readable_ids(session))
    return {
        doc_id: VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG if doc_id in dev_ids else VIRTUAL_DOCS_ROOT_SLUG
        for doc_id in document_ids
    }


def document_search_hit(
    d: PortalDocument,
    slug_map: dict[uuid.UUID, str],
) -> PortalSearchHitDocument:
    """Собрать DTO PortalSearchHitDocument из ORM-объекта и карты виртуальных slug-ов разделов."""
    slug = slug_map.get(d.id)
    item = PortalDocumentListItem.model_validate(d).model_copy(update={"nav_node_slug": slug})
    return PortalSearchHitDocument(entity_type="document", document=item)


def chat_message_search_hit(message: Any, chat: Any) -> PortalSearchHitChatMessage:
    return PortalSearchHitChatMessage(
        entity_type="chat_message",
        chat=PortalSearchChatBrief(id=chat.id, title=chat.title),
        message=PortalSearchChatMessageItem(
            id=message.id,
            chat_id=message.chat_id,
            author_sub=message.author_sub,
            body_excerpt=excerpt(message.body),
            created_at=message.created_at,
        ),
    )


def task_search_hit(task: Any) -> PortalSearchHitTask:
    return PortalSearchHitTask(
        entity_type="task",
        task=PortalSearchTaskItem(
            id=task.id,
            title=task.title,
            description_excerpt=excerpt(task.description) if task.description else None,
            status=task.status,
            priority=TaskPriority(task.priority),
            creator_sub=task.creator_sub,
            assignee_sub=task.assignee_sub,
            created_at=task.created_at,
        ),
    )


def specialist_search_hit(row: Any) -> PortalSearchHitSpecialist:
    return PortalSearchHitSpecialist(
        entity_type="specialist",
        specialist=PortalSearchSpecialistItem(sub=row.sub, full_name=row.full_name, email=row.email),
    )


def calendar_event_search_hit(hit: Any) -> PortalSearchHitCalendarEvent:
    return PortalSearchHitCalendarEvent(
        entity_type="calendar_event",
        calendar_event=PortalSearchCalendarEventItem(
            id=hit.id,
            calendar_id=hit.calendar_id,
            title=hit.title,
            starts_at=hit.starts_at,
            ends_at=hit.ends_at,
            calendar_title=hit.calendar_title,
            location=hit.location,
        ),
    )
