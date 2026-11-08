from __future__ import annotations

import logging
from typing import Any, cast

import httpx

from app.core.auth_constants import normalize_sso_gid_number
from app.core.config import Settings
from app.core.utils import decode_jwt_payload_unverified

logger = logging.getLogger(__name__)


def decode_unverified_jwt_payload(token: str) -> dict[str, Any] | None:
    """Декодирует payload JWT без проверки подписи — обёртка над ``core.utils``."""
    return decode_jwt_payload_unverified(token)


def sso_error_log_detail(response: httpx.Response, *, limit: int = 200) -> str:
    """Краткое описание ошибки SSO без тела, в котором могли быть токены."""
    try:
        data = response.json()
    except Exception:
        return f"non-json ({len(response.content)} байт)"
    if not isinstance(data, dict):
        return "json без объекта ошибки"
    for key in ("error_description", "error", "message"):
        raw = data.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()[:limit]
    return "json без поля error"


def _sso_claim_as_str(raw: object) -> str | None:
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if raw is not None and not isinstance(raw, (dict, list)):
        as_str = str(raw).strip()
        if as_str:
            return as_str
    return None


def _looks_like_email(value: str) -> bool:
    return "@" in value and " " not in value


def resolve_sso_user_sub(data: dict[str, Any]) -> str:
    """
    Стабильный ID пользователя из ответа SSO.

    Предпочтительно ``public_id`` (ранее ``keycloak_id``) — UUID в SSO.
    Поле ``sub`` сейчас часто содержит email; email-подобные значения пропускаем,
    пока есть не-email идентификатор.
    """
    for key in ("public_id", "keycloak_id"):
        value = _sso_claim_as_str(data.get(key))
        if value:
            return value

    email_from_id_claims = ""
    for key in ("sub", "id", "user_id"):
        value = _sso_claim_as_str(data.get(key))
        if not value:
            continue
        if _looks_like_email(value):
            if not email_from_id_claims:
                email_from_id_claims = value.lower()
            continue
        return value

    if email_from_id_claims:
        return email_from_id_claims
    email = data.get("email")
    if isinstance(email, str) and email.strip():
        return email.strip().lower()
    return ""


def sso_user_to_gateway_payload(data: dict[str, Any]) -> dict[str, Any]:
    """SSO userinfo / login user → dict для build_user_public."""
    raw_position = data.get("position")
    position = raw_position.strip() if isinstance(raw_position, str) and raw_position.strip() else None
    return {
        "sub": resolve_sso_user_sub(data),
        "email": data.get("email") or "",
        "preferred_username": data.get("username") or data.get("preferred_username") or "",
        "name": data.get("full_name") or data.get("name") or "",
        "groups": data.get("groups") or [],
        "position": position,
        "gid_number": normalize_sso_gid_number(data.get("gid_number")),
        "telegram": data.get("telegram"),
        "birthday": (
            data.get("birthday") or data.get("birthdate") or data.get("birth_date") or data.get("date_of_birth")
        ),
    }


async def resolve_gateway_payload_after_password_login(
    *,
    settings: Settings,
    login_response: dict[str, Any],
    access_token: str,
    http_client: httpx.AsyncClient,
) -> dict[str, Any] | None:
    """
    Собирает профиль после POST auth/login: inline user → JWT claims → GET auth/me.
    """
    inline_user = login_response.get("user")
    gateway_payload: dict[str, Any] | None = None
    if isinstance(inline_user, dict):
        gateway_payload = sso_user_to_gateway_payload(inline_user)

    if not (gateway_payload or {}).get("sub"):
        jwt_data = decode_unverified_jwt_payload(access_token)
        if jwt_data:
            merged: dict[str, Any] = {**jwt_data}
            if isinstance(inline_user, dict):
                merged.update(inline_user)
            gateway_payload = sso_user_to_gateway_payload(merged)

    if not (gateway_payload or {}).get("sub"):
        gateway_payload = await fetch_user_info_from_gateway(
            settings=settings,
            access_token=access_token,
            http_client=http_client,
        )

    if gateway_payload and gateway_payload.get("sub"):
        return gateway_payload
    return None


