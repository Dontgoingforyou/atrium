"""Интеграционные тесты: колонки канбана, ссылки задачи, PATCH/DELETE комментариев, список задач с query."""

from __future__ import annotations

import uuid

import pytest
from app.schemas.auth import UserPublic
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_portal_admin,
    user_portal_manager,
    user_portal_no_idp_groups,
    user_portal_regular,
    user_portal_user_b,
)
from tests.portal_collab.conftest import assert_api_error, async_client_as


@pytest.mark.asyncio
async def test_task_columns_crud(client_admin: AsyncClient) -> None:
    status_key = f"col_{uuid.uuid4().hex[:8]}"
    r = await client_admin.post(
        "/api/v1/portal/task-columns",
        json={
            "title": "Тестовая колонка",
            "color": "#abcdef",
            "status_key": status_key,
            "position": 99,
        },
    )
    assert r.status_code == 201, r.text
    col = r.json()
    assert col["title"] == "Тестовая колонка"
    assert col["status_key"] == status_key
    cid = col["id"]

    r = await client_admin.get("/api/v1/portal/task-columns")
    assert r.status_code == 200
    assert any(c["id"] == cid for c in r.json())

    r = await client_admin.patch(
        f"/api/v1/portal/task-columns/{cid}",
        json={"title": "Переименована", "color": "#111111", "position": 1},
    )
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "Переименована"
    assert r.json()["color"] == "#111111"

    r = await client_admin.delete(f"/api/v1/portal/task-columns/{cid}")
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_task_column_create_forbidden_without_manager_scope(
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    async with async_client_as(sqlite_session, user_portal_no_idp_groups) as ac:
        r = await ac.post(
            "/api/v1/portal/task-columns",
            json={
                "title": "X",
                "color": "#fff",
                "status_key": f"x_{uuid.uuid4().hex[:6]}",
                "position": 0,
            },
        )
        assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_task_links_crud(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Задача со ссылками", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    r = await client_admin.get(f"/api/v1/portal/tasks/{tid}/links")
    assert r.status_code == 200
    assert r.json() == []

    r = await client_admin.post(
        f"/api/v1/portal/tasks/{tid}/links",
        json={"title": "Документация", "url": "https://example.com/docs"},
    )
    assert r.status_code == 201, r.text
    link = r.json()
    assert link["title"] == "Документация"
    assert link["url"] == "https://example.com/docs"
    lid = link["id"]

    r = await client_admin.get(f"/api/v1/portal/tasks/{tid}/links")
    assert r.status_code == 200
    links = r.json()
    assert len(links) == 1
    assert links[0]["id"] == lid

    r = await client_admin.delete(f"/api/v1/portal/tasks/{tid}/links/{lid}")
    assert r.status_code == 204

    r = await client_admin.get(f"/api/v1/portal/tasks/{tid}/links")
    assert r.json() == []


@pytest.mark.asyncio
async def test_task_link_create_without_title(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Задача со ссылкой без названия", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    r = await client_admin.post(
        f"/api/v1/portal/tasks/{tid}/links",
        json={"url": "https://example.com/no-title"},
    )
    assert r.status_code == 201, r.text
    link = r.json()
    assert link["title"] is None
    assert link["url"] == "https://example.com/no-title"


@pytest.mark.asyncio
async def test_task_link_delete_forbidden_for_non_author(
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    async with async_client_as(sqlite_session, user_portal_admin) as ac:
        r = await ac.post(
            "/api/v1/portal/tasks",
            json={"title": "Чужая ссылка", "assignee_sub": user_portal_regular().sub},
        )
        assert r.status_code == 201, r.text
        tid = r.json()["id"]
        r = await ac.post(
            f"/api/v1/portal/tasks/{tid}/links",
            json={"title": "L", "url": "https://example.com/x"},
        )
        assert r.status_code == 201, r.text
        lid = r.json()["id"]

    async with async_client_as(sqlite_session, user_portal_regular) as ac:
        r = await ac.delete(f"/api/v1/portal/tasks/{tid}/links/{lid}")
        assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_task_link_delete_unknown_404(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Нет ссылки", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    r = await client_admin.delete(f"/api/v1/portal/tasks/{tid}/links/{uuid.uuid4()}")
    assert_api_error(r, 404, "not_found")


@pytest.mark.asyncio
async def test_task_comment_patch_and_delete(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Задача с комментом", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    r = await client_admin.post(
        f"/api/v1/portal/tasks/{tid}/comments",
        json={"body": "Исходный текст", "mentions": []},
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    r = await client_admin.patch(
        f"/api/v1/portal/tasks/{tid}/comments/{cid}",
        json={"expected_version": 1, "body": "Обновлённый текст"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["body"] == "Обновлённый текст"

    r = await client_admin.delete(f"/api/v1/portal/tasks/{tid}/comments/{cid}")
    assert r.status_code == 204

    r = await client_admin.get(f"/api/v1/portal/tasks/{tid}/comments")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_task_comment_reply_to_reply_stays_in_thread(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Тред", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    r = await client_admin.post(
        f"/api/v1/portal/tasks/{tid}/comments",
        json={"body": "Корень", "mentions": []},
    )
    assert r.status_code == 201, r.text
    root_id = r.json()["id"]

    r = await client_admin.post(
        f"/api/v1/portal/tasks/{tid}/comments",
        json={"body": "Ответ", "mentions": [], "parent_id": root_id},
    )
    assert r.status_code == 201, r.text
    reply_id = r.json()["id"]

    r = await client_admin.post(
        f"/api/v1/portal/tasks/{tid}/comments",
        json={"body": "Ответ на ответ", "mentions": [], "parent_id": reply_id},
    )
    assert r.status_code == 201, r.text

    listed = (await client_admin.get(f"/api/v1/portal/tasks/{tid}/comments")).json()
    assert [item["body"] for item in listed] == ["Корень"]
    assert listed[0]["replies"][0]["id"] == reply_id
    assert listed[0]["replies"][0]["replies"][0]["body"] == "Ответ на ответ"
    assert listed[0]["replies"][0]["replies"][0]["parent_id"] == reply_id


@pytest.mark.asyncio
async def test_list_tasks_mine_only_and_parent_filter(client_admin: AsyncClient) -> None:
    r = await client_admin.post("/api/v1/portal/tasks", json={"title": "Родитель", "assignee_sub": "admin-sub"})
    assert r.status_code == 201, r.text
    parent_id = r.json()["id"]

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Подзадача", "parent_task_id": parent_id},
    )
    assert r.status_code == 201, r.text
    child = r.json()
    child_id = child["id"]
    assert child["assignee_subs"] == ["admin-sub"]
    assert child["assignee_sub"] == "admin-sub"

    r = await client_admin.get(f"/api/v1/portal/tasks?parent_task_id={parent_id}")
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()}
    assert child_id in ids
    assert parent_id not in ids

    r = await client_admin.get("/api/v1/portal/tasks?mine_only=true")
    assert r.status_code == 200
    mine_ids = {t["id"] for t in r.json()}
    assert parent_id in mine_ids
    # Исполнитель родителя скопирован на подзадачу — она тоже в «моих»
    assert child_id in mine_ids


@pytest.mark.asyncio
async def test_list_tasks_board_isolates_foreign_subtasks(
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    author = user_portal_regular()
    other = user_portal_user_b()

    async with async_client_as(sqlite_session, user_portal_regular) as ac:
        r = await ac.post(
            "/api/v1/portal/tasks",
            json={"title": "Общий родитель", "assignee_subs": [author.sub, other.sub]},
        )
        assert r.status_code == 201, r.text
        parent = r.json()
        parent_id = parent["id"]
        assert set(parent["assignee_subs"]) == {author.sub, other.sub}

        r = await ac.post(
            "/api/v1/portal/tasks",
            json={
                "title": "Чужая подзадача",
                "parent_task_id": parent_id,
                "assignee_subs": [author.sub],
            },
        )
        assert r.status_code == 201, r.text
        child_only = r.json()
        child_only_id = child_only["id"]
        assert child_only["assignee_subs"] == [author.sub]

        r = await ac.post(
            "/api/v1/portal/tasks",
            json={
                "title": "Общая подзадача",
                "parent_task_id": parent_id,
                "assignee_subs": [author.sub, other.sub],
            },
        )
        assert r.status_code == 201, r.text
        child_both_id = r.json()["id"]

        r = await ac.post(
            "/api/v1/portal/tasks",
            json={
                "title": "Подзадача без исполнителей",
                "parent_task_id": parent_id,
                "assignee_subs": [],
            },
        )
        assert r.status_code == 201, r.text
        child_plain = r.json()
        child_plain_id = child_plain["id"]
        assert child_plain["assignee_subs"] == []
        assert child_plain["assignee_sub"] is None

        r = await ac.get("/api/v1/portal/tasks")
        assert r.status_code == 200
        author_ids = {t["id"] for t in r.json()}
        assert {parent_id, child_only_id, child_both_id, child_plain_id} <= author_ids

    async with async_client_as(sqlite_session, user_portal_user_b) as ac:
        r = await ac.get("/api/v1/portal/tasks")
        assert r.status_code == 200
        other_ids = {t["id"] for t in r.json()}
        assert parent_id in other_ids
        assert child_both_id in other_ids
        assert child_only_id in other_ids
        assert child_plain_id in other_ids

        r = await ac.get("/api/v1/portal/tasks?mine_only=true")
        assert r.status_code == 200
        mine_ids = {t["id"] for t in r.json()}
        assert parent_id in mine_ids
        assert child_both_id in mine_ids
        assert child_only_id not in mine_ids
        assert child_plain_id not in mine_ids

        r = await ac.get(f"/api/v1/portal/tasks?parent_task_id={parent_id}")
        assert r.status_code == 200
        detail_ids = {t["id"] for t in r.json()}
        assert parent_id not in detail_ids
        assert {child_only_id, child_both_id, child_plain_id} <= detail_ids


def _board_employee(sub: str) -> UserPublic:
    return UserPublic(
        sub=sub,
        email=f"{sub}@example.com",
        username=sub,
        full_name=sub,
        idp_groups=[],
        is_portal_admin=False,
    )


@pytest.mark.asyncio
async def test_list_tasks_manager_sees_foreign_board_subtasks(
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    """Сотрудник без роли руководителя не видит чужую подзадачу; руководитель видит."""

    def employee() -> UserPublic:
        return _board_employee("employee-a")

    def colleague() -> UserPublic:
        return _board_employee("employee-b")

    async with async_client_as(sqlite_session, employee) as ac:
        r = await ac.post(
            "/api/v1/portal/tasks",
            json={"title": "Родитель двоих", "assignee_subs": ["employee-a", "employee-b"]},
        )
        assert r.status_code == 201, r.text
        parent_id = r.json()["id"]
        r = await ac.post(
            "/api/v1/portal/tasks",
            json={
                "title": "Подзадача только автора",
                "parent_task_id": parent_id,
                "assignee_subs": ["employee-a"],
            },
        )
        assert r.status_code == 201, r.text
        child_id = r.json()["id"]

    async with async_client_as(sqlite_session, colleague) as ac:
        r = await ac.get("/api/v1/portal/tasks")
        assert r.status_code == 200
        colleague_ids = {t["id"] for t in r.json()}
        assert parent_id in colleague_ids
        assert child_id not in colleague_ids

    async with async_client_as(sqlite_session, user_portal_manager) as ac:
        r = await ac.get("/api/v1/portal/tasks", params={"assignee_sub": "employee-a"})
        assert r.status_code == 200, r.text
        manager_ids = {t["id"] for t in r.json()}
        assert parent_id in manager_ids
        assert child_id in manager_ids


@pytest.mark.asyncio
async def test_create_subtask_inherits_parent_assignees_when_omitted(
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    """Пропуск исполнителей копирует всех с родителя; явный список не раздувается."""
    author = user_portal_regular()
    other = user_portal_user_b()

    async with async_client_as(sqlite_session, user_portal_regular) as ac:
        r = await ac.post(
            "/api/v1/portal/tasks",
            json={"title": "Родитель с двумя", "assignee_subs": [author.sub, other.sub]},
        )
        assert r.status_code == 201, r.text
        parent_id = r.json()["id"]

        r = await ac.post(
            "/api/v1/portal/tasks",
            json={"title": "Наследник", "parent_task_id": parent_id},
        )
        assert r.status_code == 201, r.text
        inherited = r.json()
        assert set(inherited["assignee_subs"]) == {author.sub, other.sub}
        assert inherited["assignee_sub"] in {author.sub, other.sub}

        r = await ac.post(
            "/api/v1/portal/tasks",
            json={
                "title": "Только один",
                "parent_task_id": parent_id,
                "assignee_subs": [author.sub],
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["assignee_subs"] == [author.sub]


@pytest.mark.asyncio
async def test_list_tasks_overdue_only_filters(client_admin: AsyncClient) -> None:
    from datetime import UTC, datetime, time, timedelta

    from app.portal_collab.services._task_due_calendar import today_portal

    now = datetime.now(UTC)
    past = datetime.combine(today_portal(now) - timedelta(days=2), time.min, tzinfo=UTC).isoformat()
    today_due = datetime.combine(today_portal(now), time.min, tzinfo=UTC).isoformat()
    future = (now + timedelta(days=5)).isoformat()

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Просроченная", "assignee_sub": "admin-sub", "due_at": past},
    )
    assert r.status_code == 201, r.text
    overdue_id = r.json()["id"]

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Срок сегодня", "assignee_sub": "admin-sub", "due_at": today_due},
    )
    assert r.status_code == 201, r.text
    today_id = r.json()["id"]

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "В срок", "assignee_sub": "admin-sub", "due_at": future},
    )
    assert r.status_code == 201, r.text
    on_time_id = r.json()["id"]

    r = await client_admin.get("/api/v1/portal/tasks?mine_only=true&overdue_only=true")
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()}
    assert overdue_id in ids
    assert today_id not in ids
    assert on_time_id not in ids


@pytest.mark.asyncio
async def test_list_tasks_done_this_month_filters(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Закрыть в этом месяце", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    done_id = r.json()["id"]
    r = await client_admin.patch(
        f"/api/v1/portal/tasks/{done_id}",
        json={"expected_version": 1, "status": "done"},
    )
    assert r.status_code == 200, r.text

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Ещё открыта", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    open_id = r.json()["id"]

    r = await client_admin.get("/api/v1/portal/tasks?done_this_month=true")
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()}
    assert done_id in ids
    assert open_id not in ids


@pytest.mark.asyncio
async def test_list_tasks_status_done_is_ready_not_approval(client_admin: AsyncClient) -> None:
    """Чип «Завершена» — только «Готово»; месяц — Готово и На согласовании."""
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "На согласовании HTTP", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    approval_id = r.json()["id"]
    approval_ver = r.json()["version"]

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Готово HTTP", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    ready_id = r.json()["id"]
    ready_ver = r.json()["version"]

    approval_key = f"col_{uuid.uuid4().hex[:8]}"
    ready_key = f"col_{uuid.uuid4().hex[:8]}"
    r = await client_admin.post(
        "/api/v1/portal/task-columns",
        json={
            "title": "На согласовании",
            "color": "#3b82f6",
            "status_key": approval_key,
            "position": 80,
            "exclude_from_kpi": True,
        },
    )
    assert r.status_code == 201, r.text
    r = await client_admin.post(
        "/api/v1/portal/task-columns",
        json={
            "title": "Готово",
            "color": "#1a9000",
            "status_key": ready_key,
            "position": 81,
            "exclude_from_kpi": False,
        },
    )
    assert r.status_code == 201, r.text

    r = await client_admin.patch(
        f"/api/v1/portal/tasks/{approval_id}",
        json={"expected_version": approval_ver, "status": approval_key},
    )
    assert r.status_code == 200, r.text
    r = await client_admin.patch(
        f"/api/v1/portal/tasks/{ready_id}",
        json={"expected_version": ready_ver, "status": ready_key},
    )
    assert r.status_code == 200, r.text

    r = await client_admin.get("/api/v1/portal/tasks?status=done")
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()}
    assert ready_id in ids
    assert approval_id not in ids

    r = await client_admin.get("/api/v1/portal/tasks?done_this_month=true")
    assert r.status_code == 200
    month_ids = {t["id"] for t in r.json()}
    assert ready_id in month_ids
    assert approval_id in month_ids


@pytest.mark.asyncio
async def test_list_tasks_no_assignee_filters(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Без исполнителя для фильтра", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    unassigned_id = r.json()["id"]
    r = await client_admin.patch(
        f"/api/v1/portal/tasks/{unassigned_id}",
        json={"expected_version": 1, "assignee_subs": []},
    )
    assert r.status_code == 200, r.text

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "С исполнителем", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    assigned_id = r.json()["id"]

    r = await client_admin.get("/api/v1/portal/tasks?no_assignee=true")
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()}
    assert unassigned_id in ids
    assert assigned_id not in ids


@pytest.mark.asyncio
async def test_list_tasks_kpi_open_only_excludes_kpi_column(client_admin: AsyncClient) -> None:
    status_key = f"col_k{uuid.uuid4().hex[:8]}"
    r = await client_admin.post(
        "/api/v1/portal/task-columns",
        json={
            "title": "Закрыто KPI",
            "color": "#333333",
            "status_key": status_key,
            "position": 90,
            "exclude_from_kpi": True,
        },
    )
    assert r.status_code == 201, r.text

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "KPI открытая", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    open_id = r.json()["id"]

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Вне KPI", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    excluded_id = r.json()["id"]
    r = await client_admin.patch(
        f"/api/v1/portal/tasks/{excluded_id}",
        json={"expected_version": 1, "status": status_key},
    )
    assert r.status_code == 200, r.text

    r = await client_admin.get("/api/v1/portal/tasks?kpi_open_only=true")
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()}
    assert open_id in ids
    assert excluded_id not in ids

    r = await client_admin.get("/api/v1/portal/tasks")
    assert r.status_code == 200
    all_ids = {t["id"] for t in r.json()}
    assert excluded_id in all_ids


@pytest.mark.asyncio
async def test_task_column_delete_409_when_tasks_in_column_status(
    client_admin: AsyncClient,
) -> None:
    """Удаление колонки с status_key, по которому есть задачи — Conflict 409."""
    r = await client_admin.post("/api/v1/portal/tasks", json={"title": "В колонке todo", "assignee_sub": "admin-sub"})
    assert r.status_code == 201, r.text

    r = await client_admin.post(
        "/api/v1/portal/task-columns",
        json={
            "title": "Колонка todo",
            "color": "#000000",
            "status_key": "todo",
            "position": 0,
        },
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    r = await client_admin.delete(f"/api/v1/portal/task-columns/{cid}")
    assert r.status_code == 409
    body = r.json()
    assert body.get("code") == "conflict"
    assert "задач" in body.get("message", "").lower()


@pytest.mark.asyncio
async def test_task_column_export_txt_success(client_admin: AsyncClient) -> None:
    status_key = f"exp_{uuid.uuid4().hex[:8]}"
    r = await client_admin.post(
        "/api/v1/portal/task-columns",
        json={
            "title": "Экспорт-колонка",
            "color": "#123456",
            "status_key": status_key,
            "position": 50,
        },
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": "Родитель для экспорта",
            "assignee_sub": "admin-sub",
            "description": "<p>Описание родителя &amp; детали</p>",
        },
    )
    assert r.status_code == 201, r.text
    parent = r.json()
    parent_id = parent["id"]
    parent_number = parent.get("number")

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": "Задача для экспорта",
            "assignee_sub": "admin-sub",
            "status": status_key,
            "priority": "high",
            "parent_task_id": parent_id,
            "description": "<p>Текст описания<br/>вторая строка</p>",
        },
    )
    assert r.status_code == 201, r.text
    task = r.json()
    number = task.get("number")
    tid = task["id"]

    r = await client_admin.post(
        f"/api/v1/portal/tasks/{tid}/links",
        json={"title": "Документ", "url": "https://example.com/export-doc"},
    )
    assert r.status_code == 201, r.text

    r = await client_admin.post(
        f"/api/v1/portal/tasks/{tid}/comments",
        json={"body": "<p>Комментарий экспорта</p>", "mentions": []},
    )
    assert r.status_code == 201, r.text
    comment_id = r.json()["id"]

    r = await client_admin.post(
        f"/api/v1/portal/tasks/{tid}/comments",
        json={"body": "Ответ на комментарий", "mentions": [], "parent_id": comment_id},
    )
    assert r.status_code == 201, r.text

    r = await client_admin.get(f"/api/v1/portal/task-columns/{cid}/export")
    assert r.status_code == 200, r.text
    assert "text/plain" in (r.headers.get("content-type") or "")
    cd = r.headers.get("content-disposition") or ""
    assert "attachment" in cd
    assert f"tasks_{status_key}_" in cd
    assert cd.endswith('.txt"') or ".txt" in cd

    text = r.content.decode("utf-8-sig")
    assert "Колонка: Экспорт-колонка" in text
    assert "Задача для экспорта" in text
    assert "Приоритет: Высокий" in text
    assert "Исполнители:" in text
    assert "Создатель:" in text
    assert "Текст описания" in text
    assert "вторая строка" in text
    assert "Родительская задача:" in text
    assert "Родитель для экспорта" in text
    assert "Описание родителя & детали" in text
    assert "Комментарий экспорта" in text
    assert "[ответ]" in text
    assert "Ответ на комментарий" in text
    assert "Документ: https://example.com/export-doc" in text
    if number is not None:
        assert f"#{number}" in text
    if parent_number is not None:
        assert f"#{parent_number}" in text


@pytest.mark.asyncio
async def test_task_column_export_not_found(client_admin: AsyncClient) -> None:
    missing = uuid.uuid4()
    r = await client_admin.get(f"/api/v1/portal/task-columns/{missing}/export")
    assert r.status_code == 404
    assert r.json().get("code") == "not_found"


@pytest.mark.asyncio
async def test_task_column_export_hides_foreign_tasks(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    status_key = f"vis_{uuid.uuid4().hex[:8]}"
    r = await client_admin.post(
        "/api/v1/portal/task-columns",
        json={
            "title": "Видимость экспорта",
            "color": "#654321",
            "status_key": status_key,
            "position": 51,
        },
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={
            "title": "Секретная задача админа",
            "assignee_sub": "admin-sub",
            "status": status_key,
        },
    )
    assert r.status_code == 201, r.text

    async with async_client_as(sqlite_session, user_portal_no_idp_groups) as ac:
        r = await ac.get(f"/api/v1/portal/task-columns/{cid}/export")
        assert r.status_code == 200, r.text
        text = r.content.decode("utf-8-sig")
        assert "Колонка: Видимость экспорта" in text
        assert "Секретная задача админа" not in text


@pytest.mark.asyncio
async def test_task_column_export_foreign_assignee_forbidden_for_regular(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    status_key = f"asg_{uuid.uuid4().hex[:8]}"
    r = await client_admin.post(
        "/api/v1/portal/task-columns",
        json={
            "title": "Фильтр исполнителя",
            "color": "#abcdef",
            "status_key": status_key,
            "position": 52,
        },
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    async with async_client_as(sqlite_session, user_portal_no_idp_groups) as ac:
        r = await ac.get(
            f"/api/v1/portal/task-columns/{cid}/export",
            params={"assignee_sub": "admin-sub"},
        )
        assert_api_error(r, 403, "forbidden")
