"""Сервис настроек аккаунта пользователя портала."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.core.permissions import is_timesheet_only
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.schemas.auth import UserPublic
from app.schemas.portal_account import PortalAccountPreferencesUpdate

logger = logging.getLogger(__name__)


async def get_profile(session: AsyncSession, sub: str) -> PortalUserProfile:
    """Вернуть профиль пользователя; 403 если профиль ещё не создан.

    Намеренно 403 (а не 404): наличие профиля — следствие успешной аутентификации,
    поэтому его отсутствие указывает на нештатную ситуацию, а не на «ресурс не найден».
    """
    profile = await session.get(PortalUserProfile, sub)
    if profile is None:
        logger.warning("Отказ в доступе: профиль не найден sub=%s", sub)
        raise ForbiddenError("Профиль пользователя не найден")
    return profile


async def update_account_preferences(
    session: AsyncSession,
    user: UserPublic,
    data: PortalAccountPreferencesUpdate,
) -> PortalUserProfile:
    """Обновить настройки аккаунта; возвращает обновлённый ORM-объект.

    Маппинг в Pydantic-схему выполняется в роутере.
    """
    if data.notify_document_trash is not None:
        if is_timesheet_only(user):
            logger.warning(
                "Отказ в доступе: user_sub=%s resource=account/notify_document_trash timesheet_only",
                user.sub,
            )
            raise ForbiddenError("Настройка уведомлений о корзине недоступна для вашей роли")
        if not user.is_portal_admin:
            logger.warning(
                "Отказ в доступе: user_sub=%s resource=account/notify_document_trash",
                user.sub,
            )
            raise ForbiddenError("Настройка уведомлений о корзине доступна только администраторам")
    profile = await get_profile(session, user.sub)
    changed = False
    if data.notify_document_trash is not None:
        profile.notify_document_trash = data.notify_document_trash
        changed = True
    if data.guided_tour_completed is not None:
        profile.guided_tour_completed = data.guided_tour_completed
        changed = True
    if changed:
        await session.commit()
        await session.refresh(profile)
    return profile
