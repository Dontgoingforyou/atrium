"""Параллельные PATCH задачи с одним expected_version (CAS)."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from app.core.enums import TaskPriority, TaskStatus
from app.core.exceptions import ConflictError
from app.infrastructure.db.models.portal_task import PortalTask
from app.portal_collab.schemas.task import PortalTaskUpdate
from app.portal_collab.services import _task_mutations as task_mut
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.helpers.portal_test_users import user_portal_admin


@pytest.mark.asyncio
async def test_parallel_update_task_same_version_one_ok(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Два concurrent update с одним expected_version → один ok, один ConflictError."""

    async def _noop_publish(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(task_mut, "_publish_board_event", _noop_publish)

    user = user_portal_admin()
    task_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(
            PortalTask(
                id=task_id,
                title="Задача",
                creator_sub=user.sub,
                status=TaskStatus.TODO.value,
                priority=TaskPriority.MEDIUM.value,
                version=1,
            )
        )
        await s.commit()

    outcomes: list[str] = []

    async def try_update(title: str) -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await task_mut.update_task(
                    sess,
                    user,
                    task_id,
                    PortalTaskUpdate(expected_version=1, title=title),
                )
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    await asyncio.gather(try_update("from-a"), try_update("from-b"))

    assert sorted(outcomes) == ["conflict", "ok"]

    async with sqlite_concurrency_factory() as s:
        row = (await s.execute(select(PortalTask).where(PortalTask.id == task_id))).scalar_one()
        assert row.version == 2
        assert row.title in ("from-a", "from-b")
