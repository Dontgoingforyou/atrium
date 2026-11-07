"""Интеграционные тесты: таймшиты, CRUD, отчёты и сводка."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.auth_constants import IDP_GROUP_MANAGER
from app.core.config import Settings
from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_time_entry import PortalTimeEntry
from app.main import app
from app.schemas.auth import UserPublic
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_au_specialist_with_outstaff,
    user_manager_students_outstaff,
    user_portal_admin,
    user_portal_developer,
    user_portal_manager,
    user_portal_regular,
)
from tests.portal_time_entries.conftest import (
    TIME_ENTRIES_API,
    assert_api_error,
    assert_pydantic_422,
)


@pytest.mark.asyncio
async def test_time_entry_crud_and_summary(client_regular_entries: AsyncClient) -> None:
    r = await client_regular_entries.post(
        TIME_ENTRIES_API,
        json={
            "worked_on": "2026-04-20",
            "minutes": 60,
            "note": "разработка",
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()
    eid = created["id"]
    assert created["user_sub"] == "user-sub"
    assert created["minutes"] == 60

    r2 = await client_regular_entries.get(
        f"{TIME_ENTRIES_API}/summary",
        params={"date_from": "2026-04-20", "date_to": "2026-04-20"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json() == {"total_minutes": 60, "entries_count": 1}

    r4 = await client_regular_entries.patch(
        f"{TIME_ENTRIES_API}/{eid}",
        json={"expected_version": created["version"], "minutes": 90, "note": "обновлено"},
    )
    assert r4.status_code == 200
    assert r4.json()["minutes"] == 90

    r5 = await client_regular_entries.delete(f"{TIME_ENTRIES_API}/{eid}")
    assert r5.status_code == 204

    r7 = await client_regular_entries.get(TIME_ENTRIES_API)
    assert all(e["id"] != eid for e in r7.json()["items"])

    r_sum = await client_regular_entries.get(
        f"{TIME_ENTRIES_API}/summary",
        params={"date_from": "2026-04-20", "date_to": "2026-04-20"},
    )
    assert r_sum.status_code == 200
    assert r_sum.json() == {"total_minutes": 0, "entries_count": 0}


@pytest.mark.asyncio
async def test_manager_sees_user_entries_after_regular_deletes_own(
    client_regular_entries: AsyncClient,
    client_manager_entries: AsyncClient,
) -> None:
    """Менеджер фильтрует user_sub после того, как пользователь удалил свою запись."""
    r = await client_regular_entries.post(
        TIME_ENTRIES_API,
        json={"worked_on": "2026-04-10", "minutes": 45, "note": "временная"},
    )
    assert r.status_code == 201, r.text
    eid = r.json()["id"]
    assert (await client_regular_entries.delete(f"{TIME_ENTRIES_API}/{eid}")).status_code == 204

    r_mgr = await client_manager_entries.get(TIME_ENTRIES_API, params={"user_sub": "user-sub"})
    assert r_mgr.status_code == 200
    assert all(e["id"] != eid for e in r_mgr.json()["items"])


@pytest.mark.asyncio
async def test_time_entry_cannot_patch_others_entry(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    entry = PortalTimeEntry(
        user_sub="user-b",
        worked_on=date(2026, 4, 2),
        minutes=30,
    )
    sqlite_session.add(entry)
    await sqlite_session.commit()
    await sqlite_session.refresh(entry)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_regular
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.patch(
                f"/api/v1/portal/time-entries/{entry.id}",
                json={"expected_version": 1, "minutes": 99},
            )
            assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_filters_by_user_sub(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    sqlite_session.add(
        PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 4, 3), minutes=10),
    )
    sqlite_session.add(
        PortalTimeEntry(user_sub="user-b", worked_on=date(2026, 4, 3), minutes=20),
    )
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/portal/time-entries", params={"user_sub": "user-b"})
            assert r.status_code == 200
            data = r.json()["items"]
            assert len(data) == 1
            assert data[0]["user_sub"] == "user-b"

            s = await ac.get("/api/v1/portal/time-entries/summary", params={"user_sub": "user-sub"})
            assert s.status_code == 200
            assert s.json()["total_minutes"] == 10
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_time_entry_with_task_requires_visibility(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    task = PortalTask(
        title="Видимая задача",
        creator_sub="user-sub",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )
    sqlite_session.add(task)
    await sqlite_session.commit()
    await sqlite_session.refresh(task)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_regular
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/portal/time-entries",
                json={
                    "worked_on": "2026-04-05",
                    "minutes": 15,
                    "task_id": str(task.id),
                },
            )
            assert r.status_code == 201, r.text
            assert r.json()["task_id"] == str(task.id)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_time_entry_task_forbidden_if_not_visible(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Разработчик имеет доступ к таймшитам, но не видит чужую задачу — 403 на task_id."""
    task = PortalTask(
        title="Чужая задача",
        creator_sub="user-b",
        assignee_sub="user-b",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )
    sqlite_session.add(task)
    await sqlite_session.commit()
    await sqlite_session.refresh(task)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_developer
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/portal/time-entries",
                json={
                    "worked_on": "2026-04-06",
                    "minutes": 15,
                    "task_id": str(task.id),
                },
            )
            assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Тесты GET /portal/time-entries/report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_empty_when_no_entries(
    client_user: AsyncClient,
) -> None:
    r = await client_user.get("/api/v1/portal/time-entries/report")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_report_group_by_week(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Записи в разных ISO-неделях попадают в отдельные бакеты; поля period_label корректны."""
    # 2026-W15: 2026-04-06 (пн) — 2026-04-12 (вс)
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 4, 6), minutes=60))
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 4, 7), minutes=30))
    # 2026-W16: 2026-04-13 (пн) — 2026-04-19 (вс)
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 4, 13), minutes=90))
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_regular
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/portal/time-entries/report", params={"group_by": "week"})
            assert r.status_code == 200, r.text
            buckets = r.json()
            assert len(buckets) == 2

            w15 = buckets[0]
            assert w15["period_label"] == "2026-W15"
            assert w15["total_minutes"] == 90  # 60 + 30
            assert w15["entries_count"] == 2
            assert w15["date_start"] == "2026-04-06"
            assert w15["date_end"] == "2026-04-12"

            w16 = buckets[1]
            assert w16["period_label"] == "2026-W16"
            assert w16["total_minutes"] == 90
            assert w16["entries_count"] == 1
            assert w16["date_start"] == "2026-04-13"
            assert w16["date_end"] == "2026-04-19"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_report_group_by_month(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Записи в разных месяцах формируют бакеты с меткой YYYY-MM."""
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 3, 31), minutes=120))
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 4, 1), minutes=60))
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 4, 30), minutes=45))
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_regular
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/portal/time-entries/report", params={"group_by": "month"})
            assert r.status_code == 200, r.text
            buckets = r.json()
            assert len(buckets) == 2

            march = buckets[0]
            assert march["period_label"] == "2026-03"
            assert march["total_minutes"] == 120
            assert march["entries_count"] == 1
            assert march["date_start"] == "2026-03-01"
            assert march["date_end"] == "2026-03-31"

            april = buckets[1]
            assert april["period_label"] == "2026-04"
            assert april["total_minutes"] == 105  # 60 + 45
            assert april["entries_count"] == 2
            assert april["date_start"] == "2026-04-01"
            assert april["date_end"] == "2026-04-30"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_report_date_filter_narrows_buckets(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Параметры date_from / date_to ограничивают выборку."""
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 3, 1), minutes=60))
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 4, 1), minutes=30))
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 5, 1), minutes=20))
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_regular
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(
                "/api/v1/portal/time-entries/report",
                params={"group_by": "month", "date_from": "2026-04-01", "date_to": "2026-04-30"},
            )
            assert r.status_code == 200
            buckets = r.json()
            assert len(buckets) == 1
            assert buckets[0]["period_label"] == "2026-04"
            assert buckets[0]["total_minutes"] == 30
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_report_rbac_user_sees_only_own_entries(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Обычный пользователь видит в отчёте только свои записи, чужие не попадают в бакеты."""
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 4, 1), minutes=60))
    sqlite_session.add(PortalTimeEntry(user_sub="user-b", worked_on=date(2026, 4, 1), minutes=999))
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_regular
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/portal/time-entries/report", params={"group_by": "month"})
            assert r.status_code == 200
            buckets = r.json()
            assert len(buckets) == 1
            assert buckets[0]["total_minutes"] == 60  # только своя запись
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_report_rbac_admin_sees_all_and_can_filter(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Администратор видит все записи; опциональный фильтр user_sub работает."""
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 4, 1), minutes=60))
    sqlite_session.add(PortalTimeEntry(user_sub="user-b", worked_on=date(2026, 4, 2), minutes=40))
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # без фильтра — все записи
            r_all = await ac.get("/api/v1/portal/time-entries/report", params={"group_by": "month"})
            assert r_all.status_code == 200
            assert r_all.json()[0]["total_minutes"] == 100  # 60 + 40

            # фильтр по конкретному пользователю
            r_filtered = await ac.get(
                "/api/v1/portal/time-entries/report",
                params={"group_by": "month", "user_sub": "user-b"},
            )
            assert r_filtered.status_code == 200
            assert r_filtered.json()[0]["total_minutes"] == 40
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_report_week_iso_year_boundary(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Граничный случай ISO-недели: 2025-12-28 (вс, W52) и 2025-12-29 (пн, W01 2026)
    попадают в разные бакеты, ISO-год для метки берётся корректно."""
    # 2025-12-28 — воскресенье ISO 2025-W52
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2025, 12, 28), minutes=30))
    # 2025-12-29 — понедельник ISO 2026-W01
    sqlite_session.add(PortalTimeEntry(user_sub="user-sub", worked_on=date(2025, 12, 29), minutes=45))
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_regular
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/portal/time-entries/report", params={"group_by": "week"})
            assert r.status_code == 200, r.text
            buckets = r.json()
            labels = [b["period_label"] for b in buckets]
            assert "2025-W52" in labels
            assert "2026-W01" in labels
            w52 = next(b for b in buckets if b["period_label"] == "2025-W52")
            assert w52["total_minutes"] == 30
            w01 = next(b for b in buckets if b["period_label"] == "2026-W01")
            assert w01["total_minutes"] == 45
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Роль портала «manager» — фильтр user_sub (тот же контракт, что list_report)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_time_entries_manager_may_filter_by_other_user_sub(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    sqlite_session.add(
        PortalTimeEntry(user_sub="user-b", worked_on=date(2026, 6, 1), minutes=77),
    )
    sqlite_session.add(
        PortalTimeEntry(user_sub="manager-sub", worked_on=date(2026, 6, 1), minutes=5),
    )
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_manager
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/portal/time-entries", params={"user_sub": "user-b"})
            assert r.status_code == 200, r.text
            data = r.json()["items"]
            assert len(data) == 1
            assert data[0]["user_sub"] == "user-b"
            assert data[0]["minutes"] == 77
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_summary_manager_may_filter_by_other_user_sub(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    sqlite_session.add(
        PortalTimeEntry(user_sub="user-b", worked_on=date(2026, 6, 10), minutes=40),
    )
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_manager
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(
                "/api/v1/portal/time-entries/summary",
                params={"date_from": "2026-06-01", "date_to": "2026-06-30", "user_sub": "user-b"},
            )
            assert r.status_code == 200, r.text
            assert r.json() == {"total_minutes": 40, "entries_count": 1}
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_manager_cannot_patch_others_entry(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Менеджер видит чужие записи через фильтр user_sub, но не может их редактировать."""
    entry = PortalTimeEntry(user_sub="user-b", worked_on=date(2026, 6, 5), minutes=45)
    sqlite_session.add(entry)
    await sqlite_session.commit()
    await sqlite_session.refresh(entry)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_manager
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.patch(
                f"/api/v1/portal/time-entries/{entry.id}",
                json={"expected_version": 1, "minutes": 99},
            )
            assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_manager_cannot_delete_others_entry(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Менеджер не может удалить чужую запись — только администратор портала."""
    entry = PortalTimeEntry(user_sub="user-b", worked_on=date(2026, 6, 6), minutes=30)
    sqlite_session.add(entry)
    await sqlite_session.commit()
    await sqlite_session.refresh(entry)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_manager
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.delete(f"/api/v1/portal/time-entries/{entry.id}")
            assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Роль «Разработчик» (students) — RBAC и удаление
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_developer_can_create_own_entry(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Разработчик (students) создаёт запись с task_name — 201, поле сохраняется."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_developer
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/portal/time-entries",
                json={
                    "worked_on": "2026-05-01",
                    "minutes": 120,
                    "task_name": "Реализация фичи X",
                    "note": "Написал тесты и документацию",
                },
            )
            assert r.status_code == 201, r.text
            data = r.json()
            assert data["user_sub"] == "dev-sub"
            assert data["task_name"] == "Реализация фичи X"
            assert data["note"] == "Написал тесты и документацию"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_developer_sees_only_own_entries(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Разработчик видит только свои записи — чужие не попадают в список."""
    sqlite_session.add(PortalTimeEntry(user_sub="dev-sub", worked_on=date(2026, 5, 2), minutes=60))
    sqlite_session.add(PortalTimeEntry(user_sub="other-sub", worked_on=date(2026, 5, 2), minutes=999))
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_developer
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/portal/time-entries")
            assert r.status_code == 200, r.text
            entries = r.json()["items"]
            assert all(e["user_sub"] == "dev-sub" for e in entries)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_developer_cannot_read_others_entry(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Разработчик получает 403 при попытке изменить чужую запись."""
    entry = PortalTimeEntry(user_sub="other-sub", worked_on=date(2026, 5, 3), minutes=30)
    sqlite_session.add(entry)
    await sqlite_session.commit()
    await sqlite_session.refresh(entry)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_developer
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.patch(
                f"/api/v1/portal/time-entries/{entry.id}",
                json={"expected_version": 1, "minutes": 99},
            )
            assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_developer_deletes_own_entry(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Разработчик удаляет свою запись (DELETE): записи больше нет в списке и в сводке за месяц."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_developer
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r_create = await ac.post(
                "/api/v1/portal/time-entries",
                json={"worked_on": "2026-05-04", "minutes": 45, "task_name": "Задача"},
            )
            assert r_create.status_code == 201
            eid = r_create.json()["id"]

            r_del = await ac.delete(f"/api/v1/portal/time-entries/{eid}")
            assert r_del.status_code == 204

            r_list = await ac.get("/api/v1/portal/time-entries")
            assert r_list.status_code == 200
            assert all(e["id"] != eid for e in r_list.json()["items"])

            r_sum = await ac.get(
                "/api/v1/portal/time-entries/summary",
                params={"date_from": "2026-05-01", "date_to": "2026-05-31"},
            )
            assert r_sum.status_code == 200
            assert r_sum.json()["entries_count"] == 0
            assert r_sum.json()["total_minutes"] == 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_au_specialist_outstaff_only_can_access_own_timesheets(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Специалист АУ (position=au_specialist) с только outstaff — доступ к своим таймшитам."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    def _user() -> UserPublic:
        return UserPublic(
            sub="au-spec-outstaff-sub",
            email="ilya@example.com",
            username="ilya",
            full_name="User Hours",
            idp_groups=[IDP_GROUP_MANAGER],
            is_portal_admin=False,
            position="au_specialist",
        )

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = _user
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r_post = await ac.post(
                "/api/v1/portal/time-entries",
                json={"worked_on": "2026-05-06", "minutes": 60, "task_name": "Тест"},
            )
            assert r_post.status_code == 201

            r_list = await ac.get("/api/v1/portal/time-entries")
            assert r_list.status_code == 200
            assert r_list.json()["total"] == 1

            r_sum = await ac.get("/api/v1/portal/time-entries/summary")
            assert r_sum.status_code == 200
            assert r_sum.json()["total_minutes"] == 60
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_au_specialist_with_outstaff_and_students_can_access_timesheets(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Специалист АУ с outstaff+students — тоже только свои таймшиты, не менеджерский список."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_au_specialist_with_outstaff
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r_list = await ac.get("/api/v1/portal/time-entries")
            assert r_list.status_code == 200

            r_specialists = await ac.get(
                "/api/v1/portal/time-entries/specialists",
                params={"month": "2026-05"},
            )
            assert r_specialists.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_manager_gets_specialists_monthly_summary(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Менеджер получает список специалистов с суммарными часами за выбранный месяц."""
    sqlite_session.add(PortalTimeEntry(user_sub="dev-sub", worked_on=date(2026, 5, 1), minutes=60))
    sqlite_session.add(PortalTimeEntry(user_sub="dev-sub", worked_on=date(2026, 5, 15), minutes=90))
    sqlite_session.add(PortalTimeEntry(user_sub="other-dev", worked_on=date(2026, 5, 10), minutes=120))
    # Запись за другой месяц — не должна попасть
    sqlite_session.add(PortalTimeEntry(user_sub="dev-sub", worked_on=date(2026, 4, 30), minutes=999))
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_manager
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/portal/time-entries/specialists", params={"month": "2026-05"})
            assert r.status_code == 200, r.text
            body = r.json()
            assert "items" in body
            assert "total" in body

            subs = {item["user_sub"]: item for item in body["items"]}
            assert "dev-sub" in subs
            assert subs["dev-sub"]["total_minutes"] == 150  # 60 + 90
            assert subs["dev-sub"]["entries_count"] == 2
            assert "other-dev" in subs
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_month_param_filters_entries(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Параметр month фильтрует записи за конкретный месяц."""
    sqlite_session.add(PortalTimeEntry(user_sub="dev-sub", worked_on=date(2026, 4, 30), minutes=100))
    sqlite_session.add(PortalTimeEntry(user_sub="dev-sub", worked_on=date(2026, 5, 1), minutes=50))
    sqlite_session.add(PortalTimeEntry(user_sub="dev-sub", worked_on=date(2026, 5, 31), minutes=70))
    sqlite_session.add(PortalTimeEntry(user_sub="dev-sub", worked_on=date(2026, 6, 1), minutes=200))
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_developer
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/v1/portal/time-entries", params={"month": "2026-05"})
            assert r.status_code == 200, r.text
            entries = r.json()["items"]
            assert len(entries) == 2
            assert all(e["worked_on"].startswith("2026-05") for e in entries)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_invalid_month_returns_422(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """month=YYYY-13 не должен превращаться в 500 — ожидаем 422."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_manager
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r_list = await ac.get("/api/v1/portal/time-entries", params={"month": "2026-13"})
            assert r_list.status_code == 422
            r_spec = await ac.get("/api/v1/portal/time-entries/specialists", params={"month": "2026-00"})
            assert r_spec.status_code == 422
            r_exp = await ac.get(
                "/api/v1/portal/time-entries/export",
                params={"format": "csv", "month": "2026-13"},
            )
            assert r_exp.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_report_includes_more_than_500_entries(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Отчёт суммирует все записи месяца, а не первые 500 по дате."""
    sqlite_session.add_all(
        [PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 4, 1 + (i % 28)), minutes=1) for i in range(560)]
    )
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_regular
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(
                "/api/v1/portal/time-entries/report",
                params={"group_by": "month", "month": "2026-04"},
            )
            assert r.status_code == 200, r.text
            buckets = r.json()
            assert len(buckets) == 1
            assert buckets[0]["entries_count"] == 560
            assert buckets[0]["total_minutes"] == 560
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# 404, admin mutate, manager scope, task_id, pagination, validation
# ---------------------------------------------------------------------------

_UNKNOWN_ENTRY_ID = "00000000-0000-4000-8000-000000000099"
_UNKNOWN_TASK_ID = "00000000-0000-4000-8000-000000000088"


@pytest.mark.asyncio
async def test_patch_unknown_entry_returns_not_found(client_regular_entries: AsyncClient) -> None:
    r = await client_regular_entries.patch(
        f"{TIME_ENTRIES_API}/{_UNKNOWN_ENTRY_ID}",
        json={"expected_version": 1, "minutes": 99},
    )
    assert_api_error(r, 404, "not_found")


@pytest.mark.asyncio
async def test_delete_unknown_entry_returns_not_found(client_regular_entries: AsyncClient) -> None:
    r = await client_regular_entries.delete(f"{TIME_ENTRIES_API}/{_UNKNOWN_ENTRY_ID}")
    assert_api_error(r, 404, "not_found")


@pytest.mark.asyncio
async def test_admin_can_patch_and_delete_others_entry(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    entry = PortalTimeEntry(user_sub="user-b", worked_on=date(2026, 4, 8), minutes=40)
    sqlite_session.add(entry)
    await sqlite_session.commit()
    await sqlite_session.refresh(entry)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    prev_db = app.dependency_overrides.get(get_db_session)
    prev_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r_patch = await ac.patch(
                f"{TIME_ENTRIES_API}/{entry.id}",
                json={"expected_version": entry.version, "minutes": 55, "note": "admin edit"},
            )
            assert r_patch.status_code == 200, r_patch.text
            assert r_patch.json()["minutes"] == 55

            r_del = await ac.delete(f"{TIME_ENTRIES_API}/{entry.id}")
            assert r_del.status_code == 204
    finally:
        if prev_db is not None:
            app.dependency_overrides[get_db_session] = prev_db
        else:
            app.dependency_overrides.pop(get_db_session, None)
        if prev_user is not None:
            app.dependency_overrides[get_current_user] = prev_user
        else:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_developer_cannot_delete_others_entry(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    entry = PortalTimeEntry(user_sub="other-sub", worked_on=date(2026, 5, 8), minutes=30)
    sqlite_session.add(entry)
    await sqlite_session.commit()
    await sqlite_session.refresh(entry)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    prev_db = app.dependency_overrides.get(get_db_session)
    prev_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_developer
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.delete(f"{TIME_ENTRIES_API}/{entry.id}")
            assert_api_error(r, 403, "forbidden")
    finally:
        if prev_db is not None:
            app.dependency_overrides[get_db_session] = prev_db
        else:
            app.dependency_overrides.pop(get_db_session, None)
        if prev_user is not None:
            app.dependency_overrides[get_current_user] = prev_user
        else:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_create_with_unknown_task_id_returns_not_found(client_regular_entries: AsyncClient) -> None:
    r = await client_regular_entries.post(
        TIME_ENTRIES_API,
        json={
            "worked_on": "2026-04-20",
            "minutes": 30,
            "task_id": _UNKNOWN_TASK_ID,
        },
    )
    assert_api_error(r, 404, "not_found")


@pytest.mark.asyncio
async def test_patch_task_id_to_forbidden_task_returns_forbidden(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    task = PortalTask(
        title="Чужая",
        creator_sub="other-sub",
        assignee_sub="other-sub",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )
    own_entry = PortalTimeEntry(user_sub="dev-sub", worked_on=date(2026, 5, 12), minutes=30)
    sqlite_session.add_all([task, own_entry])
    await sqlite_session.commit()
    await sqlite_session.refresh(task)
    await sqlite_session.refresh(own_entry)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    prev_db = app.dependency_overrides.get(get_db_session)
    prev_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_developer
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.patch(
                f"{TIME_ENTRIES_API}/{own_entry.id}",
                json={"expected_version": own_entry.version, "task_id": str(task.id)},
            )
            assert_api_error(r, 403, "forbidden")
    finally:
        if prev_db is not None:
            app.dependency_overrides[get_db_session] = prev_db
        else:
            app.dependency_overrides.pop(get_db_session, None)
        if prev_user is not None:
            app.dependency_overrides[get_current_user] = prev_user
        else:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_manager_list_without_user_sub_sees_only_own(
    client_manager_entries: AsyncClient,
) -> None:
    r = await client_manager_entries.get(TIME_ENTRIES_API, params={"month": "2026-04"})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 2
    assert all(e["user_sub"] == "manager-sub" for e in items)


@pytest.mark.asyncio
async def test_admin_list_without_filter_sees_all_entries(
    client_admin_entries: AsyncClient,
) -> None:
    r = await client_admin_entries.get(TIME_ENTRIES_API, params={"month": "2026-04"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    subs = {e["user_sub"] for e in body["items"]}
    assert subs == {"manager-sub", "user-sub"}


@pytest.mark.asyncio
async def test_list_and_summary_filter_by_task_id(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    task = PortalTask(
        title="Своя задача",
        creator_sub="user-sub",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )
    sqlite_session.add(task)
    await sqlite_session.commit()
    await sqlite_session.refresh(task)

    sqlite_session.add(
        PortalTimeEntry(
            user_sub="user-sub",
            worked_on=date(2026, 4, 20),
            minutes=45,
            task_id=task.id,
            task_name="Своя задача",
        )
    )
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    prev_db = app.dependency_overrides.get(get_db_session)
    prev_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_regular
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r_list = await ac.get(
                TIME_ENTRIES_API,
                params={"month": "2026-04", "task_id": str(task.id)},
            )
            assert r_list.status_code == 200, r_list.text
            assert r_list.json()["total"] == 1
            assert r_list.json()["items"][0]["minutes"] == 45

            r_sum = await ac.get(
                f"{TIME_ENTRIES_API}/summary",
                params={"month": "2026-04", "task_id": str(task.id)},
            )
            assert r_sum.status_code == 200, r_sum.text
            assert r_sum.json() == {"total_minutes": 45, "entries_count": 1}
    finally:
        if prev_db is not None:
            app.dependency_overrides[get_db_session] = prev_db
        else:
            app.dependency_overrides.pop(get_db_session, None)
        if prev_user is not None:
            app.dependency_overrides[get_current_user] = prev_user
        else:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_pagination_limit_and_offset(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    for day in range(1, 6):
        sqlite_session.add(
            PortalTimeEntry(user_sub="user-sub", worked_on=date(2026, 7, day), minutes=10 * day),
        )
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    prev_db = app.dependency_overrides.get(get_db_session)
    prev_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_regular
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r_page = await ac.get(
                TIME_ENTRIES_API,
                params={"month": "2026-07", "limit": 2, "offset": 1},
            )
            assert r_page.status_code == 200, r_page.text
            body = r_page.json()
            assert body["total"] == 5
            assert len(body["items"]) == 2
            assert body["limit"] == 2
            assert body["skip"] == 1
    finally:
        if prev_db is not None:
            app.dependency_overrides[get_db_session] = prev_db
        else:
            app.dependency_overrides.pop(get_db_session, None)
        if prev_user is not None:
            app.dependency_overrides[get_current_user] = prev_user
        else:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("minutes", [0, 1441])
@pytest.mark.asyncio
async def test_create_invalid_minutes_returns_422(
    client_regular_entries: AsyncClient,
    minutes: int,
) -> None:
    r = await client_regular_entries.post(
        TIME_ENTRIES_API,
        json={"worked_on": "2026-04-01", "minutes": minutes},
    )
    assert_pydantic_422(r)


@pytest.mark.asyncio
async def test_specialists_admin_pagination(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    for idx, sub in enumerate(["dev-a", "dev-b", "dev-c"], start=1):
        sqlite_session.add(
            PortalTimeEntry(user_sub=sub, worked_on=date(2026, 5, idx), minutes=10 * idx),
        )
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    prev_db = app.dependency_overrides.get(get_db_session)
    prev_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(
                f"{TIME_ENTRIES_API}/specialists",
                params={"month": "2026-05", "limit": 2, "offset": 1},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["total"] == 3
            assert len(body["items"]) == 2
            assert body["limit"] == 2
            assert body["skip"] == 1
    finally:
        if prev_db is not None:
            app.dependency_overrides[get_db_session] = prev_db
        else:
            app.dependency_overrides.pop(get_db_session, None)
        if prev_user is not None:
            app.dependency_overrides[get_current_user] = prev_user
        else:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_au_chief_manager_can_access_specialists_endpoint(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    sqlite_session.add(PortalTimeEntry(user_sub="dev-sub", worked_on=date(2026, 5, 3), minutes=60))
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    prev_db = app.dependency_overrides.get(get_db_session)
    prev_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_manager_students_outstaff
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(f"{TIME_ENTRIES_API}/specialists", params={"month": "2026-05"})
            assert r.status_code == 200, r.text
            assert r.json()["total"] >= 1
    finally:
        if prev_db is not None:
            app.dependency_overrides[get_db_session] = prev_db
        else:
            app.dependency_overrides.pop(get_db_session, None)
        if prev_user is not None:
            app.dependency_overrides[get_current_user] = prev_user
        else:
            app.dependency_overrides.pop(get_current_user, None)
