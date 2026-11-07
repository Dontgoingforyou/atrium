"""Unit-тесты HTTP-вызовов SSO (token_service) с моками httpx."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.core.config import Settings
from app.services.sso import token_service as ts


def test_sso_error_log_detail_prefers_error_description() -> None:
    resp = MagicMock()
    resp.json = lambda: {
        "error": "invalid_grant",
        "error_description": "code expired",
        "access_token": "must-not-appear",
    }
    resp.content = b"{}"
    detail = ts.sso_error_log_detail(resp)
    assert detail == "code expired"
    assert "must-not-appear" not in detail


def test_sso_error_log_detail_non_json() -> None:
    resp = MagicMock()
    resp.json = MagicMock(side_effect=ValueError("no json"))
    resp.content = b"access_token=secret"
    detail = ts.sso_error_log_detail(resp)
    assert detail == f"non-json ({len(resp.content)} байт)"
    assert "secret" not in detail


def _settings_full() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        sso_client_id="c",
        sso_client_secret="s",
        sso_service_url="https://gw.example",
        sso_api_prefix="/api/",
        sso_token_path="auth/oauth2/token",
        sso_refresh_path="auth/refresh",
        sso_userinfo_path="auth/me",
        sso_logout_path="auth/logout",
    )


@pytest.mark.asyncio
async def test_fetch_user_info_returns_none_without_url() -> None:
    s = Settings(database_url="sqlite+aiosqlite:///:memory:", sso_service_url="")
    client = AsyncMock()
    out = await ts.fetch_user_info_from_gateway(settings=s, access_token="t", http_client=client)
    assert out is None
    client.get.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_user_info_non_200_returns_none() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=401, text="no")
    client = AsyncMock()
    client.get = AsyncMock(return_value=resp)
    assert await ts.fetch_user_info_from_gateway(settings=s, access_token="t", http_client=client) is None


@pytest.mark.asyncio
async def test_fetch_user_info_reraises_httpx_request_error() -> None:
    s = _settings_full()
    client = AsyncMock()
    client.get = AsyncMock(side_effect=httpx.ConnectTimeout(""))
    with pytest.raises(httpx.ConnectTimeout):
        await ts.fetch_user_info_from_gateway(settings=s, access_token="t", http_client=client)


@pytest.mark.asyncio
async def test_fetch_user_info_maps_sub_without_keycloak_id() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=200, text="")
    resp.json = lambda: {
        "sub": "sso-sub-1",
        "email": "a@b.c",
        "username": "u",
        "full_name": "FN",
        "groups": ["g1"],
    }
    client = AsyncMock()
    client.get = AsyncMock(return_value=resp)
    out = await ts.fetch_user_info_from_gateway(settings=s, access_token="tok", http_client=client)
    assert out == {
        "sub": "sso-sub-1",
        "email": "a@b.c",
        "preferred_username": "u",
        "name": "FN",
        "groups": ["g1"],
        "position": None,
        "gid_number": None,
        "telegram": None,
        "birthday": None,
    }


@pytest.mark.asyncio
async def test_fetch_user_info_maps_keycloak_id_legacy() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=200, text="")
    resp.json = lambda: {
        "keycloak_id": "kid",
        "email": "a@b.c",
        "username": "u",
        "full_name": "FN",
        "groups": ["g1"],
    }
    client = AsyncMock()
    client.get = AsyncMock(return_value=resp)
    out = await ts.fetch_user_info_from_gateway(settings=s, access_token="tok", http_client=client)
    assert out == {
        "sub": "kid",
        "email": "a@b.c",
        "preferred_username": "u",
        "name": "FN",
        "groups": ["g1"],
        "position": None,
        "gid_number": None,
        "telegram": None,
        "birthday": None,
    }


@pytest.mark.asyncio
async def test_fetch_user_info_prefers_public_id_when_sub_is_email() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=200, text="")
    resp.json = lambda: {
        "sub": "a@b.c",
        "public_id": "dafb7718-9aa5-1040-855b-9d7a3abe3472",
        "email": "a@b.c",
        "username": "u",
        "full_name": "FN",
        "groups": ["g1"],
    }
    client = AsyncMock()
    client.get = AsyncMock(return_value=resp)
    out = await ts.fetch_user_info_from_gateway(settings=s, access_token="tok", http_client=client)
    assert out is not None
    assert out["sub"] == "dafb7718-9aa5-1040-855b-9d7a3abe3472"


def test_resolve_sso_user_sub_prefers_sub_over_email() -> None:
    assert ts.resolve_sso_user_sub({"sub": "uuid-1", "email": "a@b.c"}) == "uuid-1"


def test_resolve_sso_user_sub_prefers_public_id_over_email_sub() -> None:
    assert (
        ts.resolve_sso_user_sub(
            {
                "sub": "user@example.com",
                "public_id": "dafb7718-9aa5-1040-855b-9d7a3abe3472",
                "email": "user@example.com",
            }
        )
        == "dafb7718-9aa5-1040-855b-9d7a3abe3472"
    )


def test_resolve_sso_user_sub_prefers_public_id_over_keycloak_id() -> None:
    assert ts.resolve_sso_user_sub({"public_id": "pub-1", "keycloak_id": "kid-legacy", "sub": "s"}) == "pub-1"


def test_resolve_sso_user_sub_falls_back_to_email() -> None:
    assert ts.resolve_sso_user_sub({"email": "User@Example.COM"}) == "user@example.com"


def test_resolve_sso_user_sub_email_like_sub_uses_email_field_case() -> None:
    assert ts.resolve_sso_user_sub({"sub": "User@Example.COM"}) == "user@example.com"


def test_resolve_sso_user_sub_supports_id_field() -> None:
    assert ts.resolve_sso_user_sub({"id": "user-42", "email": "a@b.c"}) == "user-42"


@pytest.mark.asyncio
async def test_resolve_gateway_payload_after_password_login_email_only_user() -> None:
    s = _settings_full()
    client = AsyncMock()
    client.get = AsyncMock()
    out = await ts.resolve_gateway_payload_after_password_login(
        settings=s,
        login_response={
            "access_token": "t",
            "user": {"email": "u@example.com", "username": "u", "full_name": "User"},
        },
        access_token="t",
        http_client=client,
    )
    assert out is not None
    assert out["sub"] == "u@example.com"
    assert out["email"] == "u@example.com"
    client.get.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_gateway_payload_after_password_login_jwt_sub() -> None:
    import base64
    import json

    s = _settings_full()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "jwt-sub"}).encode()).rstrip(b"=").decode()
    token = f"hdr.{payload}.sig"
    client = AsyncMock()
    client.get = AsyncMock()
    out = await ts.resolve_gateway_payload_after_password_login(
        settings=s,
        login_response={"access_token": token, "user": {"username": "u"}},
        access_token=token,
        http_client=client,
    )
    assert out is not None
    assert out["sub"] == "jwt-sub"
    client.get.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_user_info_maps_position() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=200, text="")
    resp.json = lambda: {
        "keycloak_id": "kid",
        "email": "a@b.c",
        "username": "u",
        "full_name": "FN",
        "groups": ["students", "outstaff"],
        "position": "au_specialist",
    }
    client = AsyncMock()
    client.get = AsyncMock(return_value=resp)
    out = await ts.fetch_user_info_from_gateway(settings=s, access_token="tok", http_client=client)
    assert out is not None
    assert out["position"] == "au_specialist"
    assert out["gid_number"] is None


@pytest.mark.asyncio
async def test_fetch_user_info_maps_gid_number() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=200, text="")
    resp.json = lambda: {
        "keycloak_id": "kid",
        "email": "a@b.c",
        "username": "u",
        "full_name": "FN",
        "groups": ["outstaff"],
        "gid_number": "10000",
    }
    client = AsyncMock()
    client.get = AsyncMock(return_value=resp)
    out = await ts.fetch_user_info_from_gateway(settings=s, access_token="tok", http_client=client)
    assert out is not None
    assert out["gid_number"] == "10000"


@pytest.mark.asyncio
async def test_fetch_user_info_maps_gid_number_int() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=200, text="")
    resp.json = lambda: {
        "sub": "sso-sub-1",
        "email": "a@b.c",
        "gid_number": 10000,
    }
    client = AsyncMock()
    client.get = AsyncMock(return_value=resp)
    out = await ts.fetch_user_info_from_gateway(settings=s, access_token="tok", http_client=client)
    assert out is not None
    assert out["gid_number"] == "10000"


@pytest.mark.asyncio
async def test_fetch_user_info_falls_back_sub_in_payload() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=200, text="")
    resp.json = lambda: {"sub": "direct", "email": None}
    client = AsyncMock()
    client.get = AsyncMock(return_value=resp)
    out = await ts.fetch_user_info_from_gateway(settings=s, access_token="t", http_client=client)
    assert out is not None
    assert out["sub"] == "direct"


@pytest.mark.asyncio
async def test_exchange_code_non_200_returns_none() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=400, text="bad")
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    out = await ts.exchange_authorization_code(
        settings=s,
        client_id="c",
        client_secret="s",
        code="code",
        redirect_uri="http://localhost/cb",
        code_verifier=None,
        http_client=client,
    )
    assert out is None


@pytest.mark.asyncio
async def test_exchange_code_ok_includes_verifier() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=200, text="")
    resp.json = lambda: {"access_token": "a"}
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    out = await ts.exchange_authorization_code(
        settings=s,
        client_id="c",
        client_secret="s",
        code="code",
        redirect_uri="http://localhost/cb",
        code_verifier="ver",
        http_client=client,
    )
    assert out == {"access_token": "a"}
    payload = client.post.await_args.kwargs["json"]
    assert payload["code_verifier"] == "ver"


@pytest.mark.asyncio
async def test_refresh_non_200_returns_none() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=500, text="err")
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    assert (
        await ts.refresh_access_token(
            settings=s,
            client_id="c",
            client_secret="s",
            refresh_token="rt",
            http_client=client,
        )
        is None
    )


@pytest.mark.asyncio
async def test_refresh_ok() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=200, text="")
    resp.json = lambda: {"access_token": "new"}
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    out = await ts.refresh_access_token(
        settings=s,
        client_id="c",
        client_secret="s",
        refresh_token="rt",
        http_client=client,
    )
    assert out == {"access_token": "new"}


@pytest.mark.asyncio
async def test_logout_false_without_service_url() -> None:
    s = Settings(database_url="sqlite+aiosqlite:///:memory:", sso_service_url="")
    client = AsyncMock()
    assert not await ts.logout_via_sso(settings=s, access_token="t", http_client=client)
    client.post.assert_not_called()


@pytest.mark.asyncio
async def test_logout_true_on_200() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=200, text="ok")
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    assert await ts.logout_via_sso(settings=s, access_token="t", http_client=client) is True


@pytest.mark.asyncio
async def test_logout_false_on_non_200() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=401, text="x")
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    assert await ts.logout_via_sso(settings=s, access_token="t", http_client=client) is False


@pytest.mark.asyncio
async def test_logout_false_on_connection_error() -> None:
    s = _settings_full()
    client = AsyncMock()
    client.post = AsyncMock(side_effect=RuntimeError("network"))
    assert await ts.logout_via_sso(settings=s, access_token="t", http_client=client) is False


@pytest.mark.asyncio
async def test_logout_normalizes_api_prefix_without_leading_slash() -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        sso_client_id="c",
        sso_client_secret="s",
        sso_service_url="https://gw.example",
        sso_api_prefix="api/",
        sso_logout_path="auth/logout",
    )
    resp = MagicMock(status_code=200, text="ok")
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    assert await ts.logout_via_sso(settings=s, access_token="t", http_client=client) is True
    called_url = client.post.await_args.args[0]
    assert called_url == "https://gw.example/api/auth/logout"


@pytest.mark.asyncio
async def test_login_with_password_ok_strips_email() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=200)
    resp.json = lambda: {"access_token": "at"}
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    status, body = await ts.login_with_password(
        settings=s,
        email="  u@example.com  ",
        password="secret",
        http_client=client,
        scope="openid",
    )
    assert status == 200
    assert body == {"access_token": "at"}
    payload = client.post.await_args.kwargs["json"]
    assert payload["email"] == "u@example.com"
    assert payload["password"] == "secret"
    assert payload["scope"] == "openid"


@pytest.mark.asyncio
async def test_login_with_password_401() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=401)
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    status, body = await ts.login_with_password(
        settings=s,
        email="u@example.com",
        password="bad",
        http_client=client,
    )
    assert status == 401
    assert body is None


@pytest.mark.asyncio
async def test_login_with_password_non_200() -> None:
    s = _settings_full()
    resp = MagicMock(status_code=503, text="down")
    resp.json = MagicMock(side_effect=ValueError("no json"))
    resp.content = b"down"
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    status, body = await ts.login_with_password(
        settings=s,
        email="u@example.com",
        password="secret",
        http_client=client,
    )
    assert status == 503
    assert body is None


@pytest.mark.asyncio
async def test_login_with_password_reraises_request_error() -> None:
    s = _settings_full()
    client = AsyncMock()
    client.post = AsyncMock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(httpx.ConnectError):
        await ts.login_with_password(
            settings=s,
            email="u@example.com",
            password="secret",
            http_client=client,
        )
