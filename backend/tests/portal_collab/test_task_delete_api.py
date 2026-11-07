"""Удаление задачи через DELETE /portal/tasks/{id}: RBAC и каскад parent_task_id."""

from __future__ import annotations

import uuid

import pytest
from app.core.config import Settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_portal_admin,
    user_portal_no_idp_groups,
    user_portal_regular,
    user_portal_user_b,
)
from tests.portal_collab.conftest import assert_api_error, async_client_as


@pytest.mark.asyncio
async def test_delete_task_204_then_get_404(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async with async_client_as(sqlite_session, user_portal_admin) as ac:
        r = await ac.post("/api/v1/portal/tasks", json={"title": "На удаление", "assignee_sub": "admin-sub"})
        assert r.status_code == 201, r.text
        tid = r.json()["id"]
        r = await ac.delete(f"/api/v1/portal/tasks/{tid}")
        assert r.status_code == 204, r.text
        r = await ac.get(f"/api/v1/portal/tasks/{tid}")
        assert_api_error(r, 404, "not_found")


@pytest.mark.asyncio
async def test_delete_task_204_by_manager_creator(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Менеджер удаляет обычную задачу, которую создал сам."""
    async with async_client_as(sqlite_session, user_portal_regular) as ac:
        r = await ac.post("/api/v1/portal/tasks", json={"title": "Своя менеджера", "assignee_sub": "user-sub"})
        assert r.status_code == 201, r.text
        tid = r.json()["id"]
        r = await ac.delete(f"/api/v1/portal/tasks/{tid}")
        assert r.status_code == 204, r.text
        r = await ac.get(f"/api/v1/portal/tasks/{tid}")
        assert_api_error(r, 404, "not_found")


@pytest.mark.asyncio
async def test_delete_task_403_non_manager_own_regular(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Не-менеджер не может удалить свою обычную задачу."""
    async with async_client_as(sqlite_session, user_portal_no_idp_groups) as ac:
        r = await ac.post(
            "/api/v1/portal/tasks",
            json={"title": "Своя без менеджера", "assignee_sub": "user-no-idp"},
        )
        assert r.status_code == 201, r.text
        tid = r.json()["id"]
        r = await ac.delete(f"/api/v1/portal/tasks/{tid}")
        assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_delete_task_403_foreign(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async with async_client_as(sqlite_session, user_portal_regular) as ac:
        r = await ac.post("/api/v1/portal/tasks", json={"title": "Чужая для B", "assignee_sub": "user-sub"})
        assert r.status_code == 201, r.text
        tid = r.json()["id"]

    async with async_client_as(sqlite_session, user_portal_user_b) as ac:
        r = await ac.delete(f"/api/v1/portal/tasks/{tid}")
        assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_delete_tour_demo_task_204_by_creator(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Автор может удалить учебную задачу онбординга (is_tour_demo)."""
    async with async_client_as(sqlite_session, user_portal_regular) as ac:
        r = await ac.post(
            "/api/v1/portal/tasks",
            json={
                "title": "Учебная задача",
                "assignee_sub": "user-sub",
                "is_tour_demo": True,
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["is_tour_demo"] is True
        tid = body["id"]
        r = await ac.delete(f"/api/v1/portal/tasks/{tid}")
        assert r.status_code == 204, r.text
        r = await ac.get(f"/api/v1/portal/tasks/{tid}")
        assert_api_error(r, 404, "not_found")


@pytest.mark.asyncio
async def test_delete_task_403_after_rename_to_tour_title(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Переименование в «Учебная задача» не даёт право на удаление без is_tour_demo."""
    async with async_client_as(sqlite_session, user_portal_no_idp_groups) as ac:
        r = await ac.post(
            "/api/v1/portal/tasks",
            json={"title": "Обычная", "assignee_sub": "user-no-idp"},
        )
        assert r.status_code == 201, r.text
        tid = r.json()["id"]
        r = await ac.patch(
            f"/api/v1/portal/tasks/{tid}",
            json={"expected_version": 1, "title": "Учебная задача"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["is_tour_demo"] is False
        r = await ac.delete(f"/api/v1/portal/tasks/{tid}")
        assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_delete_task_404_unknown_id(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async with async_client_as(sqlite_session, user_portal_admin) as ac:
        r = await ac.delete(f"/api/v1/portal/tasks/{uuid.uuid4()}")
        assert_api_error(r, 404, "not_found")


@pytest.mark.asyncio
async def test_delete_parent_task_cascades_subtasks(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """После удаления родителя подзадачи тоже удаляются (каскадное удаление)."""
    from app.infrastructure.db.models.portal_task import PortalTask

    async with async_client_as(sqlite_session, user_portal_admin) as ac:
        r = await ac.post(
            "/api/v1/portal/tasks",
            json={"title": "Родитель на удаление", "assignee_sub": "admin-sub"},
        )
        assert r.status_code == 201, r.text
        parent_id = r.json()["id"]
        r = await ac.post(
            "/api/v1/portal/tasks",
            json={"title": "Подзадача", "parent_task_id": parent_id},
        )
        assert r.status_code == 201, r.text
        child_id = r.json()["id"]
        r = await ac.delete(f"/api/v1/portal/tasks/{parent_id}")
        assert r.status_code == 204, r.text
        r = await ac.get(f"/api/v1/portal/tasks/{child_id}")
        assert_api_error(r, 404, "not_found")
        q = select(PortalTask).where(PortalTask.id == uuid.UUID(child_id))
        row = (await sqlite_session.execute(q)).scalar_one_or_none()
        assert row is None
