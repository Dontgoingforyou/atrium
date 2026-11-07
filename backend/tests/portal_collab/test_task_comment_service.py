"""Сервис task_comment: ответы и публикации (inbox/ws) через monkeypatch."""

from __future__ import annotations

import uuid

import pytest
from app.infrastructure.db.models.portal_task import PortalTaskComment
from app.portal_collab.schemas.task import PortalTaskCreate, TaskCommentCreate
from app.portal_collab.services import task as task_svc
from app.portal_collab.services import task_comment as comment_svc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin


@pytest.mark.asyncio
async def test_list_comments_and_create_reply_with_publish_mocks(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()

    async def _noop_inbox(_subs: list[str], *, notification_ids_by_sub: object | None = None) -> None:
        return None

    class _FakeMgr:
        async def publish(self, _task_id: uuid.UUID, _payload: dict) -> None:
            return None

    fake = _FakeMgr()
    monkeypatch.setattr(
        "app.portal_collab.services.task_comment.publish_portal_notification_updates",
        _noop_inbox,
    )
    monkeypatch.setattr(
        "app.portal_collab.services.task_comment.get_task_comments_manager",
        lambda: fake,
    )

    task = await task_svc.create_task(sqlite_session, admin, PortalTaskCreate(title="Тред", assignee_sub="admin-sub"))
    parent = await comment_svc.create_comment(
        sqlite_session,
        admin,
        task.id,
        TaskCommentCreate(body="Корень", mentions=[]),
    )
    reply = await comment_svc.create_comment(
        sqlite_session,
        admin,
        task.id,
        TaskCommentCreate(body="Ответ", mentions=[], parent_id=parent.id),
    )
    assert reply.parent_id == parent.id

    rows = await comment_svc.list_comments(sqlite_session, admin, task.id)
    assert len(rows) == 1
    assert rows[0].id == parent.id
    child_rows = (
        (
            await sqlite_session.execute(
                select(PortalTaskComment).where(PortalTaskComment.parent_id == parent.id),
            )
        )
        .scalars()
        .all()
    )
    assert len(child_rows) == 1
    assert child_rows[0].id == reply.id
