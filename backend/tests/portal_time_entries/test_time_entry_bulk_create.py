"""
Тесты массового создания записей таймшита: POST /portal/time-entries/bulk.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.models.portal_task import PortalTask
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_developer
from tests.portal_time_entries.conftest import assert_api_error


@pytest.mark.asyncio
async def test_bulk_create_weekdays_default_mon_to_fri(
    client_regular_entries: AsyncClient,
) -> None:
    """По умолчанию (без weekdays) создаются записи на Пн–Пт диапазона."""
    r = await client_regular_entries.post(
        "/api/v1/portal/time-entries/bulk",
        json={
            "date_from": "2026-06-01",  # понедельник
            "date_to": "2026-06-07",  # неделя целиком (вс)
            "minutes": 60,
            "task_name": "Дейлик",
        },
    )
    assert r.status_code == 201, r.text
    rows = r.json()
    assert len(rows) == 5
    dates = sorted(row["worked_on"] for row in rows)
    assert dates == ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"]
    assert all(row["minutes"] == 60 for row in rows)
    assert all(row["task_name"] == "Дейлик" for row in rows)
    assert all(row["user_sub"] == "user-sub" for row in rows)


@pytest.mark.asyncio
async def test_bulk_create_custom_weekdays_only_weekend(
    client_regular_entries: AsyncClient,
) -> None:
    """Явно переданный набор дней недели (например только Сб/Вс) фильтрует диапазон."""
    r = await client_regular_entries.post(
        "/api/v1/portal/time-entries/bulk",
        json={
            "date_from": "2026-06-01",
            "date_to": "2026-06-07",
            "weekdays": [5, 6],
            "minutes": 30,
            "note": "Обслуживание серверов",
        },
    )
    assert r.status_code == 201, r.text
    rows = r.json()
    dates = sorted(row["worked_on"] for row in rows)
    assert dates == ["2026-06-06", "2026-06-07"]


@pytest.mark.asyncio
async def test_bulk_create_date_to_before_date_from_returns_422(
    client_regular_entries: AsyncClient,
) -> None:
    r = await client_regular_entries.post(
        "/api/v1/portal/time-entries/bulk",
        json={"date_from": "2026-06-10", "date_to": "2026-06-01", "minutes": 30},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_bulk_create_empty_weekdays_returns_422(
    client_regular_entries: AsyncClient,
) -> None:
    r = await client_regular_entries.post(
        "/api/v1/portal/time-entries/bulk",
        json={"date_from": "2026-06-01", "date_to": "2026-06-07", "weekdays": [], "minutes": 30},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_bulk_create_invalid_weekday_value_returns_422(
    client_regular_entries: AsyncClient,
) -> None:
    """Значения weekdays вне диапазона 0..6 отклоняются на уровне схемы."""
    r = await client_regular_entries.post(
        "/api/v1/portal/time-entries/bulk",
        json={"date_from": "2026-06-01", "date_to": "2026-06-07", "weekdays": [3, 7], "minutes": 30},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_bulk_create_century_range_returns_422_without_walking_all_days(
    client_regular_entries: AsyncClient,
) -> None:
    """Диапазон на десятилетия не должен крутить цикл до конца, прежде чем вернуть 422."""
    r = await client_regular_entries.post(
        "/api/v1/portal/time-entries/bulk",
        json={
            "date_from": "2000-01-01",
            "date_to": "2100-12-31",
            "weekdays": [0],
            "minutes": 30,
        },
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_bulk_create_too_many_entries_returns_422(
    client_regular_entries: AsyncClient,
) -> None:
    """Диапазон, дающий более 200 записей (весь год по всем дням недели), отклоняется."""
    r = await client_regular_entries.post(
        "/api/v1/portal/time-entries/bulk",
        json={
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
            "weekdays": [0, 1, 2, 3, 4, 5, 6],
            "minutes": 30,
        },
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_bulk_create_forbidden_for_inaccessible_task(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Привязка к чужой недоступной задаче — 403, как и в одиночном create_time_entry.

    Разработчик имеет доступ к таймшитам, но не видит чужую задачу.
    """
    task = PortalTask(
        title="Чужая задача",
        creator_sub="other-sub",
        assignee_sub="other-sub",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )
    sqlite_session.add(task)
    await sqlite_session.commit()
    await sqlite_session.refresh(task)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    prev_db = app.dependency_overrides.get(get_db_session)
    prev_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_developer
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/v1/portal/time-entries/bulk",
                json={
                    "date_from": "2026-06-01",
                    "date_to": "2026-06-05",
                    "minutes": 30,
                    "task_id": str(task.id),
                },
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
async def test_bulk_create_developer_own_sub_only(
    client_developer_entries: AsyncClient,
) -> None:
    """Разработчик создаёт bulk-записи от своего user_sub (эндпоинт не принимает user_sub)."""
    r = await client_developer_entries.post(
        "/api/v1/portal/time-entries/bulk",
        json={"date_from": "2026-06-01", "date_to": "2026-06-03", "minutes": 60, "task_name": "Дейлик"},
    )
    assert r.status_code == 201, r.text
    rows = r.json()
    assert all(row["user_sub"] == "dev-sub" for row in rows)


@pytest.mark.asyncio
async def test_bulk_create_single_day_range(
    client_regular_entries: AsyncClient,
) -> None:
    """date_from == date_to и этот день попадает в weekdays — создаётся ровно одна запись."""
    r = await client_regular_entries.post(
        "/api/v1/portal/time-entries/bulk",
        json={
            "date_from": "2026-06-01",  # понедельник, попадает в дефолтные Пн-Пт
            "date_to": "2026-06-01",
            "minutes": 45,
        },
    )
    assert r.status_code == 201, r.text
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["worked_on"] == "2026-06-01"


@pytest.mark.asyncio
async def test_bulk_create_no_matching_weekday_in_range_returns_422(
    client_regular_entries: AsyncClient,
) -> None:
    """Диапазон, не содержащий ни одного из выбранных дней недели, — ошибка валидации."""
    r = await client_regular_entries.post(
        "/api/v1/portal/time-entries/bulk",
        json={
            "date_from": "2026-06-01",  # пн
            "date_to": "2026-06-01",
            "weekdays": [5, 6],  # сб/вс — не попадает
            "minutes": 30,
        },
    )
    assert r.status_code == 422, r.text
