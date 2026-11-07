"""Гонки collab: mention-уведомление и pref доски задач."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskComment
from app.infrastructure.db.models.portal_user_task_board_pref import PortalUserTaskBoardPref
from app.portal_collab.schemas.task import TaskBoardPrefWrite
from app.portal_collab.services.notification import create_mention_notifications
from app.portal_collab.services.task_board_pref import put_task_board_pref
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.concurrency.conftest import profile_from_user
from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular


@pytest.mark.asyncio
async def test_parallel_create_mention_notifications_one_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    author = user_portal_admin()
    mentioned = user_portal_regular()
    task_id = uuid.uuid4()
    comment_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add_all([profile_from_user(author), profile_from_user(mentioned)])
        s.add(
            PortalTask(
                id=task_id,
                title="Задача",
                creator_sub=author.sub,
                assignee_sub=mentioned.sub,
                status=TaskStatus.TODO.value,
                priority=TaskPriority.MEDIUM.value,
            )
        )
        s.add(
            PortalTaskComment(
                id=comment_id,
                task_id=task_id,
                author_sub=author.sub,
                body=f"Привет @{mentioned.sub}",
                mentions=[mentioned.sub],
            )
        )
        await s.commit()

    async with sqlite_concurrency_factory() as s:
        task = await s.get(PortalTask, task_id)
        comment = await s.get(PortalTaskComment, comment_id)
        assert task is not None and comment is not None

    async def try_notify() -> None:
        async with sqlite_concurrency_factory() as sess:
            task_row = await sess.get(PortalTask, task_id)
            comment_row = await sess.get(PortalTaskComment, comment_id)
            assert task_row is not None and comment_row is not None
            await create_mention_notifications(sess, task_row, comment_row, author.sub)
            await sess.commit()

    await asyncio.gather(try_notify(), try_notify())

    async with sqlite_concurrency_factory() as s:
        n = await s.execute(
            select(func.count())
            .select_from(PortalNotification)
            .where(
                PortalNotification.recipient_sub == mentioned.sub,
                PortalNotification.comment_id == comment_id,
            )
        )
        assert n.scalar_one() == 1


@pytest.mark.asyncio
async def test_parallel_put_task_board_pref_one_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = user_portal_regular()
    body = TaskBoardPrefWrite(column_order=["todo", "done"])

    async def try_put() -> None:
        async with sqlite_concurrency_factory() as sess:
            await put_task_board_pref(sess, user, body)

    await asyncio.gather(try_put(), try_put())

    async with sqlite_concurrency_factory() as s:
        n = await s.execute(
            select(func.count())
            .select_from(PortalUserTaskBoardPref)
            .where(PortalUserTaskBoardPref.user_sub == user.sub)
        )
        assert n.scalar_one() == 1
