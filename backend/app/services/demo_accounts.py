"""Локальные демо-учётки. Пароли публичные: это вход без SSO."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from app.core.auth_constants import IDP_GROUP_PORTAL_ADMIN, SSO_GID_OUTSTAFF
from app.core.config import Settings

DEMO_ISSUER = "atrium-demo"
DEMO_OAUTH_CLIENT_ID = "atrium-demo"
DEMO_GROUPS_CLAIM = "groups"
DEMO_ACCESS_TTL_SECONDS = 1800
DEMO_REFRESH_TTL_SECONDS = 14 * 24 * 3600
_LOCAL_DEMO_SECRET = "atrium-local-demo"


class DemoTokenInvalid(Exception):
    """Токен помечен как демо, но подпись или срок не сходятся."""


@dataclass(frozen=True, slots=True)
class DemoAccount:
    username: str
    password: str
    email: str
    full_name: str
    groups: tuple[str, ...]
    gid_number: str | None = None


DEMO_ACCOUNTS: tuple[DemoAccount, ...] = (
    DemoAccount(
        username="admin",
        password="demo-admin",
        email="demo-admin@example.com",
        full_name="Анна Иванова",
        groups=(IDP_GROUP_PORTAL_ADMIN,),
    ),
    DemoAccount(
        username="manager",
        password="demo-manager",
        email="demo-manager@example.com",
        full_name="Иван Петров",
        groups=(),
        gid_number=SSO_GID_OUTSTAFF,
    ),
    DemoAccount(
        username="user",
        password="demo-user",
        email="demo-user@example.com",
        full_name="Мария Соколова",
        groups=(),
    ),
)


def demo_signing_secret(settings: Settings) -> str:
    """Секрет подписи демо-токенов: cookie-секрет админки или локальный запасной."""
    secret = settings.admin_session_secret.strip()
    return secret or _LOCAL_DEMO_SECRET


def demo_login_known(login: str) -> bool:
    return _find_account(login) is not None


def authenticate_demo(login: str, password: str) -> DemoAccount | None:
    """Учётка при верном пароле. None — логин неизвестен или пароль не тот."""
    account = _find_account(login)
    if account is None:
        return None
    if hmac.compare_digest(account.password, password):
        return account
    return None


def issue_demo_tokens(account: DemoAccount, secret: str) -> tuple[str, str, int, dict[str, Any]]:
    """access, refresh, expires_in и claims профиля для сборки UserPublic."""
    now = int(time.time())
    claims = _profile_claims(account)
    access = _encode({**claims, "typ": "access", "iat": now, "exp": now + DEMO_ACCESS_TTL_SECONDS}, secret)
    refresh = _encode(
        {
            "iss": DEMO_ISSUER,
            "sub": claims["sub"],
            "typ": "refresh",
            "iat": now,
            "exp": now + DEMO_REFRESH_TTL_SECONDS,
        },
        secret,
    )
    return access, refresh, DEMO_ACCESS_TTL_SECONDS, claims


def read_demo_access_claims(token: str, secret: str) -> dict[str, Any] | None:
    """Claims профиля или None, если это не демо-токен. Битый демо-токен — DemoTokenInvalid."""
    payload = _read(token, secret, expected_typ="access")
    if payload is None:
        return None
    return _profile_claims_from_payload(payload)


def read_demo_refresh_account(token: str, secret: str) -> DemoAccount | None:
    payload = _read(token, secret, expected_typ="refresh")
    if payload is None:
        return None
    sub = str(payload.get("sub") or "")
    for account in DEMO_ACCOUNTS:
        if f"demo:{account.username}" == sub:
            return account
    raise DemoTokenInvalid


def _find_account(login: str) -> DemoAccount | None:
    key = login.strip().lower()
    if not key:
        return None
    for account in DEMO_ACCOUNTS:
        if key in {account.username, account.email.lower()}:
            return account
    return None


def _profile_claims(account: DemoAccount) -> dict[str, Any]:
    claims: dict[str, Any] = {
        "iss": DEMO_ISSUER,
        "sub": f"demo:{account.username}",
        "email": account.email,
        "preferred_username": account.username,
        "name": account.full_name,
        DEMO_GROUPS_CLAIM: list(account.groups),
    }
    if account.gid_number:
        claims["gid_number"] = account.gid_number
    return claims


def _profile_claims_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    claims: dict[str, Any] = {
        "sub": str(payload.get("sub") or ""),
        "email": str(payload.get("email") or ""),
        "preferred_username": str(payload.get("preferred_username") or ""),
        "name": str(payload.get("name") or ""),
        DEMO_GROUPS_CLAIM: payload.get(DEMO_GROUPS_CLAIM) or [],
    }
    gid = payload.get("gid_number")
    if gid:
        claims["gid_number"] = gid
    return claims


def _read(token: str, secret: str, *, expected_typ: str) -> dict[str, Any] | None:
    if _peek_issuer(token) != DEMO_ISSUER:
        return None
    payload = _decode_verified(token, secret)
    if payload.get("typ") != expected_typ:
        raise DemoTokenInvalid
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        raise DemoTokenInvalid
    return payload


def _peek_issuer(token: str) -> str | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        raw = json.loads(_b64decode(parts[1]))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    issuer = raw.get("iss")
    return issuer if isinstance(issuer, str) else None


def _encode(payload: dict[str, Any], secret: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode())
    signing = f"{header}.{body}"
    signature = _b64(hmac.new(secret.encode(), signing.encode(), hashlib.sha256).digest())
    return f"{signing}.{signature}"


def _decode_verified(token: str, secret: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise DemoTokenInvalid
    signing = f"{parts[0]}.{parts[1]}"
    expected = _b64(hmac.new(secret.encode(), signing.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, parts[2]):
        raise DemoTokenInvalid
    try:
        payload = json.loads(_b64decode(parts[1]))
    except (ValueError, json.JSONDecodeError) as exc:
        raise DemoTokenInvalid from exc
    if not isinstance(payload, dict):
        raise DemoTokenInvalid
    return payload


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)