async def fetch_user_info_from_gateway(
    *,
    settings: Settings,
    access_token: str,
    http_client: httpx.AsyncClient,
) -> dict[str, Any] | None:
    """
    GET профиль пользователя через SSO-шлюз.
    Возвращает dict, совместимый с JWT payload для build_user_public,
    или None при ошибке.
    """
    url = settings.sso_userinfo_url()
    if not url:
        return None
    try:
        response = await http_client.get(url, headers={"Authorization": f"Bearer {access_token}"})
    except httpx.RequestError as exc:
        logger.warning("SSO userinfo: сетевой сбой %s: %s", type(exc).__name__, exc)
        raise
    if response.status_code != 200:
        logger.warning(
            "SSO userinfo вернул %s: %s",
            response.status_code,
            sso_error_log_detail(response),
        )
        return None
    data = cast(dict[str, Any], response.json())
    return sso_user_to_gateway_payload(data)


async def login_with_password(
    *,
    settings: Settings,
    email: str,
    password: str,
    http_client: httpx.AsyncClient,
    scope: str | None = None,
) -> tuple[int, dict[str, Any] | None]:
    """
    POST email+password на login endpoint SSO-шлюза.
    Возвращает (HTTP status, body) — body только при 200.
    """
    login_url = settings.sso_login_endpoint_url()
    payload: dict[str, Any] = {"email": email.strip(), "password": password}
    if scope:
        payload["scope"] = scope

    try:
        response = await http_client.post(
            login_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
    except httpx.RequestError as exc:
        logger.warning("SSO login: сетевой сбой %s: %s", type(exc).__name__, exc)
        raise

    if response.status_code == 401:
        logger.warning("SSO login: неверные учётные данные")
        return 401, None

    if response.status_code != 200:
        logger.warning(
            "SSO login вернул %s: %s",
            response.status_code,
            sso_error_log_detail(response, limit=300),
        )
        return response.status_code, None

    return 200, cast(dict[str, Any], response.json())


async def exchange_authorization_code(
    *,
    settings: Settings,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str | None,
    http_client: httpx.AsyncClient,
) -> dict[str, Any] | None:
    """POST authorization code на token endpoint SSO-шлюза."""
    token_url = settings.sso_token_endpoint_url()
    payload: dict[str, Any] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if code_verifier:
        payload["code_verifier"] = code_verifier

    response = await http_client.post(
        token_url,
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    if response.status_code != 200:
        logger.warning(
            "SSO token exchange вернул %s: %s",
            response.status_code,
            sso_error_log_detail(response, limit=300),
        )
        return None
    return cast(dict[str, Any], response.json())


async def refresh_access_token(
    *,
    settings: Settings,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    http_client: httpx.AsyncClient,
) -> dict[str, Any] | None:
    """POST refresh token на dedicated refresh endpoint SSO-шлюза."""
    refresh_url = settings.sso_refresh_endpoint_url()
    payload = {
        "refresh_token": refresh_token,
    }
    response = await http_client.post(
        refresh_url,
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    if response.status_code != 200:
        logger.warning(
            "SSO token refresh вернул %s: %s",
            response.status_code,
            sso_error_log_detail(response, limit=300),
        )
        return None
    return cast(dict[str, Any], response.json())


async def logout_via_sso(
    *,
    settings: Settings,
    access_token: str,
    http_client: httpx.AsyncClient,
) -> bool:
    """POST logout на SSO-шлюз: инвалидирует refresh_token на стороне IdP."""
    url = settings.sso_logout_endpoint_url()
    if not url:
        return False
    try:
        response = await http_client.post(url, headers={"Authorization": f"Bearer {access_token}"})
        if response.status_code == 200:
            logger.info("Успешный logout через SSO")
            return True
        logger.warning("SSO logout вернул %s: %s", response.status_code, sso_error_log_detail(response))
        return False
    except httpx.HTTPError as exc:
        logger.warning("Ошибка подключения к SSO при logout: %s", exc)
        return False
    except Exception:
        logger.exception("Неожиданная ошибка SSO при logout")
        return False
