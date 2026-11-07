"""Публичный контракт httpOnly cookie refresh-токена."""

from __future__ import annotations

from app.services.auth_cookies import (
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_PATH,
    clear_refresh_cookie,
    get_refresh_token_from_request,
    set_refresh_cookie,
)
from starlette.requests import Request
from starlette.responses import Response


def test_set_refresh_cookie_flags_and_path() -> None:
    resp = Response()
    set_refresh_cookie(resp, "secret-rt", secure=True)
    raw = resp.headers.get("set-cookie", "")
    assert raw.startswith(f"{REFRESH_COOKIE_NAME}=secret-rt")
    lower = raw.lower()
    assert "httponly" in lower
    assert f"path={REFRESH_COOKIE_PATH}" in lower
    assert "samesite=lax" in lower
    assert "secure" in lower


def test_set_refresh_cookie_not_secure_when_debug() -> None:
    resp = Response()
    set_refresh_cookie(resp, "rt-val", secure=False)
    assert "secure" not in resp.headers.get("set-cookie", "").lower()


def test_get_refresh_token_prefers_cookie_over_body() -> None:
    scope = {
        "type": "http",
        "method": "POST",
        "path": REFRESH_COOKIE_PATH,
        "headers": [(b"cookie", b"rt=from-cookie")],
    }
    req = Request(scope)
    assert get_refresh_token_from_request(req, "from-body") == "from-cookie"


def test_get_refresh_token_falls_back_to_body() -> None:
    scope = {"type": "http", "method": "POST", "path": REFRESH_COOKIE_PATH, "headers": []}
    req = Request(scope)
    assert get_refresh_token_from_request(req, "from-body") == "from-body"


def test_get_refresh_token_none_when_missing() -> None:
    scope = {"type": "http", "method": "POST", "path": REFRESH_COOKIE_PATH, "headers": []}
    req = Request(scope)
    assert get_refresh_token_from_request(req, None) is None


def test_clear_refresh_cookie_expires() -> None:
    resp = Response()
    clear_refresh_cookie(resp, secure=True)
    raw = resp.headers.get("set-cookie", "").lower().replace(" ", "")
    assert raw.startswith(f"{REFRESH_COOKIE_NAME}=")
    assert "max-age=0" in raw
    assert f"path={REFRESH_COOKIE_PATH}" in raw
