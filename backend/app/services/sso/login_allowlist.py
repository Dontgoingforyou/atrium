"""Белый список email для входа (пустой список — без ограничения)."""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.core.exceptions import ForbiddenError
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

_LOGIN_DENIED_MESSAGE = "Нет доступа"


def ensure_portal_login_allowed(user: UserPublic, settings: Settings) -> None:
    """Запретить вход, если задан allowlist и email пользователя в нём нет."""
    allowed = settings.portal_login_allowlist_emails
    if not allowed:
        return
    if user.email.strip().lower() in allowed:
        return
    logger.warning("Отказ в доступе: user_sub=%s resource=portal_login", user.sub)
    raise ForbiddenError(_LOGIN_DENIED_MESSAGE)
