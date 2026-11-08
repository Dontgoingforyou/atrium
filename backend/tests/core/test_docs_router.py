"""Тесты защищённой OpenAPI (/openapi.json) и страниц /docs, /redoc.

Примечание по монкейпатчингу: docs_router импортирует get_settings и verify_access_token
на уровне модуля, поэтому патчить нужно ссылки внутри модуля роутера, а не в core/config.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError, UnauthorizedError
from app.schemas.auth import UserPublic
from httpx import AsyncClient

from tests.conftest import make_oidc_settings


def _sso_on_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        sso_client_id="cid",
        sso_client_secret="csec",
        sso_service_url="https://sso.example",
        sso_api_prefix="/api/",
        sso_token_path="auth/oauth2/token",
        sso_refresh_path="auth/refresh",
        sso_userinfo_path="auth/me",
        sso_auth_page_path="/auth",
    )


def _make_user_public() -> UserPublic:
    return UserPublic(
        sub="user-1",
        email="u@example.com",
        full_name="User One",
        username="user1",
        idp_groups=[],
        is_portal_admin=False,
    )


async def test_openapi_json_requires_bearer(client: AsyncClient) -> None:
    r = await client.get("/openapi.json")
    assert r.status_code == 401
    body = r.json()
    assert body["code"] == "unauthorized"
    assert "bearer" in body["message"].lower()
    assert r.headers.get("www-authenticate") == "Bearer"


async def test_openapi_json_rejects_non_bearer_scheme(client: AsyncClient) -> None:
    r = await client.get("/openapi.json", headers={"Authorization": "Basic x"})
    assert r.status_code == 401
    assert r.json()["code"] == "unauthorized"
    assert r.headers.get("www-authenticate") == "Bearer"


async def test_openapi_json_empty_bearer_token(client: AsyncClient) -> None:
    r = await client.get("/openapi.json", headers={"Authorization": "Bearer "})
    assert r.status_code == 401
    assert r.json()["code"] == "unauthorized"
    assert "Bearer" in r.json()["message"]
    assert r.headers.get("www-authenticate") == "Bearer"


async def test_openapi_json_503_when_sso_no_credentials(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # make_oidc_settings явно обнуляет все sso_client_id_*, чтобы Settings
    # не подхватил значения из env-переменных тестового окружения.
    s = make_oidc_settings(sso_client_id="", sso_client_secret="")
    # Патчим ссылку в docs_router (импорт на уровне модуля)
    monkeypatch.setattr("app.api.docs_router.get_settings", lambda: s)

    r = await client.get("/openapi.json", headers={"Authorization": "Bearer any"})
    assert r.status_code == 503
    assert "client_id" in r.json()["message"]


async def test_openapi_json_503_when_sso_no_service_url(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = make_oidc_settings(sso_service_url="")
    # Патчим ссылку в docs_router (импорт на уровне модуля)
    monkeypatch.setattr("app.api.docs_router.get_settings", lambda: s)

    r = await client.get("/openapi.json", headers={"Authorization": "Bearer t"})
    assert r.status_code == 503
    assert "адрес шлюза" in r.json()["message"]


async def test_openapi_json_401_invalid_token(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = _sso_on_settings()
    monkeypatch.setattr("app.api.docs_router.get_settings", lambda: s)
    monkeypatch.setattr(
        "app.api.docs_router.verify_access_token",
        AsyncMock(side_effect=UnauthorizedError("Невалидный или истёкший токен")),
    )

    r = await client.get("/openapi.json", headers={"Authorization": "Bearer bad.jwt.token"})
    assert r.status_code == 401
    assert r.json()["code"] == "unauthorized"
    assert "токен" in r.json()["message"].lower()
    assert r.headers.get("www-authenticate") == "Bearer"


async def test_openapi_json_503_when_verify_raises_app_error(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = _sso_on_settings()
    monkeypatch.setattr("app.api.docs_router.get_settings", lambda: s)
    monkeypatch.setattr(
        "app.api.docs_router.verify_access_token",
        AsyncMock(side_effect=ServiceUnavailableError("SSO временно недоступен")),
    )

    r = await client.get("/openapi.json", headers={"Authorization": "Bearer t.t.t"})
    assert r.status_code == 503
    assert r.json()["code"] == "service_unavailable"
    assert "sso" in r.json()["message"].lower()


async def test_openapi_json_ok_with_valid_token(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verify_access_token успешно возвращает пользователя → 200 + OpenAPI-схема."""
    s = _sso_on_settings()
    monkeypatch.setattr("app.api.docs_router.get_settings", lambda: s)
    monkeypatch.setattr(
        "app.api.docs_router.verify_access_token",
        AsyncMock(return_value=_make_user_public()),
    )

    r = await client.get("/openapi.json", headers={"Authorization": "Bearer hdr.pld.sig"})
    assert r.status_code == 200
    body = r.json()
    assert "openapi" in body
    assert "paths" in body


async def test_docs_page_returns_html_shell_without_schema(client: AsyncClient) -> None:
    r = await client.get("/docs")
    assert r.status_code == 200
    assert "swagger" in r.text.lower()
    assert "url: '/openapi.json'" in r.text
    assert '"paths"' not in r.text
    assert '"openapi"' not in r.text


async def test_redoc_page_returns_html_shell_without_schema(client: AsyncClient) -> None:
    r = await client.get("/redoc")
    assert r.status_code == 200
    assert "redoc" in r.text.lower()
    assert '"paths"' not in r.text
    assert '"openapi"' not in r.text


@pytest.mark.parametrize("path", ("/docs", "/redoc", "/openapi.json"))
async def test_docs_disabled_returns_404_without_ui_or_spec(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    s = make_oidc_settings(docs_enabled=False)
    monkeypatch.setattr("app.api.docs_router.get_settings", lambda: s)

    r = await client.get(path)
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"
    low = r.text.lower()
    assert "swagger-ui" not in low
    assert "redoc-container" not in low
    assert '"paths"' not in r.text
