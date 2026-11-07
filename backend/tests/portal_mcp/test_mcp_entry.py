"""Вход HTTP MCP: нет Bearer, чужая роль, менеджер и админ на одном туле."""

from __future__ import annotations

import asyncio
import base64
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.deps import get_db_session
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_task import PortalTaskColumn
from app.main import app
from app.portal_mcp.server import portal_mcp
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.helpers.portal_test_users import (
    user_outstaff_not_manager,
    user_portal_admin,
    user_portal_developer,
    user_portal_manager,
)

pytestmark = pytest.mark.asyncio

_mcp_started = False


@pytest.fixture(autouse=True)
async def mcp_runtime() -> None:
    """Держать task group MCP на цикле тестов. ``run()`` можно вызвать только один раз."""
    global _mcp_started
    if _mcp_started:
        return
    if portal_mcp._session_manager is None:
        raise RuntimeError("MCP не смонтирован")

    async def _hold() -> None:
        async with portal_mcp.session_manager.run():
            await asyncio.Event().wait()

    asyncio.get_running_loop().create_task(_hold())
    for _ in range(50):
        if portal_mcp.session_manager._task_group is not None:
            _mcp_started = True
            return
        await asyncio.sleep(0.01)
    raise RuntimeError("MCP session manager не стартовал")


def _jwt(email: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"email": email}).encode()).decode().rstrip("=")
    return f"header.{payload}.sig"


def _patch_user(monkeypatch: pytest.MonkeyPatch, user: Any) -> None:
    monkeypatch.setattr(
        "app.api.deps_auth.fetch_user_info_from_gateway",
        AsyncMock(return_value={"sub": user.sub, "email": user.email}),
    )

    async def _build(*_args: object, **_kwargs: object) -> Any:
        return user

    monkeypatch.setattr("app.api.deps_auth.build_user_public", _build)


async def _mcp_client(sqlite_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override_db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)


def _rpc(name: str, arguments: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    }


async def _call(client: AsyncClient, token: str | None, name: str, arguments: dict[str, object] | None = None) -> Any:
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return await client.post("/api/v1/mcp", headers=headers, json=_rpc(name, arguments))


def _tool_list(response: Any) -> list[dict[str, object]]:
    """Полный список из structured output. Текст MCP режет list по элементам."""
    structured = (response.json().get("result") or {}).get("structuredContent") or {}
    items = structured["result"]
    assert isinstance(items, list)
    return items


def _tool_text(response: Any) -> str:
    body = response.json()
    result = body.get("result") or {}
    if result.get("isError"):
        content = result.get("content") or []
        return str(content[0].get("text") if content else body)
    content = result.get("content") or []
    if content and isinstance(content[0], dict) and "text" in content[0]:
        return str(content[0]["text"])
    structured = result.get("structuredContent")
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False)
    return json.dumps(body, ensure_ascii=False)


async def test_mcp_without_bearer_is_401(mcp_runtime: None, sqlite_session: AsyncSession) -> None:
    async for client in _mcp_client(sqlite_session):
        response = await _call(client, None, "whoami")
        assert response.status_code == 401
        assert response.json()["code"] == "unauthorized"


