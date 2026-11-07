"""Одноразовые WebSocket-тикеты (30 с): issue + consume для каждого топика."""

from __future__ import annotations

import json
import logging
import uuid

from app.infrastructure.cache.token_cache import get_redis_client
from app.infrastructure.ws._ticket_base import (  # noqa: F401 — re-export для тестов
    TICKET_TTL_SEC,
    _mem_lock,
    _mem_store,
    _retrieve_ticket,
    _store_ticket,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

TICKET_KEY_PREFIX = "portal:chat-ws-ticket:"
INBOX_TICKET_KEY_PREFIX = "portal:inbox-ws-ticket:"
TASK_COMMENTS_TICKET_KEY_PREFIX = "portal:task-comments-ws-ticket:"
DOCUMENT_COMMENTS_TICKET_KEY_PREFIX = "portal:document-comments-ws-ticket:"
DOCUMENT_PAGE_TICKET_KEY_PREFIX = "portal:document-page-ws-ticket:"
DOCUMENT_COLLAB_TICKET_KEY_PREFIX = "portal:document-collab-ws-ticket:"
TASK_PAGE_TICKET_KEY_PREFIX = "portal:task-page-ws-ticket:"
NAV_TREE_TICKET_KEY_PREFIX = "portal:nav-tree-ws-ticket:"
TASK_BOARD_TICKET_KEY_PREFIX = "portal:task-board-ws-ticket:"
SPECIALIST_BOARD_TICKET_KEY_PREFIX = "portal:specialist-board-ws-ticket:"
CALENDAR_TICKET_KEY_PREFIX = "portal:calendar-ws-ticket:"


async def _issue_user_ticket(prefix: str, user: UserPublic) -> str:
    """Общая логика ``issue_*_ws_ticket`` для тикетов без доп. параметров (только пользователь)."""
    return await _store_ticket(get_redis_client(), prefix, {"user": user.model_dump()})


async def _consume_user_ticket(prefix: str, ticket_id: str, *, label: str) -> UserPublic | None:
    """Общая логика ``consume_*_ws_ticket`` для тикетов без доп. параметров (только пользователь)."""
    raw = await _retrieve_ticket(get_redis_client(), f"{prefix}{ticket_id}")
    if not raw:
        return None
    try:
        return UserPublic.model_validate(json.loads(raw)["user"])
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("%s WS ticket parse error: %s", label, e)
        return None


async def _issue_entity_ticket(prefix: str, entity_field: str, entity_id: uuid.UUID, user: UserPublic) -> str:
    """Общая логика ``issue_*_ws_ticket`` для тикетов «идентификатор сущности + пользователь»."""
    return await _store_ticket(get_redis_client(), prefix, {entity_field: str(entity_id), "user": user.model_dump()})


async def _consume_entity_ticket(
    prefix: str,
    entity_field: str,
    ticket_id: str,
    *,
    label: str,
) -> tuple[uuid.UUID, UserPublic] | None:
    """Общая логика ``consume_*_ws_ticket`` для тикетов «идентификатор сущности + пользователь»."""
    raw = await _retrieve_ticket(get_redis_client(), f"{prefix}{ticket_id}")
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return uuid.UUID(data[entity_field]), UserPublic.model_validate(data["user"])
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("%s WS ticket parse error: %s", label, e)
        return None


async def issue_chat_ws_ticket(chat_id: uuid.UUID, user: UserPublic) -> str:
    """Создать одноразовый тикет (30 с) для WebSocket чата."""
    return await _issue_entity_ticket(TICKET_KEY_PREFIX, "chat_id", chat_id, user)


async def consume_chat_ws_ticket(ticket_id: str) -> tuple[uuid.UUID, UserPublic] | None:
    """ATOMIC-просмотр и снятие тикета чата. None — нет/просрочен/невалиден."""
    return await _consume_entity_ticket(TICKET_KEY_PREFIX, "chat_id", ticket_id, label="Chat")


async def issue_inbox_ws_ticket(user: UserPublic) -> str:
    """Одноразовый тикет (30 с) для WebSocket инбокса пользователя."""
    return await _issue_user_ticket(INBOX_TICKET_KEY_PREFIX, user)


async def consume_inbox_ws_ticket(ticket_id: str) -> UserPublic | None:
    """ATOMIC-просмотр и снятие тикета инбокса."""
    return await _consume_user_ticket(INBOX_TICKET_KEY_PREFIX, ticket_id, label="Inbox")


async def issue_task_comments_ws_ticket(task_id: uuid.UUID, user: UserPublic) -> str:
    """Одноразовый тикет для WebSocket треда комментариев к задаче (30 с)."""
    return await _issue_entity_ticket(TASK_COMMENTS_TICKET_KEY_PREFIX, "task_id", task_id, user)


async def consume_task_comments_ws_ticket(ticket_id: str) -> tuple[uuid.UUID, UserPublic] | None:
    return await _consume_entity_ticket(TASK_COMMENTS_TICKET_KEY_PREFIX, "task_id", ticket_id, label="Task comments")


async def issue_document_comments_ws_ticket(document_id: uuid.UUID, user: UserPublic) -> str:
    """Одноразовый тикет WebSocket треда комментариев к документу (30 с)."""
    return await _issue_entity_ticket(DOCUMENT_COMMENTS_TICKET_KEY_PREFIX, "document_id", document_id, user)


async def consume_document_comments_ws_ticket(
    ticket_id: str,
) -> tuple[uuid.UUID, UserPublic] | None:
    return await _consume_entity_ticket(
        DOCUMENT_COMMENTS_TICKET_KEY_PREFIX,
        "document_id",
        ticket_id,
        label="Document comments",
    )


async def issue_document_page_ws_ticket(document_id: uuid.UUID, user: UserPublic) -> str:
    return await _issue_entity_ticket(DOCUMENT_PAGE_TICKET_KEY_PREFIX, "document_id", document_id, user)


async def consume_document_page_ws_ticket(ticket_id: str) -> tuple[uuid.UUID, UserPublic] | None:
    return await _consume_entity_ticket(
        DOCUMENT_PAGE_TICKET_KEY_PREFIX,
        "document_id",
        ticket_id,
        label="Document page",
    )


async def issue_document_collab_ws_ticket(document_id: uuid.UUID, user: UserPublic) -> str:
    """Одноразовый тикет (30 с) для Hocuspocus collab-комнаты body документа."""
    return await _issue_entity_ticket(DOCUMENT_COLLAB_TICKET_KEY_PREFIX, "document_id", document_id, user)


async def consume_document_collab_ws_ticket(ticket_id: str) -> tuple[uuid.UUID, UserPublic] | None:
    return await _consume_entity_ticket(
        DOCUMENT_COLLAB_TICKET_KEY_PREFIX,
        "document_id",
        ticket_id,
        label="Document collab",
    )


async def issue_task_page_ws_ticket(task_id: uuid.UUID, user: UserPublic) -> str:
    return await _issue_entity_ticket(TASK_PAGE_TICKET_KEY_PREFIX, "task_id", task_id, user)


async def consume_task_page_ws_ticket(ticket_id: str) -> tuple[uuid.UUID, UserPublic] | None:
    return await _consume_entity_ticket(
        TASK_PAGE_TICKET_KEY_PREFIX,
        "task_id",
        ticket_id,
        label="Task page",
    )


async def issue_nav_tree_ws_ticket(user: UserPublic) -> str:
    """Одноразовый тикет для глобального WS дерева навигации (30 с)."""
    return await _issue_user_ticket(NAV_TREE_TICKET_KEY_PREFIX, user)


async def consume_nav_tree_ws_ticket(ticket_id: str) -> UserPublic | None:
    """ATOMIC-просмотр и снятие тикета nav-tree. None — нет/просрочен/невалиден."""
    return await _consume_user_ticket(NAV_TREE_TICKET_KEY_PREFIX, ticket_id, label="Nav tree")


async def issue_task_board_ws_ticket(user: UserPublic) -> str:
    """Одноразовый тикет для WS доски задач (30 с). Доска — единая глобальная комната."""
    return await _issue_user_ticket(TASK_BOARD_TICKET_KEY_PREFIX, user)


async def consume_task_board_ws_ticket(ticket_id: str) -> UserPublic | None:
    """ATOMIC-просмотр и снятие тикета доски задач. None — нет/просрочен/невалиден."""
    return await _consume_user_ticket(TASK_BOARD_TICKET_KEY_PREFIX, ticket_id, label="Task board")


async def issue_specialist_board_ws_ticket(user: UserPublic) -> str:
    """Одноразовый тикет для WS доски специалистов (30 с)."""
    return await _issue_user_ticket(SPECIALIST_BOARD_TICKET_KEY_PREFIX, user)


async def consume_specialist_board_ws_ticket(ticket_id: str) -> UserPublic | None:
    """ATOMIC-просмотр и снятие тикета доски специалистов."""
    return await _consume_user_ticket(SPECIALIST_BOARD_TICKET_KEY_PREFIX, ticket_id, label="Specialist board")


async def issue_calendar_ws_ticket(user: UserPublic) -> str:
    """Одноразовый тикет для WS календаря портала (30 с)."""
    return await _issue_user_ticket(CALENDAR_TICKET_KEY_PREFIX, user)


async def consume_calendar_ws_ticket(ticket_id: str) -> UserPublic | None:
    """ATOMIC-просмотр и снятие тикета календаря."""
    return await _consume_user_ticket(CALENDAR_TICKET_KEY_PREFIX, ticket_id, label="Calendar")
