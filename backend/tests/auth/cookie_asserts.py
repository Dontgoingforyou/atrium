"""Проверки Set-Cookie refresh-токена (BFF)."""

from __future__ import annotations

from httpx import Response


def refresh_set_cookie(response: Response) -> str:
    """Заголовок Set-Cookie для ``rt``, либо пустая строка."""
    for item in response.headers.get_list("set-cookie"):
        if item.lower().startswith("rt="):
            return item
    return ""


def assert_refresh_cookie_set(response: Response, *, value: str) -> None:
    header = refresh_set_cookie(response)
    assert header, "ожидается Set-Cookie rt="
    assert header.startswith(f"rt={value}") or f"rt={value};" in header
    lower = header.lower()
    assert "httponly" in lower
    assert "path=/api/v1/auth/refresh" in lower
    assert "samesite=lax" in lower


def assert_refresh_cookie_cleared(response: Response) -> None:
    header = refresh_set_cookie(response)
    assert header, "logout должен сбросить cookie rt"
    lower = header.lower().replace(" ", "")
    assert "max-age=0" in lower or "max-age=-1" in lower
