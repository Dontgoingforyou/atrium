"""Загрузка данных для текста уведомлений Telegram."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from app.core.enums import TaskPriority
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.db.models.portal_task import PortalTask
from app.portal_telegram.services.notification_fetch import (
    fetch_mention_display_labels_longest_first,
    fetch_notification_for_recipient,
    mention_subs_from_notification,
)


def test_mention_subs_task_mention() -> None:
    n = MagicMock()
    n.type = "task_mention"
    n.comment = MagicMock()
    n.comment.mentions = ["a", "b"]
    n.document_comment = None
    assert mention_subs_from_notification(n) == ["a", "b"]


def test_mention_subs_document_mention() -> None:
    n = MagicMock()
    n.type = "document_mention"
    n.comment = None
    n.document_comment = MagicMock()
    n.document_comment.mentions = ["d1", "d2"]
    assert mention_subs_from_notification(n) == ["d1", "d2"]


def test_mention_subs_other_type_returns_empty() -> None:
    n = MagicMock()
    n.type = "task_assigned"
    n.comment = MagicMock()
    n.comment.mentions = ["ignored"]
    assert mention_subs_from_notification(n) == []


def test_mention_subs_task_mention_without_comment_returns_empty() -> None:
    n = MagicMock()
    n.type = "task_mention"
    n.comment = None
    assert mention_subs_from_notification(n) == []


@pytest.mark.asyncio
async def test_fetch_mention_display_labels_longest_first(sqlite_session) -> None:
    """Порядок подписей — по убыванию длины строки имени."""
    labels = await fetch_mention_display_labels_longest_first(
        sqlite_session,
        ["user-sub", "admin-sub", "user-sub"],
    )
    assert labels == ["Admin", "User"]


@pytest.mark.asyncio
async def test_fetch_notification_for_recipient_by_id(sqlite_session) -> None:
    tid = uuid4()
    sqlite_session.add(
        PortalTask(
            id=tid,
            title="Задача тест",
            creator_sub="admin-sub",
            priority=TaskPriority.MEDIUM,
        )
    )
    await sqlite_session.flush()
    t_old = datetime.now(UTC) - timedelta(days=2)
    t_new = datetime.now(UTC) - timedelta(days=1)
    nid_old = uuid4()
    nid_new = uuid4()
    sqlite_session.add(
        PortalNotification(
            id=nid_old,
            recipient_sub="user-sub",
            type="task_assigned",
            task_id=tid,
            author_sub="admin-sub",
            created_at=t_old,
        )
    )
    sqlite_session.add(
        PortalNotification(
            id=nid_new,
            recipient_sub="user-sub",
            type="task_assigned",
            task_id=tid,
            author_sub="admin-sub",
            created_at=t_new,
        )
    )
    await sqlite_session.commit()

    by_id = await fetch_notification_for_recipient(sqlite_session, "user-sub", notification_id=nid_old)
    assert by_id is not None
    assert by_id.id == nid_old

    missing = await fetch_notification_for_recipient(sqlite_session, "user-sub", notification_id=uuid4())
    assert missing is None

    without_id = await fetch_notification_for_recipient(sqlite_session, "user-sub")
    assert without_id is None
