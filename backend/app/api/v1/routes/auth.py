from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.deps import DbSession, HttpClient
from app.core.config import Settings, get_settings
from app.core.exceptions import BadRequestError, ServiceUnavailableError, UnauthorizedError
from app.schemas.auth import (
    PasswordLoginRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TokenExchangeRequest,
    TokenResponse,
)
from app.services.auth_cookies import get_refresh_token_from_request, set_refresh_cookie
from app.services.sso.client_resolver import (
    SsoCredentialsNotFoundError,
    resolve_sso_credentials_for_client_id,
    resolve_sso_credentials_for_redirect,
)
from app.services.sso.login_allowlist import ensure_portal_login_allowed
from app.services.sso.token_service import (
    exchange_authorization_code,
    fetch_user_info_from_gateway,
    login_with_password,
    refresh_access_token,
    resolve_gateway_payload_after_password_login,
)
from app.services.user_profile import build_user_public

logger = logging.getLogger(__name__)

_SSO_UNAVAILABLE = (
    "Сервис аутентификации (SSO) временно недоступен. "
    "Проверьте, что из контейнера API достижим SSO_SERVICE_URL, и повторите."
)
# Fallback TTL токена, если SSO-шлюз не вернул expires_in.
_DEFAULT_TOKEN_EXPIRES_IN = 1800

router = APIRouter()


class AuthorizationUrlRead(BaseModel):
    """Ответ эндпоинта /auth/authorization-url."""

    authorization_url: str


def _require_sso() -> None:
    s = get_settings()
    if not s.sso_enabled:
        raise ServiceUnavailableError(s.sso_disabled_detail)


def _parse_token_grant(raw: dict[str, Any]) -> tuple[str, str | None, int]:
    """access_token/refresh_token/expires_in из ответа SSO-шлюза (login/exchange/refresh)."""
    access = str(raw["access_token"])
    refresh = raw.get("refresh_token") or None
    expires_in = int(raw.get("expires_in") or 0) or _DEFAULT_TOKEN_EXPIRES_IN
    return access, refresh, expires_in


def _token_grant_response(
    payload: TokenResponse | RefreshTokenResponse,
    *,
    refresh: str | None,
    secure: bool,
) -> JSONResponse:
    """Собирает JSON-ответ из payload и, при наличии refresh-токена, ставит httpOnly cookie.

    Возвращается ``JSONResponse`` напрямую (а не через ``response_model``): refresh-токен
    уходит клиенту только через ``Set-Cookie`` (security.mdc), поэтому тело ответа и cookie
    собираются здесь одной функцией — переиспользуется в password_login/token_exchange/refresh_token.
    """
    resp = JSONResponse(content=payload.model_dump())
    if refresh:
        set_refresh_cookie(resp, refresh, secure=secure)
    return resp


def _resolve_refresh_client_credentials(body: RefreshTokenRequest, s: Settings) -> tuple[str, str]:
    """Один зарегистрированный client_id или явный client_id из тела при нескольких клиентах."""
    all_ids = frozenset(cid for cid, _ in s.sso_client_credential_pairs())
    if body.client_id and body.client_id.strip():
        try:
            return resolve_sso_credentials_for_client_id(body.client_id, s)
        except SsoCredentialsNotFoundError as e:
            raise BadRequestError("Неизвестный или не настроенный client_id") from e
    if len(all_ids) <= 1:
        if not all_ids:
            raise ServiceUnavailableError(s.sso_disabled_detail)
        only = next(iter(all_ids))
        try:
            return resolve_sso_credentials_for_client_id(only, s)
        except SsoCredentialsNotFoundError as e:
            raise ServiceUnavailableError(s.sso_disabled_detail) from e
    raise BadRequestError("Укажите client_id (в окружении задано несколько SSO-клиентов)")


