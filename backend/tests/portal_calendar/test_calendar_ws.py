"""WebSocket календаря: тикет через микросервис, прокси WS."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from app.api.deps import get_db_session
from app.core.config import Settings
from app.main import app
from fastapi import WebSocketDisconnect
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient
from tests.portal_calendar.conftest import CALENDAR_API, override_dependency

_AUTH = {"Authorization": "Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiJ1c2VyLXN1YiJ9.x"}


def _patch_calendar_settings(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    monkeypatch.setattr("app.portal_calendar.remote.get_settings", lambda: settings)
    monkeypatch.setattr("app.portal_calendar.routes.calendar_ws.get_settings", lambda: settings)


@pytest.mark.asyncio
async def test_calendar_ws_ticket_returns_ticket(
    client_user: AsyncClient,
    patch_oidc_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_oidc_settings.calendar_service_url = "http://calendar.test"
    patch_oidc_settings.calendar_product = "atrium"
    _patch_calendar_settings(monkeypatch, patch_oidc_settings)

    async def _fake_issue(self: object) -> str:
        return "ticket-from-ms"

    monkeypatch.setattr(
        "app.portal_calendar.remote.CalendarRemote.issue_ws_ticket",
        _fake_issue,
    )
    r = await client_user.post(f"{CALENDAR_API}/ws-ticket", headers=_AUTH)
    assert r.status_code == 201, r.text
    assert r.json().get("ticket") == "ticket-from-ms"


@pytest.mark.asyncio
async def test_calendar_ws_ticket_forbidden_for_timesheet(
    client_developer: AsyncClient,
    patch_oidc_settings: Settings,
) -> None:
    patch_oidc_settings.calendar_service_url = "http://calendar.test"
    r = await client_developer.post(f"{CALENDAR_API}/ws-ticket", headers=_AUTH)
    assert r.status_code == 403, r.text


def test_calendar_ws_rejects_without_service_url(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_oidc_settings.calendar_service_url = ""
    _patch_calendar_settings(monkeypatch, patch_oidc_settings)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with override_dependency(get_db_session, _db):
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"{CALENDAR_API}/ws?ticket=dead-ticket"):
                pass
        assert exc_info.value.code == 4001


def test_calendar_ws_closes_when_upstream_unreachable(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Нет живого микросервиса — прокси закрывает сокет (не локальная шина)."""
    patch_oidc_settings.calendar_service_url = "http://127.0.0.1:1"
    _patch_calendar_settings(monkeypatch, patch_oidc_settings)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with override_dependency(get_db_session, _db):
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"{CALENDAR_API}/ws?ticket=dead-ticket-xx"):
                pass
        assert exc_info.value.code == 4001
