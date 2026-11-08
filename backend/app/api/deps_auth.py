import logging
import time
from typing import Annotated, Any

import httpx
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, HttpClient
from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError, ServiceUnavailableError, UnauthorizedError
from app.core.permissions import is_manager_or_admin, is_timesheet_only
from app.core.utils import decode_jwt_payload_unverified
from app.infrastructure.cache import token_cache
from app.schemas.auth import UserPublic
from app.services.demo_accounts import (
    DEMO_GROUPS_CLAIM,
    DemoTokenInvalid,
    demo_signing_secret,
    read_demo_access_claims,
)
from app.services.sso.login_allowlist import ensure_portal_login_allowed
from app.services.sso.token_service import fetch_user_info_from_gateway
from app.services.user_profile import build_user_public

logger = logging.getLogger(__name__)

# Версия формата userinfo в Redis:
# 1 — telegram/birthday; 2 — добавлен claim position (должность SSO);
# 3 — добавлен claim gid_number (основной отдел SSO).
_USERINFO_CACHE_VERSION = 3


def extract_bearer_token(authorization: str | None) -> str | None:
    """Достаёт токен из заголовка ``Authorization: Bearer <token>``.

    Возвращает ``None``, если заголовок отсутствует, имеет другую схему или токен пуст.
    Единая точка разбора — не дублировать проверку `.lower().startswith("bearer ")` по роутерам.
    """
    if not isinstance(authorization, str) or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return token or None


def is_plausible_jwt(token: str) -> bool:
    """Минимальная проверка: JWT состоит из 3 частей, разделённых точкой.

    Не верифицирует подпись — достаточно отсеять случайный мусор и не позволить
    произвольно инвалидировать кэш чужих токенов без знания самого токена.
    Используется в beacon-эндпоинтах (`portal_users.py`, `auth.py`), где токен
    передаётся в теле запроса без предварительной проверки Authorization-заголовком.
    """
    parts = token.split(".")
    return len(parts) == 3 and all(len(p) >= 4 for p in parts)  # noqa: PLR2004


def _is_userinfo_cache_valid(payload: dict[str, Any]) -> bool:
    """Кэш пригоден, если есть sub и актуальная версия (не legacy без specialist-полей)."""
    return bool(payload.get("sub")) and payload.get("_userinfo_v") == _USERINFO_CACHE_VERSION


def _prepare_userinfo_for_cache(payload: dict[str, Any]) -> dict[str, Any]:
    """Дополняет payload перед записью в Redis."""
    out = dict(payload)
    out["_userinfo_v"] = _USERINFO_CACHE_VERSION
    return out


def _extract_token_exp(token: str) -> int | None:
    """Декодирует exp-клейм из JWT без верификации подписи.

    Используется только для вычисления TTL кэша — не для проверки авторизации.
    """
    payload = decode_jwt_payload_unverified(token)
    if payload is None:
        return None
    exp = payload.get("exp")
    return int(exp) if exp is not None else None


def _cache_ttl(token: str, max_ttl: int) -> int:
    """Возвращает TTL кэша = min(max_ttl, секунды до истечения токена).

    Если exp не удалось извлечь — возвращает max_ttl.
    Всегда не менее 1 секунды.
    """
    exp = _extract_token_exp(token)
    if exp is None:
        return max_ttl
    remaining = exp - int(time.time())
    if remaining <= 0:
        return 1
    return min(max_ttl, remaining)


async def _rewrite_cached_sub_if_remapped(
    token: str,
    cached_payload: dict[str, Any],
    canonical_sub: str,
    max_ttl: int,
) -> None:
    """Если SSO-sub в кэше ≠ канонический sub профиля — перезаписать кэш."""
    cached_sub = str(cached_payload.get("sub") or "")
    if not canonical_sub or cached_sub == canonical_sub:
        return
    rewritten = dict(cached_payload)
    rewritten["sub"] = canonical_sub
    await token_cache.set_cached_userinfo(
        token,
        _prepare_userinfo_for_cache(rewritten),
        ttl=_cache_ttl(token, max_ttl),
    )


