"""Гонки воронки специалистов: колонка и закрепление на доске."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from app.core.auth_constants import SSO_GID_OUTSTAFF
from app.core.exceptions import ConflictError
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.portal_specialists.schemas.board import (
    ManagerSpecialistAdd,
    ManagerSpecialistPatch,
    SpecialistColumnCreate,
)
from app.portal_specialists.services.board_columns_statuses import create_specialist_column
from app.portal_specialists.services.board_entries import add_to_board, move_on_board
from app.schemas.auth import UserPublic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.concurrency.conftest import profile_from_user
from tests.helpers.portal_test_users import user_portal_admin


def _manager() -> UserPublic:
    return UserPublic(
        sub="mgr-race",
        email="mgr-race@example.com",
        username="mgr-race",
        full_name="Mgr Race",
        idp_groups=["outstaff"],
        is_portal_admin=False,
        gid_number=SSO_GID_OUTSTAFF,
        position="au_chief",
    )


def _student() -> UserPublic:
    return UserPublic(
        sub="student-race",
        email="st@example.com",
        username="st",
        full_name="Student",
        idp_groups=["students"],
        is_portal_admin=False,
    )


@pytest.mark.asyncio
async def test_parallel_create_specialist_column_one_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    admin = user_portal_admin()
    data = SpecialistColumnCreate(key="race-col", title="Гонка", color="#112233", position=0)
    outcomes: list[str] = []

    async def try_create() -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await create_specialist_column(sess, admin, data)
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    await asyncio.gather(try_create(), try_create())
    assert sorted(outcomes) == ["conflict", "ok"]

    async with sqlite_concurrency_factory() as s:
        n = await s.execute(
            select(func.count()).select_from(PortalSpecialistColumn).where(PortalSpecialistColumn.key == "race-col")
        )
        assert n.scalar_one() == 1


@pytest.mark.asyncio
async def test_parallel_add_to_board_one_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.portal_specialists.services.board_entries.publish_specialist_board_event",
        AsyncMock(),
    )
    manager = _manager()
    student = _student()
    async with sqlite_concurrency_factory() as s:
        s.add(profile_from_user(manager))
        s.add(profile_from_user(student, portal_chat_allowed=False))
        s.add(PortalSpecialistColumn(key="new", title="Новые", color="#000000", position=0))
        await s.commit()

    data = ManagerSpecialistAdd(specialist_sub=student.sub, column_key="new")
    outcomes: list[str] = []

    async def try_add() -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await add_to_board(sess, manager, data)
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    await asyncio.gather(try_add(), try_add())
    assert sorted(outcomes) == ["conflict", "ok"]

    async with sqlite_concurrency_factory() as s:
        n = await s.execute(
            select(func.count())
            .select_from(PortalManagerSpecialist)
            .where(
                PortalManagerSpecialist.manager_sub == manager.sub,
                PortalManagerSpecialist.specialist_sub == student.sub,
            )
        )
        assert n.scalar_one() == 1


@pytest.mark.asyncio
async def test_parallel_move_on_board_same_version_one_ok(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Два concurrent move с одним expected_version → один ok, один ConflictError."""
    monkeypatch.setattr(
        "app.portal_specialists.services.board_entries.publish_specialist_board_event",
        AsyncMock(),
    )
    manager = _manager()
    student = _student()
    async with sqlite_concurrency_factory() as s:
        s.add(profile_from_user(manager))
        s.add(profile_from_user(student, portal_chat_allowed=False))
        s.add(PortalSpecialistColumn(key="new", title="Новые", color="#000000", position=0))
        s.add(PortalSpecialistColumn(key="cv_sent", title="CV", color="#111111", position=1))
        s.add(PortalSpecialistColumn(key="hired", title="Hired", color="#222222", position=2))
        s.add(
            PortalManagerSpecialist(
                manager_sub=manager.sub,
                specialist_sub=student.sub,
                column_key="new",
                position=0,
                version=1,
            )
        )
        await s.commit()

    outcomes: list[str] = []

    async def try_move(column_key: str) -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await move_on_board(
                    sess,
                    manager,
                    student.sub,
                    ManagerSpecialistPatch(expected_version=1, column_key=column_key),
                )
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    await asyncio.gather(try_move("cv_sent"), try_move("hired"))
    assert sorted(outcomes) == ["conflict", "ok"]

    async with sqlite_concurrency_factory() as s:
        row = (
            await s.execute(
                select(PortalManagerSpecialist).where(
                    PortalManagerSpecialist.manager_sub == manager.sub,
                    PortalManagerSpecialist.specialist_sub == student.sub,
                )
            )
        ).scalar_one()
        assert row.version == 2
        assert row.column_key in ("cv_sent", "hired")
