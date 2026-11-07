"""Прокси байтов фото пользователя из Effective Admin."""

from __future__ import annotations

import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.integrations.effective_admin.client import EffectiveAdminPhotoClient, PhotoBytes
from app.integrations.effective_admin.username import username_from_email
from app.services.user_photo_url import verify_user_photo_signature

logger = logging.getLogger(__name__)


async def fetch_user_photo_for_proxy(
    session: AsyncSession,
    http: httpx.AsyncClient,
    *,
    user_sub: str,
    exp: int,
    sig: str,
    viewer_bearer: str | None = None,
    viewer_sub: str | None = None,
) -> PhotoBytes:
    """Тянет байты из EA.

    ``viewer_sub`` не используется для авторизации в EA (JWT ``sub`` часто email,
    а portal sub — ``public_id``). При наличии Bearer зрителя вызываем
    ``GET /users/{username}/photo`` — по контракту EA любой валидный SSO JWT.
    """
    _ = viewer_sub  # совместимость сигнатуры роутера
    verify_user_photo_signature(user_sub=user_sub, exp=exp, sig=sig)
    settings = get_settings()
    if not settings.effective_admin_photos_enabled:
        raise ServiceUnavailableError("Интеграция фото не настроена")

    profile = await session.get(PortalUserProfile, user_sub)
    if profile is None:
        raise NotFoundError("Пользователь не найден")
    username = username_from_email(profile.email)
    if username is None:
        raise NotFoundError("Фото недоступно: нет email")

    client = EffectiveAdminPhotoClient(settings, http)
    service = settings.effective_admin_service_token.strip()

    if viewer_bearer:
        try:
            return await client.get_user_photo(username=username, bearer_token=viewer_bearer)
        except NotFoundError:
            raise
        except ServiceUnavailableError:
            if not service:
                raise
            logger.info(
                "EA photo: JWT зрителя не принят, пробуем service token username=%s",
                username,
            )

    if service:
        return await client.get_user_photo(username=username, bearer_token=service)

    raise ServiceUnavailableError(
        "Задайте EFFECTIVE_ADMIN_SERVICE_TOKEN или откройте фото с Authorization Bearer",
    )
