"""Подписанные URL прокси фото пользователя."""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.utils import hmac_secrets_equal
from app.integrations.profile_directory.username import username_from_email


def _signing_secret() -> bytes | None:
    """Ключ HMAC для photo URL: admin_session_secret или SSO client_secret.

    Без секрета возвращает ``None`` — предсказуемый fallback запрещён.
    """
    s = get_settings()
    raw = (s.admin_session_secret or s.sso_client_secret_prod or s.sso_client_secret or "").strip()
    return raw.encode() if raw else None


def build_user_photo_proxy_url(*, user_sub: str, email: str | None, version: int | None = None) -> str | None:
    """Относительный URL ``/api/v1/portal/users/{sub}/photo?exp&sig&v=`` или None."""
    settings = get_settings()
    if not settings.profile_directory_photos_enabled:
        return None
    if username_from_email(email) is None:
        return None
    if _signing_secret() is None:
        return None
    ttl = settings.user_photo_url_ttl_seconds
    exp = int(time.time()) + ttl
    sig = _sign(user_sub, exp)
    qs: dict[str, str] = {"exp": str(exp), "sig": sig}
    if version is not None:
        qs["v"] = str(version)
    return f"/api/v1/portal/users/{user_sub}/photo?{urlencode(qs)}"


def verify_user_photo_signature(*, user_sub: str, exp: int, sig: str) -> None:
    if _signing_secret() is None:
        raise ForbiddenError("Подпись ссылки на фото недоступна: не задан секрет")
    now = int(time.time())
    if exp < now:
        raise UnauthorizedError("Ссылка на фото истекла")
    expected = _sign(user_sub, exp)
    if not hmac_secrets_equal(sig, expected):
        raise ForbiddenError("Некорректная подпись ссылки на фото")


def _sign(user_sub: str, exp: int) -> str:
    secret = _signing_secret()
    if secret is None:
        raise ForbiddenError("Подпись ссылки на фото недоступна: не задан секрет")
    msg = f"{user_sub}:{exp}".encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()
