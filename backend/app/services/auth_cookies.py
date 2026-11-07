"""Утилиты для httpOnly-cookie refresh-токена (BFF-паттерн).

Refresh-токен НЕ передаётся фронтенду в теле ответа — только через Set-Cookie.
Это исключает кражу токена через XSS из localStorage.
"""

from __future__ import annotations

import logging

from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

REFRESH_COOKIE_NAME = "rt"
# Путь ограничен: браузер отправит cookie только на /api/v1/auth/refresh
REFRESH_COOKIE_PATH = "/api/v1/auth/refresh"
# Максимальный срок жизни cookie: 30 дней (запас под типичный Keycloak SSO_SESSION_IDLE)
REFRESH_COOKIE_MAX_AGE = 30 * 24 * 3600


def set_refresh_cookie(
    response: Response,
    refresh_token: str,
    *,
    secure: bool,
    max_age: int = REFRESH_COOKIE_MAX_AGE,
) -> None:
    """Установить httpOnly cookie с refresh-токеном."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=secure,
        samesite="lax",
    )


def clear_refresh_cookie(response: Response, *, secure: bool) -> None:
    """Удалить cookie refresh-токена (logout)."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=secure,
        samesite="lax",
    )


def get_refresh_token_from_request(request: Request, body_refresh: str | None) -> str | None:
    """Получить refresh-токен: сначала из httpOnly cookie, затем из тела (backward compat)."""
    cookie_rt = request.cookies.get(REFRESH_COOKIE_NAME)
    if cookie_rt:
        return cookie_rt
    if body_refresh:
        logger.warning(
            "refresh_token передан в теле запроса — устаревший канал; используйте httpOnly cookie 'rt'",
        )
        return body_refresh
    return None