async def test_mcp_rejects_employee_and_timesheet_only(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async for client in _mcp_client(sqlite_session):
        for user in (user_outstaff_not_manager(), user_portal_developer()):
            _patch_user(monkeypatch, user)
            response = await _call(client, "token", "whoami")
            assert response.status_code == 200
            assert "менеджер" in _tool_text(response).lower() or "администратор" in _tool_text(response).lower()


async def test_mcp_manager_whoami_and_cannot_purge(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_user(monkeypatch, user_portal_manager())
    async for client in _mcp_client(sqlite_session):
        who = await _call(client, "token", "whoami")
        assert who.status_code == 200
        text = _tool_text(who)
        assert "manager-sub" in text
        assert "isError" not in text or '"isError": false' in who.text or "manager-sub" in text
        purge = await _call(client, "token", "documents_purge", {"document_id": str(uuid.uuid4())})
        assert "администратор" in _tool_text(purge).lower()


async def test_mcp_admin_purge_missing_document_passes_gate(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_user(monkeypatch, user_portal_admin())
    async for client in _mcp_client(sqlite_session):
        response = await _call(client, "token", "documents_purge", {"document_id": str(uuid.uuid4())})
        assert "не найден" in _tool_text(response).lower()


async def test_mcp_email_profile_when_userinfo_rejects_token(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.deps_auth.fetch_user_info_from_gateway", AsyncMock(return_value=None))
    async for client in _mcp_client(sqlite_session):
        response = await _call(client, _jwt("admin@example.com"), "whoami")
        text = _tool_text(response)
        assert "admin-sub" in text
        assert "true" in text.lower()


async def test_mcp_manager_cannot_exclude_column_from_kpi_admin_can(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    column = PortalTaskColumn(title="Готово", color="#6131cf", status_key="mcp-done", position=9)
    sqlite_session.add(column)
    await sqlite_session.commit()
    async for client in _mcp_client(sqlite_session):
        _patch_user(monkeypatch, user_portal_manager())
        denied = await _call(
            client,
            "token",
            "task_columns_update",
            {"column_id": str(column.id), "exclude_from_kpi": True},
        )
        assert "администратор" in _tool_text(denied).lower()
        _patch_user(monkeypatch, user_portal_admin())
        allowed = await _call(
            client,
            "token",
            "task_columns_update",
            {"column_id": str(column.id), "exclude_from_kpi": True},
        )
        assert "mcp-done" in _tool_text(allowed)


async def test_mcp_manager_board_stays_own_admin_sees_requested(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sqlite_session.add_all(
        [
            PortalManagerSpecialist(
                manager_sub="manager-sub",
                specialist_sub="own-spec",
                column_key="new",
                position=0,
                created_at=datetime.now(UTC),
            ),
            PortalManagerSpecialist(
                manager_sub="admin-sub",
                specialist_sub="foreign-spec",
                column_key="new",
                position=0,
                created_at=datetime.now(UTC),
            ),
        ]
    )
    await sqlite_session.commit()
    async for client in _mcp_client(sqlite_session):
        _patch_user(monkeypatch, user_portal_manager())
        own = await _call(client, "token", "specialists_board", {"manager_sub": "admin-sub", "limit": 50})
        own_text = _tool_text(own)
        assert "foreign-spec" not in own_text
        assert "own-spec" in own_text
        _patch_user(monkeypatch, user_portal_admin())
        foreign = await _call(client, "token", "specialists_board", {"manager_sub": "admin-sub", "limit": 50})
        assert "foreign-spec" in _tool_text(foreign)


async def test_mcp_manager_moves_specialist_to_column(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sqlite_session.add_all(
        [
            PortalSpecialistColumn(key="new", title="Новые", color="#6366f1", position=0),
            PortalSpecialistColumn(key="fired", title="Уволен", color="#888888", position=1),
            PortalManagerSpecialist(
                manager_sub="manager-sub",
                specialist_sub="own-spec",
                column_key="new",
                position=0,
                created_at=datetime.now(UTC),
            ),
        ]
    )
    await sqlite_session.commit()
    _patch_user(monkeypatch, user_portal_manager())
    async for client in _mcp_client(sqlite_session):
        moved = await _call(
            client,
            "token",
            "specialists_move",
            {"specialist_sub": "own-spec", "column_key": "fired", "expected_version": 1},
        )
        body = json.loads(_tool_text(moved))
        assert body["column_key"] == "fired"
        assert body["version"] == 2
        assert body["specialist_sub"] == "own-spec"
        missing = await _call(
            client,
            "token",
            "specialists_move",
            {"specialist_sub": "own-spec", "column_key": "missing", "expected_version": 2},
        )
        assert "колонка воронки не найдена" in _tool_text(missing).lower()


async def test_mcp_manager_adds_task_file_and_named_link(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_user(monkeypatch, user_portal_manager())
    pdf = base64.b64encode(b"%PDF-1.4 mcp file").decode()

    def _fake_presigned_url(_storage_key: str, **kwargs: object) -> str:
        suffix = "attachment" if kwargs.get("force_download") else "inline"
        return f"https://minio.local/sk-mcp?disposition={suffix}"

    async for client in _mcp_client(sqlite_session):
        with (
            patch(
                "app.portal_collab.services.task_file.async_upload_file",
                new_callable=AsyncMock,
                return_value="sk-mcp",
            ),
            patch(
                "app.portal_collab.services.task_file.async_delete_object",
                new_callable=AsyncMock,
            ),
            patch(
                "app.portal_collab.services.task_file.get_presigned_url",
                MagicMock(side_effect=_fake_presigned_url),
            ),
        ):
            created = await _call(
                client,
                "token",
                "tasks_create",
                {"title": "Задача из MCP", "description": "Описание из MCP", "assignee_subs": ["manager-sub"]},
            )
            created_text = _tool_text(created)
            assert "Задача из MCP" in created_text
            task_id = str(json.loads(created_text)["id"])
            empty_card = json.loads(
                _tool_text(await _call(client, "token", "tasks_get", {"task_id": task_id})),
            )
            assert empty_card["links"] == []
            assert empty_card["files"] == []
            uploaded = await _call(
                client,
                "token",
                "tasks_files_add",
                {
                    "task_id": task_id,
                    "filename": "report.pdf",
                    "content_type": "application/pdf",
                    "content_base64": pdf,
                },
            )
            uploaded_text = _tool_text(uploaded)
            assert "report.pdf" in uploaded_text
            assert "minio.local" in uploaded_text
            linked = await _call(
                client,
                "token",
                "tasks_links_add",
                {"task_id": task_id, "url": "https://example.com/spec", "title": "Макет"},
            )
            linked_text = _tool_text(linked)
            assert "Макет" in linked_text
            assert "https://example.com/spec" in linked_text
            card = json.loads(_tool_text(await _call(client, "token", "tasks_get", {"task_id": task_id})))
            assert card["links"][0]["title"] == "Макет"
            assert card["links"][0]["url"] == "https://example.com/spec"
            assert card["files"][0]["original_filename"] == "report.pdf"
            removed_file = json.loads(
                _tool_text(
                    await _call(
                        client,
                        "token",
                        "tasks_files_delete",
                        {"task_id": task_id, "file_id": card["files"][0]["id"]},
                    ),
                ),
            )
            assert removed_file == {"ok": True}
            removed_link = json.loads(
                _tool_text(
                    await _call(
                        client,
                        "token",
                        "tasks_links_delete",
                        {"task_id": task_id, "link_id": card["links"][0]["id"]},
                    ),
                ),
            )
            assert removed_link == {"ok": True}
            cleared = json.loads(_tool_text(await _call(client, "token", "tasks_get", {"task_id": task_id})))
            assert cleared["files"] == []
            assert cleared["links"] == []


async def test_mcp_manager_adds_task_comment_without_image(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_user(monkeypatch, user_portal_manager())
    async for client in _mcp_client(sqlite_session):
        created = await _call(
            client,
            "token",
            "tasks_create",
            {"title": "Задача с комментарием", "description": "Описание из MCP", "assignee_subs": ["manager-sub"]},
        )
        task_id = str(json.loads(_tool_text(created))["id"])
        commented = json.loads(
            _tool_text(
                await _call(
                    client,
                    "token",
                    "task_comments_add",
                    {"task_id": task_id, "body": "Сохранены"},
                ),
            ),
        )
        assert commented["body"] == "Сохранены"
        assert commented["task_id"] == task_id
        assert "media_id" not in commented
        listed = _tool_list(await _call(client, "token", "task_comments_list", {"task_id": task_id}))
        assert listed[0]["comment_id"] == commented["comment_id"]
        assert listed[0]["body"] == "Сохранены"
        removed = json.loads(
            _tool_text(
                await _call(
                    client,
                    "token",
                    "task_comments_delete",
                    {"task_id": task_id, "comment_id": commented["comment_id"]},
                ),
            ),
        )
        assert removed == {"ok": True}
        assert _tool_list(await _call(client, "token", "task_comments_list", {"task_id": task_id})) == []


async def test_mcp_manager_deletes_document_file_and_comment(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = base64.b64encode(b"%PDF-1.4 mcp file").decode()
    _patch_user(monkeypatch, user_portal_manager())

    def _fake_presigned_url(_storage_key: str, **kwargs: object) -> str:
        suffix = "attachment" if kwargs.get("force_download") else "inline"
        return f"https://minio.local/sk-doc?disposition={suffix}"

    async for client in _mcp_client(sqlite_session):
        with (
            patch(
                "app.portal_documents.services.document_file.async_upload_file",
                new_callable=AsyncMock,
                return_value="sk-doc",
            ),
            patch(
                "app.portal_documents.services.document_file.async_delete_object",
                new_callable=AsyncMock,
            ),
            patch(
                "app.portal_documents.services.document_file.get_presigned_url",
                MagicMock(side_effect=_fake_presigned_url),
            ),
        ):
            created = json.loads(
                _tool_text(
                    await _call(client, "token", "documents_create", {"title": "Документ из MCP"}),
                ),
            )
            document_id = str(created["id"])
            uploaded = json.loads(
                _tool_text(
                    await _call(
                        client,
                        "token",
                        "documents_files_add",
                        {
                            "document_id": document_id,
                            "filename": "note.pdf",
                            "content_type": "application/pdf",
                            "content_base64": pdf,
                        },
                    ),
                ),
            )
            listed_files = _tool_list(
                await _call(client, "token", "documents_files_list", {"document_id": document_id}),
            )
            assert listed_files[0]["id"] == uploaded["id"]
            assert listed_files[0]["original_filename"] == "note.pdf"
            commented = json.loads(
                _tool_text(
                    await _call(
                        client,
                        "token",
                        "document_comments_add",
                        {"document_id": document_id, "body": "К документу"},
                    ),
                ),
            )
            listed_comments = _tool_list(
                await _call(client, "token", "document_comments_list", {"document_id": document_id}),
            )
            assert listed_comments[0]["comment_id"] == commented["comment_id"]
            assert listed_comments[0]["body"] == "К документу"
            removed_file = json.loads(
                _tool_text(
                    await _call(
                        client,
                        "token",
                        "documents_files_delete",
                        {"document_id": document_id, "file_id": uploaded["id"]},
                    ),
                ),
            )
            assert removed_file == {"ok": True}
            removed_comment = json.loads(
                _tool_text(
                    await _call(
                        client,
                        "token",
                        "document_comments_delete",
                        {"document_id": document_id, "comment_id": commented["comment_id"]},
                    ),
                ),
            )
            assert removed_comment == {"ok": True}
            assert _tool_list(await _call(client, "token", "documents_files_list", {"document_id": document_id})) == []
            assert (
                _tool_list(await _call(client, "token", "document_comments_list", {"document_id": document_id})) == []
            )


async def test_mcp_file_rejects_bad_base64_and_over_limit(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.portal_mcp.file_payload import MAX_ENCODED_LENGTH

    _patch_user(monkeypatch, user_portal_manager())
    async for client in _mcp_client(sqlite_session):
        broken = await _call(
            client,
            "token",
            "tasks_files_add",
            {
                "task_id": str(uuid.uuid4()),
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "content_base64": "!!!!",
            },
        )
        assert "base64" in _tool_text(broken).lower()
        huge = await _call(
            client,
            "token",
            "tasks_files_add",
            {
                "task_id": str(uuid.uuid4()),
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "content_base64": "A" * (MAX_ENCODED_LENGTH + 1),
            },
        )
        assert "миб" in _tool_text(huge).lower()


_TEMPLATE_BLOCKS = (
    "Проблема",
    "Результат",
    "Критерий «готово»",
    "Что сделать",
    "Связанные материалы",
)


async def test_mcp_tasks_template_returns_blocks_without_creating_task(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_user(monkeypatch, user_portal_manager())
    async for client in _mcp_client(sqlite_session):
        before = _tool_list(await _call(client, "token", "tasks_list", {}))
        shown = json.loads(_tool_text(await _call(client, "token", "tasks_template", {})))
        after = _tool_list(await _call(client, "token", "tasks_list", {}))
    assert "template" in shown
    text = str(shown["template"])
    for block in _TEMPLATE_BLOCKS:
        assert block in text
    assert [row["id"] for row in after] == [row["id"] for row in before]


@pytest.mark.parametrize("description", ["", "   ", "\n\t"])
async def test_mcp_tasks_create_rejects_blank_description(
    description: str,
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_user(monkeypatch, user_portal_manager())
    async for client in _mcp_client(sqlite_session):
        refused = await _call(
            client,
            "token",
            "tasks_create",
            {"title": "Без описания", "description": description, "assignee_subs": ["manager-sub"]},
        )
        listed = _tool_list(await _call(client, "token", "tasks_list", {}))
    result = refused.json().get("result") or {}
    assert result.get("isError") is True
    assert "шаблон" in _tool_text(refused).lower()
    assert all(row.get("title") != "Без описания" for row in listed)


async def test_mcp_tasks_create_keeps_description(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_user(monkeypatch, user_portal_manager())
    body = "Проблема\nНет шаблона.\n\nРезультат\nКарточка с текстом."
    async for client in _mcp_client(sqlite_session):
        created = json.loads(
            _tool_text(
                await _call(
                    client,
                    "token",
                    "tasks_create",
                    {"title": "С описанием", "description": body, "assignee_subs": ["manager-sub"]},
                ),
            ),
        )
    assert created["title"] == "С описанием"
    assert created["description"] == body


async def test_mcp_portal_users_list_returns_sub_and_name(
    mcp_runtime: None,
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_user(monkeypatch, user_portal_manager())
    async for client in _mcp_client(sqlite_session):
        rows = _tool_list(await _call(client, "token", "portal_users_list", {"limit": 50}))
    manager = next(row for row in rows if row["sub"] == "manager-sub")
    assert manager["display_name"] == "Manager"
    assert manager["email"] == "mgr@example.com"
