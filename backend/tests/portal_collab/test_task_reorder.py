"""Перестановка задач: корректность индексов и инварианты при «параллельных» вызовах."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path

import app.infrastructure.db.models  # noqa: F401
import pytest
from app.core.config import Settings
from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.base import Base
from app.infrastructure.db.models.portal_task import PortalTask
from app.portal_collab.services import task as task_svc
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.helpers.portal_test_users import user_portal_admin
from tests.portal_collab.conftest import async_client_as


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _assert_contiguous_zero_based_positions(tasks: list[PortalTask], *, status: str) -> None:
    same = [t for t in tasks if t.status == status]
    positions = sorted(t.position for t in same)
    n = len(same)
    assert positions == list(range(n)), f"ожидались 0..{n - 1}, получили {positions}"


@pytest.mark.asyncio
async def test_reorder_sequential_same_status(sqlite_session: AsyncSession) -> None:
    user = user_portal_admin()
    base = _now_utc()
    t1 = PortalTask(
        title="a",
        creator_sub=user.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        position=0,
        created_at=base,
        updated_at=base,
    )
    t2 = PortalTask(
        title="b",
        creator_sub=user.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        position=1,
        created_at=base,
        updated_at=base,
    )
    t3 = PortalTask(
        title="c",
        creator_sub=user.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        position=2,
        created_at=base,
        updated_at=base,
    )
    sqlite_session.add_all([t1, t2, t3])
    await sqlite_session.commit()
    for o in (t1, t2, t3):
        await sqlite_session.refresh(o)

    # последний (pos 2) в начало
    await task_svc.reorder_task(sqlite_session, user, t3.id, TaskStatus.TODO.value, before_task_id=t1.id)
    rows = list((await sqlite_session.execute(select(PortalTask))).scalars().all())
    _assert_contiguous_zero_based_positions(rows, status=TaskStatus.TODO.value)
    by_title = {t.title: t.position for t in rows if t.status == TaskStatus.TODO.value}
    assert by_title == {"a": 1, "b": 2, "c": 0}


@pytest.mark.asyncio
async def test_reorder_subtasks_any_status_among_siblings(sqlite_session: AsyncSession) -> None:
    """Подзадачи одного родителя меняют местами порядок, не трогая чужие задачи колонки."""
    user = user_portal_admin()
    base = _now_utc()
    parent = PortalTask(
        title="parent",
        creator_sub=user.sub,
        status=TaskStatus.IN_PROGRESS.value,
        priority=TaskPriority.MEDIUM.value,
        position=0,
        created_at=base,
        updated_at=base,
    )
    outsider = PortalTask(
        title="outsider",
        creator_sub=user.sub,
        status=TaskStatus.IN_PROGRESS.value,
        priority=TaskPriority.MEDIUM.value,
        position=5,
        created_at=base,
        updated_at=base,
    )
    sqlite_session.add_all([parent, outsider])
    await sqlite_session.commit()
    await sqlite_session.refresh(parent)
    await sqlite_session.refresh(outsider)

    child_a = PortalTask(
        title="child-a",
        creator_sub=user.sub,
        status=TaskStatus.IN_PROGRESS.value,
        priority=TaskPriority.MEDIUM.value,
        parent_task_id=parent.id,
        position=0,
        created_at=base,
        updated_at=base,
    )
    child_done = PortalTask(
        title="child-done",
        creator_sub=user.sub,
        status=TaskStatus.DONE.value,
        priority=TaskPriority.MEDIUM.value,
        parent_task_id=parent.id,
        position=1,
        created_at=base,
        updated_at=base,
    )
    child_c = PortalTask(
        title="child-c",
        creator_sub=user.sub,
        status=TaskStatus.IN_PROGRESS.value,
        priority=TaskPriority.MEDIUM.value,
        parent_task_id=parent.id,
        position=2,
        created_at=base,
        updated_at=base,
    )
    sqlite_session.add_all([child_a, child_done, child_c])
    await sqlite_session.commit()
    for row in (child_a, child_done, child_c):
        await sqlite_session.refresh(row)

    await task_svc.reorder_task(
        sqlite_session,
        user,
        child_c.id,
        TaskStatus.IN_PROGRESS.value,
        before_task_id=child_a.id,
    )

    rows = list((await sqlite_session.execute(select(PortalTask))).scalars().all())
    by_title = {t.title: t for t in rows}
    assert by_title["child-c"].position == 0
    assert by_title["child-a"].position == 1
    assert by_title["child-done"].position == 2
    assert by_title["child-c"].status == TaskStatus.IN_PROGRESS.value
    assert by_title["child-done"].status == TaskStatus.DONE.value
    assert by_title["outsider"].position == 5


@pytest.mark.asyncio
async def test_reorder_concurrent_invariants_file_sqlite(tmp_path: Path) -> None:
    """Два session из одного файла SQLite: инвариант «без дыр и дубликатов position» в колонке."""
    db_path = tmp_path / "reorder_race.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url)

    @event.listens_for(engine.sync_engine, "connect")
    def _fk(dbapi_connection: object, _connection_record: object) -> None:
        cur = dbapi_connection.cursor()  # type: ignore[union-attr]
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    user = user_portal_admin()
    base = _now_utc()
    ids: list[uuid.UUID] = []
    async with factory() as s0:
        for i in range(4):
            t = PortalTask(
                title=f"t{i}",
                creator_sub=user.sub,
                status=TaskStatus.TODO.value,
                priority=TaskPriority.MEDIUM.value,
                position=i,
                created_at=base,
                updated_at=base,
            )
            s0.add(t)
        await s0.commit()
        for t in (await s0.execute(select(PortalTask))).scalars().all():
            ids.append(t.id)
        assert len(ids) == 4

    a, b, c, d_ = ids

    async def r1() -> None:
        async with factory() as s:
            # разные сценарии новой позиции
            await task_svc.reorder_task(s, user, c, TaskStatus.TODO.value, before_task_id=a)

    async def r2() -> None:
        async with factory() as s:
            await task_svc.reorder_task(s, user, a, TaskStatus.TODO.value, after_task_id=c)

    await asyncio.gather(r1(), r2())

    async with factory() as s_check:
        rows = list((await s_check.execute(select(PortalTask))).scalars().all())
        _assert_contiguous_zero_based_positions(rows, status=TaskStatus.TODO.value)

    await engine.dispose()


@pytest.mark.asyncio
async def test_reorder_via_http_ok(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    user = user_portal_admin()
    base = _now_utc()
    t1 = PortalTask(
        title="http-1",
        creator_sub=user.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        position=0,
        created_at=base,
        updated_at=base,
    )
    t2 = PortalTask(
        title="http-2",
        creator_sub=user.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        position=1,
        created_at=base,
        updated_at=base,
    )
    sqlite_session.add_all([t1, t2])
    await sqlite_session.commit()
    await sqlite_session.refresh(t1)
    async with async_client_as(sqlite_session, user_portal_admin) as ac:
        r = await ac.post(
            "/api/v1/portal/tasks/reorder",
            json={
                "task_id": str(t2.id),
                "before_task_id": str(t1.id),
                "status": "todo",
            },
        )
        assert r.status_code == 200, r.text
    rows = list((await sqlite_session.execute(select(PortalTask))).scalars().all())
    _assert_contiguous_zero_based_positions(rows, status=TaskStatus.TODO.value)
    by_id = {str(t.id): t.position for t in rows if t.status == TaskStatus.TODO.value}
    assert by_id[str(t2.id)] == 0
    assert by_id[str(t1.id)] == 1