@router.get(
    "/authorization-url",
    summary="URL авторизации IdP (PKCE)",
    response_model=AuthorizationUrlRead,
)
async def authorization_url(
    redirect_uri: str = Query(description="Полный redirect_uri SPA (whitelist)"),
    code_challenge: str = Query(),
    state: str = Query(),
    code_challenge_method: str = Query(default="S256"),
) -> AuthorizationUrlRead:
    _require_sso()
    if code_challenge_method != "S256":
        raise BadRequestError("Поддерживается только code_challenge_method=S256")
    s = get_settings()
    if redirect_uri not in s.sso_redirect_uris_list:
        logger.warning(
            "Отклонён authorization-url: redirect_uri не в whitelist: %r",
            redirect_uri,
        )
        raise BadRequestError("Недопустимый redirect_uri")
    try:
        oauth_client_id, _ = resolve_sso_credentials_for_redirect(redirect_uri, s)
    except SsoCredentialsNotFoundError:
        raise BadRequestError("Нет учётных данных SSO для этого redirect_uri; задайте пару в .env") from None
    params = {
        "client_id": oauth_client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": s.sso_scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }
    auth_entry = s.sso_authorization_entry_url()
    return AuthorizationUrlRead(authorization_url=f"{auth_entry}?{urlencode(params)}")


def _resolve_password_login_redirect_uri(body: PasswordLoginRequest, s: Settings) -> str:
    if body.redirect_uri and body.redirect_uri.strip():
        redirect_uri = body.redirect_uri.strip()
        if redirect_uri not in s.sso_redirect_uris_list:
            logger.warning(
                "Отклонён password login: redirect_uri не в whitelist: %r",
                redirect_uri,
            )
            raise BadRequestError("Недопустимый redirect_uri")
        return redirect_uri
    uris = s.sso_redirect_uris_list
    if len(uris) == 1:
        return uris[0]
    raise BadRequestError("Укажите redirect_uri")


@router.post(
    "/login",
    summary="Вход по email и паролю (прокси SSO)",
    response_model=TokenResponse,
)
async def password_login(
    body: PasswordLoginRequest,
    db: DbSession,
    http_client: HttpClient,
) -> JSONResponse:
    _require_sso()
    s = get_settings()
    redirect_uri = _resolve_password_login_redirect_uri(body, s)
    try:
        oauth_client_id, _ = resolve_sso_credentials_for_redirect(redirect_uri, s)
    except SsoCredentialsNotFoundError:
        raise BadRequestError("Нет учётных данных SSO для этого redirect_uri; задайте пару в .env") from None

    try:
        login_status_code, raw = await login_with_password(
            settings=s,
            email=body.email,
            password=body.password,
            http_client=http_client,
            scope=s.sso_scopes or None,
        )
    except httpx.RequestError as exc:
        logger.warning("503: SSO password login недоступен: %s", exc)
        raise ServiceUnavailableError(_SSO_UNAVAILABLE) from exc

    if login_status_code == 401:
        raise UnauthorizedError("Неверный email или пароль")
    if login_status_code != 200 or not raw or "access_token" not in raw:
        raise ServiceUnavailableError(_SSO_UNAVAILABLE)

    access, refresh, expires_in = _parse_token_grant(raw)

    try:
        gateway_payload = await resolve_gateway_payload_after_password_login(
            settings=s,
            login_response=raw,
            access_token=access,
            http_client=http_client,
        )
    except httpx.RequestError as exc:
        logger.warning("503: SSO userinfo недоступен (после password login): %s", exc)
        raise ServiceUnavailableError(_SSO_UNAVAILABLE) from exc

    if not gateway_payload:
        raise UnauthorizedError("Не удалось получить профиль пользователя от SSO")

    user = await build_user_public(
        db,
        gateway_payload,
        groups_claim_path=s.sso_groups_claim,
    )
    ensure_portal_login_allowed(user, s)

    payload = TokenResponse(
        access_token=access,
        refresh_token=None,
        expires_in=expires_in,
        oauth_client_id=oauth_client_id,
        user=user,
        redirect_after_login="/",
    )
    return _token_grant_response(payload, refresh=refresh, secure=not s.debug)


@router.post(
    "/token",
    summary="Обмен authorization code на токены",
    response_model=TokenResponse,
)
async def token_exchange(
    body: TokenExchangeRequest,
    db: DbSession,
    http_client: HttpClient,
) -> JSONResponse:
    _require_sso()
    s = get_settings()
    if body.redirect_uri not in s.sso_redirect_uris_list:
        logger.warning(
            "Отклонён token exchange: redirect_uri не в whitelist: %r",
            body.redirect_uri,
        )
        raise BadRequestError("Недопустимый redirect_uri")
    try:
        oauth_client_id, client_secret = resolve_sso_credentials_for_redirect(body.redirect_uri, s)
    except SsoCredentialsNotFoundError:
        raise BadRequestError("Нет учётных данных SSO для этого redirect_uri; задайте пару в .env") from None
    try:
        raw = await exchange_authorization_code(
            settings=s,
            client_id=oauth_client_id,
            client_secret=client_secret,
            code=body.code,
            redirect_uri=body.redirect_uri,
            code_verifier=body.code_verifier,
            http_client=http_client,
        )
    except httpx.RequestError as exc:
        logger.warning("503: SSO token exchange недоступен: %s", exc)
        raise ServiceUnavailableError(_SSO_UNAVAILABLE) from exc
    if not raw or "access_token" not in raw:
        raise UnauthorizedError("Не удалось обменять код на токены")
    access, refresh, expires_in = _parse_token_grant(raw)

    try:
        gateway_payload = await fetch_user_info_from_gateway(settings=s, access_token=access, http_client=http_client)
    except httpx.RequestError as exc:
        logger.warning("503: SSO userinfo недоступен (после token exchange): %s", exc)
        raise ServiceUnavailableError(_SSO_UNAVAILABLE) from exc
    if not gateway_payload or not gateway_payload.get("sub"):
        raise UnauthorizedError("Не удалось получить профиль пользователя от SSO")
    user = await build_user_public(
        db,
        gateway_payload,
        groups_claim_path=s.sso_groups_claim,
    )
    ensure_portal_login_allowed(user, s)

    payload = TokenResponse(
        access_token=access,
        refresh_token=None,  # refresh передаётся через httpOnly cookie, не в теле
        expires_in=expires_in,
        oauth_client_id=oauth_client_id,
        user=user,
        redirect_after_login="/",
    )
    return _token_grant_response(payload, refresh=refresh, secure=not s.debug)


@router.post(
    "/refresh",
    summary="Обновление access token",
    response_model=RefreshTokenResponse,
)
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    http_client: HttpClient,
) -> JSONResponse:
    _require_sso()
    s = get_settings()
    rt = get_refresh_token_from_request(request, body.refresh_token)
    if not rt:
        raise UnauthorizedError("Refresh-токен не передан (ни в cookie 'rt', ни в теле запроса)")
    body_with_rt = body.model_copy(update={"refresh_token": rt})
    oauth_client_id, client_secret = _resolve_refresh_client_credentials(body_with_rt, s)
    try:
        raw = await refresh_access_token(
            settings=s,
            client_id=oauth_client_id,
            client_secret=client_secret,
            refresh_token=rt,
            http_client=http_client,
        )
    except httpx.RequestError as exc:
        logger.warning("503: SSO token refresh недоступен: %s", exc)
        raise ServiceUnavailableError(_SSO_UNAVAILABLE) from exc
    if not raw or "access_token" not in raw:
        raise UnauthorizedError("Не удалось обновить токен")
    access, new_refresh, expires_in = _parse_token_grant(raw)

    payload = RefreshTokenResponse(
        access_token=access,
        refresh_token=None,  # refresh передаётся через httpOnly cookie, не в теле
        expires_in=expires_in,
        oauth_client_id=oauth_client_id,
    )
    return _token_grant_response(payload, refresh=new_refresh, secure=not s.debug)
