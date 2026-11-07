"""Уникальные кейсы KeycloakAdminAuth. HTTP-гейт `/admin` — tests/admin/test_admin_http_gate.py."""

from __future__ import annotations

from typing import Any

from app.admin.auth import KeycloakAdminAuth
from app.main import app
from httpx import ASGITransport, AsyncClient


class _MockRequest:
    def __init__(self, session: dict[str, Any] | None = None, base_url: str = "http://localhost:8000/") -> None:
        self.session: dict[str, Any] = session if session is not None else {}
        self.base_url = base_url  # type: ignore[assignment]

    def __str__(self) -> str:
        return self.base_url


async def test_admin_form_login_always_returns_false() -> None:
    request = _MockRequest()
    assert await KeycloakAdminAuth(secret_key="test-secret").login(request) is False  # type: ignore[arg-type]


async def test_admin_exit_to_portal_redirects_root() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
        r = await ac.post("/admin/exit-to-portal")
    assert r.status_code == 303
    assert r.headers.get("location") == "/"