async def verify_access_token(
    token: str,
    db: AsyncSession,
    http_client: httpx.AsyncClient,
) -> UserPublic:
    """Валидировать Bearer-токен и вернуть пользователя.

    Выделена из get_current_user для использования в WebSocket-эндпоинтах,
    где токен передаётся query-параметром, а не заголовком Authorization.
    Поднимает AppError-подклассы при невалидном токене.
    """
    if len(token) > 8192:
        logger.warning("400: токен превышает допустимую длину (%d)", len(token))
        raise BadRequestError("Токен слишком длинный")
    s = get_settings()
    try:
        demo_claims = read_demo_access_claims(token, demo_signing_secret(s))
    except DemoTokenInvalid:
        raise UnauthorizedError("Невалидный или истёкший токен") from None
    if demo_claims is not None:
        user = await build_user_public(db, demo_claims, groups_claim_path=DEMO_GROUPS_CLAIM)
        ensure_portal_login_allowed(user, s)
        return user
    if not s.sso_enabled:
        raise ServiceUnavailableError(s.sso_disabled_detail)

    cached_payload = await token_cache.get_cached_userinfo(token)
    if cached_payload and _is_userinfo_cache_valid(cached_payload):
        logger.debug("SSO userinfo из кэша Redis: sub=%s", cached_payload.get("sub"))
        user = await build_user_public(db, cached_payload, groups_claim_path=s.sso_groups_claim)
        ensure_portal_login_allowed(user, s)
        # После remap email→UUID переписываем кэш: иначе каждый запрос снова ищет по email.
        await _rewrite_cached_sub_if_remapped(token, cached_payload, user.sub, s.token_cache_ttl)
        return user

    try:
        gateway_payload = await fetch_user_info_from_gateway(settings=s, access_token=token, http_client=http_client)
    except httpx.RequestError as exc:
        logger.warning("503: SSO userinfo недоступен: %s", exc)
        raise ServiceUnavailableError(
            "Сервис входа временно недоступен. Повторите попытку через минуту.",
        ) from exc
    if not gateway_payload or not gateway_payload.get("sub"):
        logger.warning("401: SSO вернул пустой payload (невалидный или истёкший токен)")
        raise UnauthorizedError("Невалидный или истёкший токен")

    user = await build_user_public(db, gateway_payload, groups_claim_path=s.sso_groups_claim)
    ensure_portal_login_allowed(user, s)
    cached = _prepare_userinfo_for_cache(gateway_payload)
    if str(cached.get("sub") or "") != user.sub:
        cached["sub"] = user.sub
    await token_cache.set_cached_userinfo(
        token,
        cached,
        ttl=_cache_ttl(token, s.token_cache_ttl),
    )
    return user


async def get_current_user(
    db: DbSession,
    http_client: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
) -> UserPublic:
    token = extract_bearer_token(authorization)
    if token is None:
        logger.warning("401: отсутствует или некорректный заголовок Authorization")
        raise UnauthorizedError("Требуется заголовок Authorization: Bearer")
    return await verify_access_token(token, db, http_client)


async def require_portal_admin(
    user: Annotated[UserPublic, Depends(get_current_user)],
) -> UserPublic:
    if not user.is_portal_admin:
        raise ForbiddenError("Требуется группа администратора портала в IdP")
    return user


async def require_portal_manager_or_admin(
    user: Annotated[UserPublic, Depends(get_current_user)],
) -> UserPublic:
    """Менеджер или администратор портала."""
    if is_manager_or_admin(user):
        return user
    raise ForbiddenError("Требуется роль менеджера или администратора портала")


async def require_non_developer(
    user: Annotated[UserPublic, Depends(get_current_user)],
) -> UserPublic:
    """Запретить доступ пользователям с режимом «только таймшиты» ко всем разделам портала кроме ТШ.

    Используется как зависимость на уровне роутера — применяется ко всем эндпоинтам сразу
    (см. `NON_DEVELOPER_ROUTE_DEPENDENCIES` ниже).
    """
    if is_timesheet_only(user):
        logger.warning(
            "Отказ в доступе к разделу портала: user_sub=%s position=%s",
            user.sub,
            user.position,
        )
        raise ForbiddenError("Этот раздел недоступен для вашей роли")
    return user


CurrentUser = Annotated[UserPublic, Depends(get_current_user)]
PortalAdminUser = Annotated[UserPublic, Depends(require_portal_admin)]
PortalManagerOrAdminUser = Annotated[UserPublic, Depends(require_portal_manager_or_admin)]
NonDeveloperUser = Annotated[UserPublic, Depends(require_non_developer)]

# Единый источник для `dependencies=[...]` роутеров, которым закрыт доступ пользователям
# с режимом «только таймшиты» (portal_collab, portal_chat, api/v1/router и т.д.) —
# не копировать `[Depends(require_non_developer)]` в каждый router.py.
NON_DEVELOPER_ROUTE_DEPENDENCIES = [Depends(require_non_developer)]
