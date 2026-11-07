"""Синглтоны room-менеджеров: чаты и треды комментариев (Redis pub/sub)."""

from __future__ import annotations

import logging

import redis.asyncio as aioredis

from app.infrastructure.ws.room_manager import (
    REDIS_CHANNEL_PREFIX_CALENDAR,
    REDIS_CHANNEL_PREFIX_CHAT,
    REDIS_CHANNEL_PREFIX_DOCUMENT_COMMENTS,
    REDIS_CHANNEL_PREFIX_DOCUMENT_PAGE,
    REDIS_CHANNEL_PREFIX_NAV_TREE,
    REDIS_CHANNEL_PREFIX_SPECIALIST_BOARD,
    REDIS_CHANNEL_PREFIX_TASK_BOARD,
    REDIS_CHANNEL_PREFIX_TASK_COMMENTS,
    REDIS_CHANNEL_PREFIX_TASK_PAGE,
    TopicRoomManager,
)

logger = logging.getLogger(__name__)

_chat_manager: TopicRoomManager | None = None
_task_comments_manager: TopicRoomManager | None = None
_document_comments_manager: TopicRoomManager | None = None
_document_page_manager: TopicRoomManager | None = None
_task_page_manager: TopicRoomManager | None = None
_nav_tree_manager: TopicRoomManager | None = None
_task_board_manager: TopicRoomManager | None = None
_specialist_board_manager: TopicRoomManager | None = None
_calendar_manager: TopicRoomManager | None = None


def init_ws_managers(redis: aioredis.Redis | None) -> None:
    """Инициализация всех WS-менеджеров комнат."""
    global _chat_manager, _task_comments_manager
    global _document_comments_manager, _document_page_manager, _task_page_manager
    global _nav_tree_manager, _task_board_manager, _specialist_board_manager
    global _calendar_manager
    _chat_manager = TopicRoomManager(redis, REDIS_CHANNEL_PREFIX_CHAT)
    _task_comments_manager = TopicRoomManager(redis, REDIS_CHANNEL_PREFIX_TASK_COMMENTS)
    _document_comments_manager = TopicRoomManager(redis, REDIS_CHANNEL_PREFIX_DOCUMENT_COMMENTS)
    _document_page_manager = TopicRoomManager(redis, REDIS_CHANNEL_PREFIX_DOCUMENT_PAGE)
    _task_page_manager = TopicRoomManager(redis, REDIS_CHANNEL_PREFIX_TASK_PAGE)
    _nav_tree_manager = TopicRoomManager(redis, REDIS_CHANNEL_PREFIX_NAV_TREE)
    _task_board_manager = TopicRoomManager(redis, REDIS_CHANNEL_PREFIX_TASK_BOARD)
    _specialist_board_manager = TopicRoomManager(redis, REDIS_CHANNEL_PREFIX_SPECIALIST_BOARD)
    _calendar_manager = TopicRoomManager(redis, REDIS_CHANNEL_PREFIX_CALENDAR)
    logger.info(
        "TopicRoomManager (chat, task_comments, task_page,"
        " document_*, nav_tree, task_board, specialist_board, calendar) инициализирован (Redis: %s)",
        "да" if redis else "нет — in-memory режим",
    )


def get_chat_manager() -> TopicRoomManager:
    global _chat_manager
    if _chat_manager is None:
        _chat_manager = TopicRoomManager(None, REDIS_CHANNEL_PREFIX_CHAT)
    return _chat_manager


def get_task_comments_manager() -> TopicRoomManager:
    global _task_comments_manager
    if _task_comments_manager is None:
        _task_comments_manager = TopicRoomManager(None, REDIS_CHANNEL_PREFIX_TASK_COMMENTS)
    return _task_comments_manager


def get_document_comments_manager() -> TopicRoomManager:
    global _document_comments_manager
    if _document_comments_manager is None:
        _document_comments_manager = TopicRoomManager(None, REDIS_CHANNEL_PREFIX_DOCUMENT_COMMENTS)
    return _document_comments_manager


def get_document_page_manager() -> TopicRoomManager:
    global _document_page_manager
    if _document_page_manager is None:
        _document_page_manager = TopicRoomManager(None, REDIS_CHANNEL_PREFIX_DOCUMENT_PAGE)
    return _document_page_manager


def get_task_page_manager() -> TopicRoomManager:
    global _task_page_manager
    if _task_page_manager is None:
        _task_page_manager = TopicRoomManager(None, REDIS_CHANNEL_PREFIX_TASK_PAGE)
    return _task_page_manager


def get_nav_tree_manager() -> TopicRoomManager:
    """Глобальный менеджер: все пользователи видят обновления дерева навигации в реальном времени."""
    global _nav_tree_manager
    if _nav_tree_manager is None:
        _nav_tree_manager = TopicRoomManager(None, REDIS_CHANNEL_PREFIX_NAV_TREE)
    return _nav_tree_manager


def get_task_board_manager() -> TopicRoomManager:
    """Глобальный менеджер: real-time события канбан-доски задач."""
    global _task_board_manager
    if _task_board_manager is None:
        _task_board_manager = TopicRoomManager(None, REDIS_CHANNEL_PREFIX_TASK_BOARD)
    return _task_board_manager


def get_specialist_board_manager() -> TopicRoomManager:
    """Глобальный менеджер: real-time события доски специалистов."""
    global _specialist_board_manager
    if _specialist_board_manager is None:
        _specialist_board_manager = TopicRoomManager(None, REDIS_CHANNEL_PREFIX_SPECIALIST_BOARD)
    return _specialist_board_manager


def get_calendar_manager() -> TopicRoomManager:
    """Глобальный менеджер: real-time события календаря портала."""
    global _calendar_manager
    if _calendar_manager is None:
        _calendar_manager = TopicRoomManager(None, REDIS_CHANNEL_PREFIX_CALENDAR)
    return _calendar_manager


class ConnectionManager(TopicRoomManager):
    """Совместимость с тестами: тот же API, что раньше — только ``chat:{id}``."""

    def __init__(self, redis: aioredis.Redis | None) -> None:
        super().__init__(redis, REDIS_CHANNEL_PREFIX_CHAT)
