"""RBAC / IDOR / 401 collab: матрица auth, timesheet, задачи, договорённости, Jira."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import Settings
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_portal_admin,
    user_portal_no_idp_groups,
    user_portal_regular,
)
from tests.portal_collab.conftest import COLLAB_API, as_user, assert_api_error, async_client_as

_AUTH_UUID = "00000000-0000-0000-0000-000000000001"
_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


def _file_kw() -> dict[str, object]:
    return {"files": {"file": ("a.jpg", _JPEG, "image/jpeg")}}


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", f"{COLLAB_API}/tasks", {}),
        ("POST", f"{COLLAB_API}/tasks", {"json": {"title": "X", "assignee_sub": "user-sub"}}),
        ("POST", f"{COLLAB_API}/tasks/reorder", {"json": {"task_id": _AUTH_UUID, "status": "todo"}}),
        ("GET", f"{COLLAB_API}/tasks/by-number/1", {}),
        ("GET", f"{COLLAB_API}/tasks/{_AUTH_UUID}", {}),
        ("PATCH", f"{COLLAB_API}/tasks/{_AUTH_UUID}", {"json": {"expected_version": 1, "title": "X"}}),
        ("DELETE", f"{COLLAB_API}/tasks/{_AUTH_UUID}", {}),
        ("GET", f"{COLLAB_API}/tasks/{_AUTH_UUID}/history", {}),
        ("POST", f"{COLLAB_API}/tasks/{_AUTH_UUID}/rich-media", _file_kw()),
        ("POST", f"{COLLAB_API}/tasks/jira/backfill", {}),
        ("GET", f"{COLLAB_API}/task-columns", {}),
        ("POST", f"{COLLAB_API}/task-columns", {"json": {"title": "X", "color": "#000", "status_key": "x"}}),
        ("POST", f"{COLLAB_API}/task-columns/jira/sync-mapping", {}),
        ("GET", f"{COLLAB_API}/task-columns/{_AUTH_UUID}/export", {}),
        ("PATCH", f"{COLLAB_API}/task-columns/{_AUTH_UUID}", {"json": {"title": "Y"}}),
        ("DELETE", f"{COLLAB_API}/task-columns/{_AUTH_UUID}", {}),
        ("GET", f"{COLLAB_API}/me/task-board-pref", {}),
        (
            "PUT",
            f"{COLLAB_API}/me/task-board-pref",
            {"json": {"column_order": [], "hidden_status_keys": [], "title_overrides": {}}},
        ),
        ("GET", f"{COLLAB_API}/tasks/{_AUTH_UUID}/comments", {}),
        ("POST", f"{COLLAB_API}/tasks/{_AUTH_UUID}/comments", {"json": {"body": "hi", "mentions": []}}),
        (
            "PATCH",
            f"{COLLAB_API}/tasks/{_AUTH_UUID}/comments/{_AUTH_UUID}",
            {"json": {"expected_version": 1, "body": "x"}},
        ),
        ("DELETE", f"{COLLAB_API}/tasks/{_AUTH_UUID}/comments/{_AUTH_UUID}", {}),
        ("POST", f"{COLLAB_API}/tasks/{_AUTH_UUID}/comments/rich-media", _file_kw()),
        ("POST", f"{COLLAB_API}/tasks/{_AUTH_UUID}/comments/ws-ticket", {}),
        ("GET", f"{COLLAB_API}/tasks/{_AUTH_UUID}/links", {}),
        ("POST", f"{COLLAB_API}/tasks/{_AUTH_UUID}/links", {"json": {"url": "https://example.com"}}),
        ("DELETE", f"{COLLAB_API}/tasks/{_AUTH_UUID}/links/{_AUTH_UUID}", {}),
        ("GET", f"{COLLAB_API}/tasks/{_AUTH_UUID}/files", {}),
        ("POST", f"{COLLAB_API}/tasks/{_AUTH_UUID}/files", {"files": {"file": ("n.txt", b"plain text", "text/plain")}}),
        ("DELETE", f"{COLLAB_API}/tasks/{_AUTH_UUID}/files/{_AUTH_UUID}", {}),
        ("GET", f"{COLLAB_API}/agreements", {}),
        ("POST", f"{COLLAB_API}/agreements", {"json": {"body": "текст"}}),
        ("GET", f"{COLLAB_API}/agreements/{_AUTH_UUID}", {}),
        ("PATCH", f"{COLLAB_API}/agreements/{_AUTH_UUID}", {"json": {"body": "x"}}),
        ("GET", f"{COLLAB_API}/notifications", {}),
        ("GET", f"{COLLAB_API}/notifications/unread-count", {}),
        ("POST", f"{COLLAB_API}/notifications/{_AUTH_UUID}/read", {}),
        ("POST", f"{COLLAB_API}/notifications/mark-all-read", {}),
        ("DELETE", f"{COLLAB_API}/notifications", {}),
        ("DELETE", f"{COLLAB_API}/notifications/{_AUTH_UUID}", {}),
        ("POST", f"{COLLAB_API}/tasks/board/ws-ticket", {}),
        ("GET", f"{COLLAB_API}/rich-media/{_AUTH_UUID}", {}),
    ],
)
async def test_collab_endpoints_require_auth(
    client_sqlite_only: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_sqlite_only.request(method, path, **kwargs)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", f"{COLLAB_API}/tasks", {}),
        ("POST", f"{COLLAB_API}/tasks", {"json": {"title": "X", "assignee_sub": "dev-sub"}}),
        ("GET", f"{COLLAB_API}/agreements", {}),
        ("POST", f"{COLLAB_API}/agreements", {"json": {"body": "текст"}}),
        ("GET", f"{COLLAB_API}/task-columns", {}),
        ("GET", f"{COLLAB_API}/me/task-board-pref", {}),
        ("GET", f"{COLLAB_API}/notifications", {}),
        ("POST", f"{COLLAB_API}/tasks/board/ws-ticket", {}),
        ("POST", f"{COLLAB_API}/tasks/{_AUTH_UUID}/comments", {"json": {"body": "x", "mentions": []}}),
        ("GET", f"{COLLAB_API}/tasks/{_AUTH_UUID}/files", {}),
        ("GET", f"{COLLAB_API}/tasks/{_AUTH_UUID}/links", {}),
        ("POST", f"{COLLAB_API}/tasks/jira/backfill", {}),
        ("POST", f"{COLLAB_API}/task-columns/jira/sync-mapping", {}),
    ],
)
async def test_timesheet_only_forbidden_on_collab_routes(
    client_developer: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_developer.request(method, path, **kwargs)
    assert_api_error(r, 403, "forbidden")


async def test_rich_media_get_unknown_404_for_developer(client_developer: AsyncClient) -> None:
    """GET /rich-media не под NON_DEVELOPER: отказ — object RBAC / 404, не гейт роутера."""
    r = await client_developer.get(f"{COLLAB_API}/rich-media/{_AUTH_UUID}")
    assert_api_error(r, 404, "not_found")


async def _create_task(client: AsyncClient, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"title": extra.pop("title", "RBAC задача"), **extra}
    if "assignee_sub" not in payload and "assignee_subs" not in payload:
        payload["assignee_sub"] = "admin-sub"
    r = await client.post(f"{COLLAB_API}/tasks", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def test_get_task_and_by_number_idor(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    from app.infrastructure.db.models.portal_task import PortalTask

    task = await _create_task(client_admin, title="Секрет", assignee_sub="admin-sub")
    tid = task["id"]
    number = task["number"]
    if number is None:
        row = await sqlite_session.get(PortalTask, uuid.UUID(str(tid)))
        assert row is not None
        row.number = 4242
        await sqlite_session.commit()
        number = 4242

    with as_user(user_portal_regular):
        r = await client_admin.get(f"{COLLAB_API}/tasks/{tid}")
        assert r.status_code == 200, r.text
        r = await client_admin.get(f"{COLLAB_API}/tasks/by-number/{number}")
        assert r.status_code == 200, r.text

    with as_user(user_portal_no_idp_groups):
        r = await client_admin.get(f"{COLLAB_API}/tasks/{tid}")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.get(f"{COLLAB_API}/tasks/by-number/{number}")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.get(f"{COLLAB_API}/tasks/{tid}/history")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.get(f"{COLLAB_API}/tasks/{tid}/comments")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.get(f"{COLLAB_API}/tasks/{tid}/files")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.get(f"{COLLAB_API}/tasks/{tid}/links")
        assert_api_error(r, 403, "forbidden")

    r = await client_admin.get(f"{COLLAB_API}/tasks/{_AUTH_UUID}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{COLLAB_API}/tasks/by-number/999999")
    assert_api_error(r, 404, "not_found")


async def test_manager_can_view_but_not_edit_foreign_task(client_admin: AsyncClient) -> None:
    task = await _create_task(client_admin, title="Чужая для менеджера", assignee_sub="admin-sub")
    tid = task["id"]

    with as_user(user_portal_regular):
        r = await client_admin.get(f"{COLLAB_API}/tasks/{tid}")
        assert r.status_code == 200, r.text
        r = await client_admin.patch(f"{COLLAB_API}/tasks/{tid}", json={"expected_version": 1, "title": "взлом"})
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.post(
            f"{COLLAB_API}/tasks/reorder",
            json={"task_id": tid, "status": "todo"},
        )
        assert_api_error(r, 403, "forbidden")
        with (
            patch("app.services.rich_media_upload.async_upload_stream_to_key", new_callable=AsyncMock),
            patch("app.services.rich_media.get_presigned_url", return_value="https://minio.local/img"),
        ):
            r = await client_admin.post(
                f"{COLLAB_API}/tasks/{tid}/rich-media",
                files={"file": ("pic.jpg", _JPEG, "image/jpeg")},
            )
        assert_api_error(r, 403, "forbidden")


async def test_assignee_cannot_change_assignees(client_admin: AsyncClient) -> None:
    task = await _create_task(client_admin, title="Исполнитель не меняет состав", assignee_sub="user-sub")
    tid = task["id"]
    with as_user(user_portal_regular):
        r = await client_admin.patch(
            f"{COLLAB_API}/tasks/{tid}",
            json={"expected_version": 1, "assignee_subs": ["user-sub", "user-b"]},
        )
        assert_api_error(r, 403, "forbidden")


async def test_comment_link_file_cross_task_idor(client_admin: AsyncClient) -> None:
    a = await _create_task(client_admin, title="Задача A")
    b = await _create_task(client_admin, title="Задача B")
    r = await client_admin.post(
        f"{COLLAB_API}/tasks/{b['id']}/comments",
        json={"body": "чужой коммент", "mentions": []},
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    r = await client_admin.patch(
        f"{COLLAB_API}/tasks/{a['id']}/comments/{cid}",
        json={"expected_version": 1, "body": "подмена"},
    )
    assert_api_error(r, 404, "not_found")

    r = await client_admin.post(
        f"{COLLAB_API}/tasks/{b['id']}/links",
        json={"url": "https://example.com/b"},
    )
    assert r.status_code == 201, r.text
    lid = r.json()["id"]
    r = await client_admin.delete(f"{COLLAB_API}/tasks/{a['id']}/links/{lid}")
    assert_api_error(r, 404, "not_found")

    with (
        patch("app.portal_collab.services.task_file.async_upload_file", new_callable=AsyncMock, return_value="sk-idor"),
        patch("app.portal_collab.services.task_file.get_presigned_url", return_value="https://minio.local/x"),
    ):
        r = await client_admin.post(
            f"{COLLAB_API}/tasks/{b['id']}/files",
            files={"file": ("notes.txt", b"plain text", "text/plain")},
        )
    assert r.status_code == 201, r.text
    fid = r.json()["id"]
    r = await client_admin.delete(f"{COLLAB_API}/tasks/{a['id']}/files/{fid}")
    assert_api_error(r, 404, "not_found")


async def test_comment_patch_delete_author_only(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async with async_client_as(sqlite_session, user_portal_admin) as ac:
        task = await _create_task(ac, title="Коммент автора", assignee_sub="user-sub")
        r = await ac.post(
            f"{COLLAB_API}/tasks/{task['id']}/comments",
            json={"body": "моё", "mentions": []},
        )
        assert r.status_code == 201, r.text
        cid = r.json()["id"]

    async with async_client_as(sqlite_session, user_portal_regular) as ac:
        r = await ac.patch(
            f"{COLLAB_API}/tasks/{task['id']}/comments/{cid}",
            json={"expected_version": 1, "body": "чужое"},
        )
        assert_api_error(r, 403, "forbidden")
        r = await ac.delete(f"{COLLAB_API}/tasks/{task['id']}/comments/{cid}")
        assert_api_error(r, 403, "forbidden")


async def test_agreements_http_rbac(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async with async_client_as(sqlite_session, user_portal_admin) as ac:
        r = await ac.post(f"{COLLAB_API}/agreements", json={"body": "Только админ"})
        assert r.status_code == 201, r.text
        hidden_id = r.json()["id"]
        task = await _create_task(ac, title="Для агримента")
        tid = task["id"]
        r = await ac.post(f"{COLLAB_API}/agreements", json={"body": "Через задачу", "task_id": tid})
        assert r.status_code == 201, r.text
        visible_id = r.json()["id"]

    async with async_client_as(sqlite_session, user_portal_no_idp_groups) as ac:
        r = await ac.get(f"{COLLAB_API}/agreements/{hidden_id}")
        assert_api_error(r, 403, "forbidden")
        r = await ac.patch(f"{COLLAB_API}/agreements/{hidden_id}", json={"body": "взлом"})
        assert_api_error(r, 403, "forbidden")
        r = await ac.post(f"{COLLAB_API}/agreements", json={"body": "к задаче", "task_id": tid})
        assert_api_error(r, 403, "forbidden")

    async with async_client_as(sqlite_session, user_portal_regular) as ac:
        r = await ac.get(f"{COLLAB_API}/agreements/{visible_id}")
        assert r.status_code == 200, r.text
        r = await ac.patch(f"{COLLAB_API}/agreements/{visible_id}", json={"body": "не создатель"})
        assert_api_error(r, 403, "forbidden")


async def test_rich_media_get_forbidden_for_foreign_task(client_admin: AsyncClient) -> None:
    task = await _create_task(client_admin, title="Медиа")
    with (
        patch("app.services.rich_media_upload.async_upload_stream_to_key", new_callable=AsyncMock),
        patch("app.services.rich_media.get_presigned_url", return_value="https://minio.local/img"),
    ):
        r = await client_admin.post(
            f"{COLLAB_API}/tasks/{task['id']}/rich-media",
            files={"file": ("pic.jpg", _JPEG, "image/jpeg")},
        )
        assert r.status_code == 201, r.text
        media_id = r.json()["id"]
        r = await client_admin.post(
            f"{COLLAB_API}/tasks/{task['id']}/comments/rich-media",
            files={"file": ("c.jpg", _JPEG, "image/jpeg")},
        )
        assert r.status_code == 201, r.text

    with as_user(user_portal_no_idp_groups):
        r = await client_admin.get(f"{COLLAB_API}/rich-media/{media_id}")
        assert_api_error(r, 403, "forbidden")


async def test_jira_admin_gates(client_admin: AsyncClient) -> None:
    with as_user(user_portal_regular):
        r = await client_admin.post(f"{COLLAB_API}/tasks/jira/backfill")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.post(f"{COLLAB_API}/task-columns/jira/sync-mapping")
        assert_api_error(r, 403, "forbidden")

    disabled = Settings(jira_tasks_sync_enabled=False, jira_base_url="", jira_personal_access_token="")
    with patch("app.portal_collab.routes.tasks.get_settings", return_value=disabled):
        r = await client_admin.post(f"{COLLAB_API}/tasks/jira/backfill")
        assert_api_error(r, 503, "service_unavailable")

    with patch(
        "app.portal_collab.services.task_jira_column_sync.get_settings",
        return_value=Settings(jira_base_url="", jira_personal_access_token=""),
    ):
        r = await client_admin.post(f"{COLLAB_API}/task-columns/jira/sync-mapping")
        assert_api_error(r, 503, "service_unavailable")
