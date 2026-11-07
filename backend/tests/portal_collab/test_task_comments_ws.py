"""WebSocket тредов комментариев задачи."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.core.exceptions import ForbiddenError
from app.main import app
from app.portal_chat.comment_thread_events import COMMENT_THREAD_UPDATED_EVENT
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.helpers.portal_test_users import user_portal_no_idp_groups, user_portal_regular
from tests.helpers.ws_client import websocket_connect_with_ticket
from tests.portal_collab.conftest import assert_api_error, override_dependency


def test_task_comments_ws_ticket_and_ws_rejects_bad_ticket(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_regular),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        t = client.post("/api/v1/portal/tasks", json={"title": "WS task", "assignee_sub": "admin-sub"})
        assert t.status_code == 201, t.text
        task_id = t.json()["id"]
        r = client.post(f"/api/v1/portal/tasks/{task_id}/comments/ws-ticket")
        assert r.status_code == 201, r.text
        assert "ticket" in r.json()
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                "/api/v1/portal/tasks/00000000-0000-0000-0000-00000000aaaa/comments/ws"
                "?ticket=00000000-0000-0000-0000-00000000dead"
            ):
                pass
        assert exc_info.value.code == 4001


def test_task_comments_ws_ticket_403_foreign_task(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_regular),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        t = client.post("/api/v1/portal/tasks", json={"title": "Чужая для B", "assignee_sub": "admin-sub"})
        assert t.status_code == 201, t.text
        task_id = t.json()["id"]

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_no_idp_groups),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(f"/api/v1/portal/tasks/{task_id}/comments/ws-ticket")
        assert_api_error(r, 403, "forbidden")


def test_task_comments_ws_ticket_404_unknown_task(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    missing_id = uuid.uuid4()
    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_regular),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(f"/api/v1/portal/tasks/{missing_id}/comments/ws-ticket")
        assert_api_error(r, 404, "not_found")


def test_task_comment_publishes_thread_updated_to_websocket(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_regular),
    ):
        client = TestClient(app, raise_server_exceptions=True)
        t = client.post("/api/v1/portal/tasks", json={"title": "E2E thread WS", "assignee_sub": "admin-sub"})
        assert t.status_code == 201, t.text
        task_id = t.json()["id"]
        r = client.post(f"/api/v1/portal/tasks/{task_id}/comments/ws-ticket")
        assert r.status_code == 201, r.text
        ticket = r.json()["ticket"]
        with client.websocket_connect(f"/api/v1/portal/tasks/{task_id}/comments/ws?ticket={ticket}") as ws:
            c = client.post(f"/api/v1/portal/tasks/{task_id}/comments", json={"body": "e2e comment"})
            assert c.status_code == 201, c.text
            raw = ws.receive_text()
            data = json.loads(raw)
            assert data["event"] == COMMENT_THREAD_UPDATED_EVENT


def test_task_comments_ws_url_task_id_mismatch_closes_4001(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_regular),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        t1 = client.post("/api/v1/portal/tasks", json={"title": "WS A", "assignee_sub": "user-sub"})
        t2 = client.post("/api/v1/portal/tasks", json={"title": "WS B", "assignee_sub": "user-sub"})
        assert t1.status_code == 201 and t2.status_code == 201
        id_a, id_b = t1.json()["id"], t2.json()["id"]
        r = client.post(f"/api/v1/portal/tasks/{id_a}/comments/ws-ticket")
        ticket = r.json()["ticket"]
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, f"/api/v1/portal/tasks/{id_b}/comments/ws", ticket):
                pass
        assert exc_info.value.code == 4001


def test_task_comments_ws_get_task_forbidden_after_ticket(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    async def _forbidden(*_a: object, **_k: object) -> None:
        raise ForbiddenError("Нет доступа к задаче")

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_regular),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        t = client.post("/api/v1/portal/tasks", json={"title": "WS forbid", "assignee_sub": "user-sub"})
        task_id = t.json()["id"]
        r = client.post(f"/api/v1/portal/tasks/{task_id}/comments/ws-ticket")
        ticket = r.json()["ticket"]
        monkeypatch.setattr("app.portal_collab.routes.tasks.svc.get_task", _forbidden)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, f"/api/v1/portal/tasks/{task_id}/comments/ws", ticket):
                pass
        assert exc_info.value.code == 4001
