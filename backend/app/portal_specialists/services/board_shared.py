"""Общие хелперы доски специалистов (RBAC, маппинг строки JOIN → DTO)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import is_manager_or_admin
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_specialists.schemas.board import ManagerSpecialistEntryRead
from app.schemas.auth import UserPublic
from app.services.user_photo_url import build_user_photo_proxy_url

logger = logging.getLogger(__name__)

_DEFAULT_FORBIDDEN_MESSAGE = "Доступ к доске специалистов — только для менеджера или администратора портала"
_WRITE_FORBIDDEN_MESSAGE = "Редактировать карточку специалиста может только закреплённый менеджер или администратор"
SPECIALIST_CARD_READ_FORBIDDEN = "Доступ к карточке специалиста — только для менеджера или администратора"


def require_manager_or_admin(user: UserPublic, message: str | None = None) -> None:
    """Проверить, что пользователь — менеджер отдела (gid_number) или администратор портала.

    Единая точка входа для RBAC-проверки в модуле portal_specialists:
    не дублировать эту проверку локально в других сервисах модуля.
    """
    if is_manager_or_admin(user):
        return
    logger.warning(
        "RBAC: доступ к специалистам отклонён user_sub=%s roles=%s",
        user.sub,
        user.idp_groups,
    )
    raise ForbiddenError(message or _DEFAULT_FORBIDDEN_MESSAGE)


async def require_specialist_write_access(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
) -> None:
    """Право на запись: admin или менеджер отдела, закрепивший данного специалиста.

    Политика менеджера — ``is_manager_or_admin`` (``gid_number``), не группа Keycloak ``outstaff``.
    """
    if user.is_portal_admin:
        return
    if not is_manager_or_admin(user):
        logger.warning(
            "RBAC: запись в карточку специалиста отклонена user_sub=%s specialist_sub=%s",
            user.sub,
            specialist_sub,
        )
        raise ForbiddenError(_WRITE_FORBIDDEN_MESSAGE)
    stmt = select(PortalManagerSpecialist).where(
        PortalManagerSpecialist.manager_sub == user.sub,
        PortalManagerSpecialist.specialist_sub == specialist_sub,
    )
    entry = (await session.execute(stmt)).scalar_one_or_none()
    if entry is None:
        logger.warning(
            "RBAC: менеджер не закреплён за специалистом user_sub=%s specialist_sub=%s",
            user.sub,
            specialist_sub,
        )
        raise ForbiddenError(_WRITE_FORBIDDEN_MESSAGE)


async def ensure_specialist_card_visible(
    session: AsyncSession,
    user_profile: PortalUserProfile,
) -> None:
    """Карточка: студент (без чатов) или уже есть закрепление на чьей-то доске."""
    if not user_profile.portal_chat_allowed:
        return
    exists = await session.scalar(
        select(PortalManagerSpecialist.id).where(PortalManagerSpecialist.specialist_sub == user_profile.sub).limit(1),
    )
    if exists is None:
        raise NotFoundError("Пользователь не найден")


async def ensure_column_key_exists(session: AsyncSession, column_key: str) -> None:
    col_id = await session.scalar(
        select(PortalSpecialistColumn.id).where(PortalSpecialistColumn.key == column_key).limit(1),
    )
    if col_id is None:
        raise NotFoundError("Колонка воронки не найдена")


async def ensure_specialist_can_join_board(session: AsyncSession, specialist_sub: str) -> None:
    """На доску — существующий студент или уже закреплённый на чьей-то доске специалист."""
    profile = await session.get(PortalUserProfile, specialist_sub)
    if profile is None:
        raise NotFoundError("Пользователь не найден")
    if not profile.portal_chat_allowed:
        return
    exists = await session.scalar(
        select(PortalManagerSpecialist.id).where(PortalManagerSpecialist.specialist_sub == specialist_sub).limit(1),
    )
    if exists is None:
        raise ValidationError("На доску можно добавить только специалиста без доступа к чатам портала")


def build_entry_read(row: Any, _settings: Any | None = None) -> ManagerSpecialistEntryRead:
    """Собрать ManagerSpecialistEntryRead из строки JOIN-запроса."""
    avatar_url = build_user_photo_proxy_url(user_sub=row.specialist_sub, email=row.specialist_email)
    return ManagerSpecialistEntryRead(
        id=row.id,
        specialist_sub=row.specialist_sub,
        display_name=row.specialist_name,
        email=row.specialist_email,
        avatar_url=avatar_url,
        column_key=row.column_key,
        position=row.position,
        version=row.version,
        manager_sub=row.manager_sub,
        manager_display_name=row.manager_name,
        status_id=row.status_id,
        status_title=row.status_title,
        status_color=getattr(row, "status_color", None),
        created_at=row.created_at,
    )
