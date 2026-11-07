"""Ветки verify_access_token (кэш, SSO, длина токена)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.api.deps_auth import extract_bearer_token, is_plausible_jwt, verify_access_token
from app.core.config import Settings
from app.core.exceptions import BadRequestError, ServiceUnavailableError, UnauthorizedError
from app.schemas.auth import UserPublic


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("aaaa.bbbb.cccc", True),
        ("bad", False),
        ("a.b.c", False),
        ("", False),
        ("aaaa.bbbb.cccc.dddd", False),
        ("aaa.bbbb.cccc", False),
    ],
)
def test_is_plausible_jwt(token: str, expected: bool) -> None:
    assert is_plausible_jwt(token) is expected


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, None),
        ("Basic abc", None),
        ("Bearer", None),
        ("Bearer   ", None),
        ("Bearer tok", "tok"),
        ("BEARER TokVal", "TokVal"),
    ],
)
def test_extract_bearer_token(header: str | None, expected: str | None) -> None:
    assert extract_bearer_token(header) == expected


@pytest.mark.asyncio
async def test_verify_token_rejects_too_long_token() -> None:
    db = AsyncMock()
    client = httpx.AsyncClient()
    token = "x" * 8193
    with pytest.raises(BadRequestError) as exc:
        await verify_access_token(token, db, client)
    assert exc.value.status_code == 400
    await client.aclose()


@pytest.mark.asyncio
async def test_verify_token_503_when_sso_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(database_url="sqlite+aiosqlite:///:memory:", sso_service_url="")
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    db = AsyncMock()
    client = httpx.AsyncClient()
    with pytest.raises(ServiceUnavailableError) as exc:
        await verify_access_token("short", db, client)
    assert exc.value.status_code == 503
    await client.aclose()


@pytest.mark.asyncio
async def test_verify_token_rewrites_cache_when_sso_sub_remapped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Кэш с email-sub переписывается на canonical UUID после build_user_public."""
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        sso_client_id="c",
        sso_client_secret="sec",
        sso_service_url="https://gw.example",
        sso_api_prefix="/api/",
        sso_userinfo_path="me",
        sso_token_path="t",
        sso_refresh_path="r",
        token_cache_ttl=300,
    )
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)

    cached = {
        "sub": "user@example.com",
        "email": "user@example.com",
        "groups": [],
        "telegram": None,
        "birthday": None,
        "_userinfo_v": 3,
    }
    get_cache = AsyncMock(return_value=cached)
    set_cache = AsyncMock()
    monkeypatch.setattr("app.api.deps_auth.token_cache.get_cached_userinfo", get_cache)
    monkeypatch.setattr("app.api.deps_auth.token_cache.set_cached_userinfo", set_cache)

    build = AsyncMock(
        return_value=UserPublic(
            sub="canonical-uuid",
            email="user@example.com",
            username="user",
            full_name="",
            idp_groups=[],
            is_portal_admin=False,
        )
    )
    monkeypatch.setattr("app.api.deps_auth.build_user_public", build)

    db = AsyncMock()
    client = httpx.AsyncClient()
    user = await verify_access_token("tok", db, client)
    assert user.sub == "canonical-uuid"
    set_cache.assert_awaited_once()
    rewritten = set_cache.await_args.args[1]
    assert rewritten["sub"] == "canonical-uuid"
    assert rewritten.get("_userinfo_v") == 3
    await client.aclose()


