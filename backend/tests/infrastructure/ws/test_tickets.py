"""Тесты одноразовых WS-тикетов (`app.infrastructure.ws.tickets`)."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import patch

import pytest
from app.infrastructure.ws.tickets import (
    CALENDAR_TICKET_KEY_PREFIX,
    DOCUMENT_COMMENTS_TICKET_KEY_PREFIX,
    DOCUMENT_PAGE_TICKET_KEY_PREFIX,
    INBOX_TICKET_KEY_PREFIX,
    NAV_TREE_TICKET_KEY_PREFIX,
    SPECIALIST_BOARD_TICKET_KEY_PREFIX,
    TASK_BOARD_TICKET_KEY_PREFIX,
    TASK_COMMENTS_TICKET_KEY_PREFIX,
    TICKET_KEY_PREFIX,
    TICKET_TTL_SEC,
    _mem_store,
    consume_calendar_ws_ticket,
    consume_chat_ws_ticket,
    consume_document_comments_ws_ticket,
    consume_document_page_ws_ticket,
    consume_inbox_ws_ticket,
    consume_nav_tree_ws_ticket,
    consume_specialist_board_ws_ticket,
    consume_task_board_ws_ticket,
    consume_task_comments_ws_ticket,
    issue_calendar_ws_ticket,
    issue_chat_ws_ticket,
    issue_document_comments_ws_ticket,
    issue_document_page_ws_ticket,
    issue_inbox_ws_ticket,
    issue_nav_tree_ws_ticket,
    issue_specialist_board_ws_ticket,
    issue_task_board_ws_ticket,
    issue_task_comments_ws_ticket,
)
from app.schemas.auth import UserPublic

type ConsumeFn = Callable[[str], Awaitable[Any]]
type IssueFn = Callable[..., Awaitable[str]]


def _user() -> UserPublic:
    return UserPublic(
        sub="user-sub",
        email="u@example.com",
        username="u",
        full_name="U",
        idp_groups=["g1"],
        is_portal_admin=False,
    )


class _FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self.last_ex: int | None = None

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._kv[key] = value
        self.last_ex = ex

    async def getdel(self, key: str) -> str | None:
        return self._kv.pop(key, None)


def _no_redis() -> object:
    return patch("app.infrastructure.ws.tickets.get_redis_client", return_value=None)


def _with_redis(client: _FakeRedis) -> object:
    return patch("app.infrastructure.ws.tickets.get_redis_client", return_value=client)


# (kind, prefix, issue, consume, has_entity)
_TICKET_KINDS: list[tuple[str, str, IssueFn, ConsumeFn, bool]] = [
    ("chat", TICKET_KEY_PREFIX, issue_chat_ws_ticket, consume_chat_ws_ticket, True),
    ("inbox", INBOX_TICKET_KEY_PREFIX, issue_inbox_ws_ticket, consume_inbox_ws_ticket, False),
    (
        "task_comments",
        TASK_COMMENTS_TICKET_KEY_PREFIX,
        issue_task_comments_ws_ticket,
        consume_task_comments_ws_ticket,
        True,
    ),
    (
        "document_comments",
        DOCUMENT_COMMENTS_TICKET_KEY_PREFIX,
        issue_document_comments_ws_ticket,
        consume_document_comments_ws_ticket,
        True,
    ),
    (
        "document_page",
        DOCUMENT_PAGE_TICKET_KEY_PREFIX,
        issue_document_page_ws_ticket,
        consume_document_page_ws_ticket,
        True,
    ),
    ("nav_tree", NAV_TREE_TICKET_KEY_PREFIX, issue_nav_tree_ws_ticket, consume_nav_tree_ws_ticket, False),
    ("task_board", TASK_BOARD_TICKET_KEY_PREFIX, issue_task_board_ws_ticket, consume_task_board_ws_ticket, False),
    (
        "specialist_board",
        SPECIALIST_BOARD_TICKET_KEY_PREFIX,
        issue_specialist_board_ws_ticket,
        consume_specialist_board_ws_ticket,
        False,
    ),
    ("calendar", CALENDAR_TICKET_KEY_PREFIX, issue_calendar_ws_ticket, consume_calendar_ws_ticket, False),
]


async def _issue(issue: IssueFn, *, has_entity: bool, user: UserPublic, entity_id: uuid.UUID) -> str:
    if has_entity:
        return await issue(entity_id, user)
    return await issue(user)


def _expected(has_entity: bool, user: UserPublic, entity_id: uuid.UUID) -> object:
    return (entity_id, user) if has_entity else user


# --- memory (no Redis) ---


@pytest.mark.parametrize(
    ("_kind", "_prefix", "issue", "consume", "has_entity"),
    _TICKET_KINDS,
    ids=[row[0] for row in _TICKET_KINDS],
)
async def test_ws_ticket_memory_roundtrip_is_one_time(
    _kind: str,
    _prefix: str,
    issue: IssueFn,
    consume: ConsumeFn,
    has_entity: bool,
) -> None:
    u = _user()
    entity_id = uuid.uuid4()
    with _no_redis():
        tid = await _issue(issue, has_entity=has_entity, user=u, entity_id=entity_id)
    with _no_redis():
        assert await consume(tid) == _expected(has_entity, u, entity_id)
    with _no_redis():
        assert await consume(tid) is None


async def test_chat_ws_ticket_memory_expired() -> None:
    """Expiry через публичный issue/consume, не через запись в _mem_store без prefix."""
    u = _user()
    chat_id = uuid.uuid4()
    clock = {"now": 1_000.0}

    def _mono() -> float:
        return clock["now"]

    with patch("app.infrastructure.ws._ticket_base.time.monotonic", side_effect=_mono):
        with _no_redis():
            tid = await issue_chat_ws_ticket(chat_id, u)
        clock["now"] = 1_000.0 + TICKET_TTL_SEC + 1.0
        with _no_redis():
            assert await consume_chat_ws_ticket(tid) is None


async def test_memory_consume_cleans_expired_prefixed_key() -> None:
    u = _user()
    entity_id = uuid.uuid4()
    dead_key = f"{TASK_COMMENTS_TICKET_KEY_PREFIX}{uuid.uuid4()}"
    _mem_store[dead_key] = ("{}", time.monotonic() - 1.0)
    with _no_redis():
        tid = await issue_task_comments_ws_ticket(entity_id, u)
    with _no_redis():
        assert await consume_task_comments_ws_ticket(tid) == (entity_id, u)
    assert dead_key not in _mem_store


@pytest.mark.parametrize(
    ("prefix", "consume", "payload"),
    [
        (
            TICKET_KEY_PREFIX,
            consume_chat_ws_ticket,
            json.dumps({"chat_id": "not-a-uuid", "user": _user().model_dump()}),
        ),
        (INBOX_TICKET_KEY_PREFIX, consume_inbox_ws_ticket, "not-json"),
        (TASK_COMMENTS_TICKET_KEY_PREFIX, consume_task_comments_ws_ticket, "{}"),
        (DOCUMENT_COMMENTS_TICKET_KEY_PREFIX, consume_document_comments_ws_ticket, "{}"),
        (DOCUMENT_PAGE_TICKET_KEY_PREFIX, consume_document_page_ws_ticket, "{}"),
        (NAV_TREE_TICKET_KEY_PREFIX, consume_nav_tree_ws_ticket, "{}"),
        (TASK_BOARD_TICKET_KEY_PREFIX, consume_task_board_ws_ticket, "{}"),
        (SPECIALIST_BOARD_TICKET_KEY_PREFIX, consume_specialist_board_ws_ticket, "{}"),
        (CALENDAR_TICKET_KEY_PREFIX, consume_calendar_ws_ticket, "{}"),
    ],
    ids=[
        "chat",
        "inbox",
        "task_comments",
        "document_comments",
        "document_page",
        "nav_tree",
        "task_board",
        "specialist_board",
        "calendar",
    ],
)
async def test_ws_ticket_parse_error_returns_none(
    prefix: str,
    consume: ConsumeFn,
    payload: str,
) -> None:
    tid = str(uuid.uuid4())
    _mem_store[f"{prefix}{tid}"] = (payload, time.monotonic() + 60.0)
    with _no_redis():
        assert await consume(tid) is None


async def test_consume_unknown_ticket_memory_returns_none() -> None:
    unknown = str(uuid.uuid4())
    with _no_redis():
        assert await consume_inbox_ws_ticket(unknown) is None
        assert await consume_task_comments_ws_ticket(unknown) is None
        assert await consume_document_comments_ws_ticket(unknown) is None
        assert await consume_nav_tree_ws_ticket(unknown) is None
        assert await consume_document_page_ws_ticket(unknown) is None
        assert await consume_task_board_ws_ticket(unknown) is None
        assert await consume_specialist_board_ws_ticket(unknown) is None
        assert await consume_calendar_ws_ticket(unknown) is None


async def test_cross_prefix_chat_ticket_not_consumed_as_inbox() -> None:
    u = _user()
    chat_id = uuid.uuid4()
    with _no_redis():
        tid = await issue_chat_ws_ticket(chat_id, u)
        assert await consume_inbox_ws_ticket(tid) is None
        assert await consume_chat_ws_ticket(tid) == (chat_id, u)


async def test_cross_prefix_inbox_ticket_not_consumed_as_chat() -> None:
    u = _user()
    with _no_redis():
        tid = await issue_inbox_ws_ticket(u)
        assert await consume_chat_ws_ticket(tid) is None
        assert await consume_inbox_ws_ticket(tid) == u


# --- Redis ---


@pytest.mark.parametrize(
    ("_kind", "_prefix", "issue", "consume", "has_entity"),
    _TICKET_KINDS,
    ids=[row[0] for row in _TICKET_KINDS],
)
async def test_ws_ticket_redis_roundtrip_is_one_time(
    _kind: str,
    _prefix: str,
    issue: IssueFn,
    consume: ConsumeFn,
    has_entity: bool,
) -> None:
    r = _FakeRedis()
    u = _user()
    entity_id = uuid.uuid4()
    with _with_redis(r):
        tid = await _issue(issue, has_entity=has_entity, user=u, entity_id=entity_id)
        assert r.last_ex == TICKET_TTL_SEC
        assert await consume(tid) == _expected(has_entity, u, entity_id)
        assert await consume(tid) is None


async def test_redis_missing_ticket_returns_none() -> None:
    with _with_redis(_FakeRedis()):
        assert await consume_chat_ws_ticket(str(uuid.uuid4())) is None
