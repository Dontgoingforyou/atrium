"""HTTP `app.api.v1.routes.auth`: authorization-url, token, refresh."""

from __future__ import annotations

from unittest.mock import MagicMock

import app.api.v1.routes.auth as auth_routes
import httpx
import pytest
from app.core.config import Settings
from app.services.sso.client_resolver import SsoCredentialsNotFoundError
from httpx import AsyncClient

from tests.auth.cookie_asserts import assert_refresh_cookie_set, refresh_set_cookie
from tests.conftest import make_oidc_settings

_CALLBACK = "http://localhost:5173/auth/callback"


async def test_authorization_url_sso_disabled(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = Settings(database_url="sqlite+aiosqlite:///:memory:", sso_service_url="")
    monkeypatch.setattr(auth_routes, "get_settings", lambda: s)
    response = await client.get(
        "/api/v1/auth/authorization-url",
        params={"redirect_uri": _CALLBACK, "code_challenge": "ch", "state": "st"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


async def test_authorization_url_bad_redirect(patch_oidc_settings: Settings, client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/authorization-url",
        params={"redirect_uri": "https://evil.example/callback", "code_challenge": "x", "state": "y"},
    )
    assert response.status_code == 400
    assert "redirect_uri" in response.json()["message"]


async def test_authorization_url_bad_challenge_method(patch_oidc_settings: Settings, client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/authorization-url",
        params={
            "redirect_uri": _CALLBACK,
            "code_challenge": "x",
            "state": "y",
            "code_challenge_method": "plain",
        },
    )
    assert response.status_code == 400
    assert "S256" in response.json()["message"]


async def test_authorization_url_ok(patch_oidc_settings: Settings, client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/authorization-url",
        params={"redirect_uri": _CALLBACK, "code_challenge": "challenge", "state": "stateval"},
    )
    assert response.status_code == 200
    url = response.json()["authorization_url"]
    assert url.startswith("https://sso.example/auth?")
    assert "code_challenge=challenge" in url
    assert "state=stateval" in url
    assert "client_id=test-client" in url


async def test_authorization_url_no_credentials_for_redirect(
    patch_oidc_settings: Settings,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_routes,
        "resolve_sso_credentials_for_redirect",
        MagicMock(side_effect=SsoCredentialsNotFoundError("uri")),
    )
    response = await client.get(
        "/api/v1/auth/authorization-url",
        params={"redirect_uri": _CALLBACK, "code_challenge": "x", "state": "y"},
    )
    assert response.status_code == 400
    assert "Внешний вход не настроен" in response.json()["message"]


async def test_authorization_url_uses_port_specific_client(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        sso_client_id="",
        sso_client_secret="",
        sso_client_id_5173="spa-5173",
        sso_client_secret_5173="sec-5173",
        sso_service_url="https://sso.example",
        sso_auth_page_path="/auth",
        sso_allowed_redirect_uris=_CALLBACK,
        sso_groups_claim="groups",
    )
    monkeypatch.setattr(auth_routes, "get_settings", lambda: s)
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    response = await client.get(
        "/api/v1/auth/authorization-url",
        params={"redirect_uri": _CALLBACK, "code_challenge": "x", "state": "y"},
    )
    assert response.status_code == 200
    assert "client_id=spa-5173" in response.json()["authorization_url"]


async def test_token_bad_redirect(patch_oidc_settings: Settings, client_sqlite_only: AsyncClient) -> None:
    response = await client_sqlite_only.post(
        "/api/v1/auth/token",
        json={"code": "abc", "redirect_uri": "https://evil.example/cb"},
    )
    assert response.status_code == 400
    assert "redirect_uri" in response.json()["message"]


async def test_token_no_credentials_for_redirect(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_routes,
        "resolve_sso_credentials_for_redirect",
        MagicMock(side_effect=SsoCredentialsNotFoundError("uri")),
    )
    response = await client_sqlite_only.post(
        "/api/v1/auth/token",
        json={"code": "c", "redirect_uri": _CALLBACK},
    )
    assert response.status_code == 400
    assert "Внешний вход не настроен" in response.json()["message"]


async def test_token_exchange_sso_unreachable(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _raise(**_kwargs: object) -> None:
        raise httpx.ConnectError("down")

    monkeypatch.setattr(auth_routes, "exchange_authorization_code", _raise)
    response = await client_sqlite_only.post(
        "/api/v1/auth/token",
        json={"code": "c", "redirect_uri": _CALLBACK},
    )
    assert response.status_code == 503
    assert "Сервис входа временно недоступен" in response.json()["message"]


async def test_token_exchange_empty_token_response(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _empty(**_kwargs: object) -> dict[str, str]:
        return {}

    monkeypatch.setattr(auth_routes, "exchange_authorization_code", _empty)
    response = await client_sqlite_only.post(
        "/api/v1/auth/token",
        json={"code": "c", "redirect_uri": _CALLBACK},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


async def test_token_exchange_userinfo_unreachable(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _exchange(**_kwargs: object) -> dict[str, str]:
        return {"access_token": "at", "expires_in": 60}

    async def _userinfo_fail(**_kwargs: object) -> None:
        raise httpx.ConnectError("down")

    monkeypatch.setattr(auth_routes, "exchange_authorization_code", _exchange)
    monkeypatch.setattr(auth_routes, "fetch_user_info_from_gateway", _userinfo_fail)
    response = await client_sqlite_only.post(
        "/api/v1/auth/token",
        json={"code": "c", "redirect_uri": _CALLBACK},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


async def test_token_exchange_returns_tokens_and_refresh_cookie(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _exchange(**_kwargs: object) -> dict[str, str | int]:
        return {"access_token": "dummy", "refresh_token": "r1", "expires_in": 60}

    async def _userinfo(**_kwargs: object) -> dict[str, object]:
        return {
            "sub": "user-1",
            "email": "u@example.com",
            "preferred_username": "u",
            "groups": ["outstaff"],
            "position": "au_chief",
        }

    monkeypatch.setattr(auth_routes, "exchange_authorization_code", _exchange)
    monkeypatch.setattr(auth_routes, "fetch_user_info_from_gateway", _userinfo)
    response = await client_sqlite_only.post(
        "/api/v1/auth/token",
        json={"code": "code", "redirect_uri": _CALLBACK, "code_verifier": "v" * 43},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "dummy"
    assert data["refresh_token"] is None
    assert data["user"]["sub"] == "user-1"
    assert data["user"]["idp_groups"] == ["outstaff"]
    assert data["user"]["position"] == "au_chief"
    assert data["user"]["is_portal_admin"] is False
    assert data["oauth_client_id"] == "test-client"
    assert_refresh_cookie_set(response, value="r1")


async def test_token_exchange_userinfo_without_sub(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _exchange(**_kwargs: object) -> dict[str, str]:
        return {"access_token": "at", "expires_in": 60}

    async def _userinfo(**_kwargs: object) -> dict[str, str]:
        return {"email": "u@example.com"}

    monkeypatch.setattr(auth_routes, "exchange_authorization_code", _exchange)
    monkeypatch.setattr(auth_routes, "fetch_user_info_from_gateway", _userinfo)
    response = await client_sqlite_only.post(
        "/api/v1/auth/token",
        json={"code": "c", "redirect_uri": _CALLBACK},
    )
    assert response.status_code == 401
    assert "профиль" in response.json()["message"]


async def test_token_exchange_au_specialist_position(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_exchange(**_kwargs: object) -> dict[str, str | int]:
        return {"access_token": "dummy", "refresh_token": "r1", "expires_in": 60}

    async def fake_user_info(**_kwargs: object) -> dict[str, object]:
        return {
            "sub": "au-spec",
            "email": "spec@example.com",
            "preferred_username": "spec",
            "groups": ["students", "outstaff"],
            "position": "au_specialist",
        }

    monkeypatch.setattr(auth_routes, "exchange_authorization_code", fake_exchange)
    monkeypatch.setattr(auth_routes, "fetch_user_info_from_gateway", fake_user_info)
    response = await client_sqlite_only.post(
        "/api/v1/auth/token",
        json={"code": "code", "redirect_uri": _CALLBACK, "code_verifier": "v" * 43},
    )
    assert response.status_code == 200
    user = response.json()["user"]
    assert user["position"] == "au_specialist"
    assert user["idp_groups"] == ["students", "outstaff"]


async def test_token_exchange_null_refresh_when_sso_omits_it(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_exchange(**_kwargs: object) -> dict[str, object]:
        return {"access_token": "access-abc", "expires_in": 300}

    async def fake_user_info(**_kwargs: object) -> dict[str, object]:
        return {"sub": "u-42", "email": "u@example.com", "preferred_username": "u", "groups": []}

    monkeypatch.setattr(auth_routes, "exchange_authorization_code", fake_exchange)
    monkeypatch.setattr(auth_routes, "fetch_user_info_from_gateway", fake_user_info)
    response = await client_sqlite_only.post(
        "/api/v1/auth/token",
        json={"code": "code", "redirect_uri": _CALLBACK, "code_verifier": "v" * 43},
    )
    assert response.status_code == 200
    assert response.json()["refresh_token"] is None
    assert refresh_set_cookie(response) == ""


@pytest.mark.parametrize(
    "verifier",
    ["v" * 42, "v" * 129],
)
async def test_token_exchange_code_verifier_length_422(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    verifier: str,
) -> None:
    response = await client_sqlite_only.post(
        "/api/v1/auth/token",
        json={"code": "code", "redirect_uri": _CALLBACK, "code_verifier": verifier},
    )
    assert response.status_code == 422


async def test_refresh_sso_unreachable(
    patch_oidc_settings: Settings,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _raise(**_kwargs: object) -> None:
        raise httpx.ConnectError("down")

    monkeypatch.setattr(auth_routes, "refresh_access_token", _raise)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "rt", "client_id": "test-client"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


async def test_refresh_empty_token_response(
    patch_oidc_settings: Settings,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _empty(**_kwargs: object) -> dict[str, str]:
        return {}

    monkeypatch.setattr(auth_routes, "refresh_access_token", _empty)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "rt", "client_id": "test-client"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


async def test_refresh_missing_token_is_401(patch_oidc_settings: Settings, client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/refresh", json={})
    assert response.status_code == 401
    assert "Refresh-токен" in response.json()["message"]


async def test_refresh_ok_single_client_without_explicit_client_id(
    patch_oidc_settings: Settings,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _refresh(**kwargs: object) -> dict[str, str | int]:
        assert kwargs["client_id"] == "test-client"
        return {"access_token": "new", "expires_in": 90, "refresh_token": "nr"}

    monkeypatch.setattr(auth_routes, "refresh_access_token", _refresh)
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "rt"})
    assert response.status_code == 200
    assert response.json()["access_token"] == "new"
    assert response.json()["refresh_token"] is None
    assert_refresh_cookie_set(response, value="nr")


async def test_refresh_prefers_cookie_over_body(
    patch_oidc_settings: Settings,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    async def _refresh(**kwargs: object) -> dict[str, str | int]:
        seen.append(str(kwargs["refresh_token"]))
        return {"access_token": "from-cookie", "expires_in": 90, "refresh_token": "rotated"}

    monkeypatch.setattr(auth_routes, "refresh_access_token", _refresh)
    client.cookies.set("rt", "cookie-rt")
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "body-rt"},
    )
    assert response.status_code == 200
    assert seen == ["cookie-rt"]
    assert response.json()["access_token"] == "from-cookie"
    assert_refresh_cookie_set(response, value="rotated")


async def test_refresh_requires_client_id_when_multiple_sso_clients(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = make_oidc_settings(
        sso_client_id="",
        sso_client_secret="",
        sso_client_id_5173="c5173",
        sso_client_secret_5173="s5173",
        sso_client_id_9088="c9088",
        sso_client_secret_9088="s9088",
    )
    monkeypatch.setattr(auth_routes, "get_settings", lambda: s)
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "rt"})
    assert response.status_code == 400
    assert "client_id" in response.json()["message"]


async def test_refresh_unknown_client_id_is_400(
    patch_oidc_settings: Settings,
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "rt", "client_id": "no-such-client"},
    )
    assert response.status_code == 400
    assert "client_id" in response.json()["message"]


async def test_refresh_ok_with_explicit_client_id(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = make_oidc_settings(
        sso_client_id="",
        sso_client_secret="",
        sso_client_id_5173="c5173",
        sso_client_secret_5173="s5173",
        sso_client_id_9088="c9088",
        sso_client_secret_9088="s9088",
    )
    monkeypatch.setattr(auth_routes, "get_settings", lambda: s)
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    called: dict[str, str] = {}

    async def fake_refresh(
        *,
        settings: object,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        http_client: object,
    ) -> dict[str, str]:
        called["client_id"] = client_id
        called["client_secret"] = client_secret
        assert refresh_token == "rt"
        return {"access_token": "new-access", "expires_in": 120}

    monkeypatch.setattr(auth_routes, "refresh_access_token", fake_refresh)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "rt", "client_id": "c9088"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "new-access"
    assert data["oauth_client_id"] == "c9088"
    assert data["refresh_token"] is None
    assert called == {"client_id": "c9088", "client_secret": "s9088"}


async def test_refresh_token_too_long_422(patch_oidc_settings: Settings, client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "r" * 8193})
    assert response.status_code == 422