@pytest.mark.asyncio
async def test_verify_token_legacy_cache_misses_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy-кэш без _userinfo_v или с устаревшей версией не используется — идём в SSO."""
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        sso_client_id="c",
        sso_client_secret="sec",
        sso_service_url="https://gw.example",
        sso_api_prefix="/api/",
        sso_userinfo_path="me",
        sso_token_path="t",
        sso_refresh_path="r",
    )
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    monkeypatch.setattr(
        "app.api.deps_auth.token_cache.get_cached_userinfo",
        AsyncMock(return_value={"sub": "old", "email": "old@example.com", "groups": []}),
    )

    gw_payload = {"sub": "gw-user", "email": "g@example.com", "groups": []}
    fetch = AsyncMock(return_value=gw_payload)
    monkeypatch.setattr("app.api.deps_auth.fetch_user_info_from_gateway", fetch)

    set_cache = AsyncMock()
    monkeypatch.setattr("app.api.deps_auth.token_cache.set_cached_userinfo", set_cache)

    build = AsyncMock(
        return_value=UserPublic(
            sub="gw-user",
            email="g@example.com",
            username="g",
            full_name="",
            idp_groups=[],
            is_portal_admin=False,
        )
    )
    monkeypatch.setattr("app.api.deps_auth.build_user_public", build)

    db = AsyncMock()
    client = MagicMock(spec=httpx.AsyncClient)
    user = await verify_access_token("tok", db, client)
    assert user.sub == "gw-user"
    fetch.assert_awaited_once()
    set_cache.assert_awaited_once()
    cached_arg = set_cache.await_args.args[1]
    assert cached_arg.get("_userinfo_v") == 3


@pytest.mark.asyncio
async def test_verify_token_fetches_gateway_and_sets_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        sso_client_id="c",
        sso_client_secret="sec",
        sso_service_url="https://gw.example",
        sso_api_prefix="/api/",
        sso_userinfo_path="me",
        sso_token_path="t",
        sso_refresh_path="r",
        sso_groups_claim="groups",
    )
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    monkeypatch.setattr("app.api.deps_auth.token_cache.get_cached_userinfo", AsyncMock(return_value=None))

    gw_payload = {"sub": "gw-user", "email": "g@example.com", "groups": []}
    fetch = AsyncMock(return_value=gw_payload)
    monkeypatch.setattr("app.api.deps_auth.fetch_user_info_from_gateway", fetch)

    set_cache = AsyncMock()
    monkeypatch.setattr("app.api.deps_auth.token_cache.set_cached_userinfo", set_cache)

    build = AsyncMock(
        return_value=UserPublic(
            sub="gw-user",
            email="g@example.com",
            username="g",
            full_name="",
            idp_groups=[],
            is_portal_admin=False,
        )
    )
    monkeypatch.setattr("app.api.deps_auth.build_user_public", build)

    db = AsyncMock()
    client = MagicMock(spec=httpx.AsyncClient)
    user = await verify_access_token("good", db, client)
    assert user.sub == "gw-user"
    fetch.assert_awaited_once()
    set_cache.assert_awaited_once()
    cached_arg = set_cache.await_args.args[1]
    assert cached_arg.get("_userinfo_v") == 3
    build.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_token_401_when_gateway_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        sso_client_id="c",
        sso_client_secret="sec",
        sso_service_url="https://gw.example",
        sso_api_prefix="/api/",
        sso_userinfo_path="me",
        sso_token_path="t",
        sso_refresh_path="r",
    )
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    monkeypatch.setattr("app.api.deps_auth.token_cache.get_cached_userinfo", AsyncMock(return_value=None))
    monkeypatch.setattr("app.api.deps_auth.fetch_user_info_from_gateway", AsyncMock(return_value=None))

    db = AsyncMock()
    client = MagicMock(spec=httpx.AsyncClient)
    with pytest.raises(UnauthorizedError) as exc:
        await verify_access_token("bad", db, client)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_token_503_when_gateway_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        sso_client_id="c",
        sso_client_secret="sec",
        sso_service_url="https://gw.example",
        sso_api_prefix="/api/",
        sso_userinfo_path="me",
        sso_token_path="t",
        sso_refresh_path="r",
    )
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    monkeypatch.setattr("app.api.deps_auth.token_cache.get_cached_userinfo", AsyncMock(return_value=None))

    async def _raise_httpx(*_a: object, **_k: object) -> None:
        raise httpx.ConnectTimeout("")

    monkeypatch.setattr("app.api.deps_auth.fetch_user_info_from_gateway", _raise_httpx)
    db = AsyncMock()
    client = MagicMock(spec=httpx.AsyncClient)
    with pytest.raises(ServiceUnavailableError) as exc:
        await verify_access_token("t", db, client)
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_verify_token_cache_hit_same_sub_does_not_rewrite(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        sso_client_id="c",
        sso_client_secret="sec",
        sso_service_url="https://gw.example",
        sso_api_prefix="/api/",
        sso_userinfo_path="me",
        sso_token_path="t",
        sso_refresh_path="r",
        token_cache_ttl=300,
    )
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    cached = {"sub": "same-sub", "email": "u@example.com", "groups": [], "_userinfo_v": 3}
    monkeypatch.setattr("app.api.deps_auth.token_cache.get_cached_userinfo", AsyncMock(return_value=cached))
    set_cache = AsyncMock()
    monkeypatch.setattr("app.api.deps_auth.token_cache.set_cached_userinfo", set_cache)
    fetch = AsyncMock()
    monkeypatch.setattr("app.api.deps_auth.fetch_user_info_from_gateway", fetch)
    monkeypatch.setattr(
        "app.api.deps_auth.build_user_public",
        AsyncMock(
            return_value=UserPublic(
                sub="same-sub",
                email="u@example.com",
                username="u",
                full_name="",
                idp_groups=[],
                is_portal_admin=False,
            )
        ),
    )
    db = AsyncMock()
    client = MagicMock(spec=httpx.AsyncClient)
    user = await verify_access_token("tok", db, client)
    assert user.sub == "same-sub"
    fetch.assert_not_awaited()
    set_cache.assert_not_awaited()
