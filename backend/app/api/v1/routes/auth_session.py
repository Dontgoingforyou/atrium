"""Сессия портального пользователя: профиль, сессия SQLAdmin, выход.

Отделено от `auth.py` (OAuth/password обмен токенов) по размеру файла и
по смыслу: здесь — управление уже выданной сессией,
там — её первичное получение.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Header, Request, Response, status

from app.api.deps import HttpClient
from app.api.deps_auth import CurrentUser, extract_bearer_token, is_plausible_jwt
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.infrastructure.cache import token_cache
from app.schemas.auth import LogoutBeaconRequest, UserPublic
from app.services.auth_cookies import clear_refresh_cookie
from app.services.sso.token_service import logout_via_sso

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/me",
    summary="Текущий пользователь (Bearer access token)",
)
async def me(user: CurrentUser) -> UserPublic:
    """Профиль с актуальными ролями портала из БД."""
    return user


def _admin_session_keys_clear(request: Request) -> None:
    for key in (
        "admin_sub",
        "admin_username",
        "admin_email",
        "admin_full_name",
    ):
        request.session.pop(key, None)


@router.post(
    "/admin-session",
    summary="Сессия SQLAdmin по Bearer токену портала (JSON с URL для перехода)",
)
async def admin_session(
    request: Request,
    user: CurrentUser,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    """
    Одна точка OAuth у SPA; панель /admin открывается по cookie после проверки
    is_portal_admin (группа atrium_role_admin в профиле SSO, как у /auth/me).

    Ответ JSON, а не HTTP-редирект: иначе fetch с redirect=follow получает 200 от HTML /admin/
    и фронт не может обработать переход.
    """
    if not user.is_portal_admin:
        raise ForbiddenError("Недостаточно прав для панели администратора")
    token = extract_bearer_token(authorization)
    if token is None:
        raise UnauthorizedError("Требуется заголовок Authorization: Bearer")
    request.session["admin_sub"] = user.sub
    request.session["admin_username"] = user.username
    request.session["admin_email"] = user.email
    request.session["admin_full_name"] = user.full_name
    return {"redirect_url": "/admin/"}


@router.post(
    "/logout",
    summary="Выход: сброс сессии",
)
async def logout(
    request: Request,
    http_client: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    """
    Вызывается кнопкой «Выход» в SPA.
    1. Удаляет токен из Redis-кэша (мгновенно).
    2. Уведомляет SSO-шлюз — инвалидирует refresh_token в IdP (best-effort).
    3. Сбрасывает httpOnly cookie refresh-токена.
    """
    _admin_session_keys_clear(request)
    s = get_settings()
    token = extract_bearer_token(authorization)
    if token is not None:
        await token_cache.invalidate_token(token)
        if s.sso_enabled:
            await logout_via_sso(settings=s, access_token=token, http_client=http_client)

    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_refresh_cookie(resp, secure=not s.debug)
    return resp


@router.post(
    "/logout-beacon",
    summary="Выход через sendBeacon (закрытие вкладки)",
    status_code=204,
)
async def logout_beacon(body: LogoutBeaconRequest) -> None:
    """
    Вызывается через `sendBeacon` на beforeunload (закрытие вкладки, F5, уход по ссылке).

    Только сбрасывает Redis-кэш userinfo для этого access_token — без вызова SSO logout:
    иначе любой refresh страницы или «На сайт» из админки ломал бы сессию в IdP.

    Полный выход из SSO — только POST /auth/logout (кнопка «Выход»). Cookie SQLAdmin не трогаем.

    Безопасность: sendBeacon не поддерживает заголовки Authorization, поэтому принимаем
    токен в теле. Проверяем JWT-формат (`is_plausible_jwt`) чтобы предотвратить массовую
    инвалидацию кэша произвольными строками.
    """
    token = (body.access_token or "").strip()
    if not token or not is_plausible_jwt(token):
        return
    await token_cache.invalidate_token(token)
    logger.debug("logout-beacon: Redis-кэш userinfo сброшен")
