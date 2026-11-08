from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.optimistic_lock import compare_and_swap_row
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_link import PortalSpecialistLink
from app.infrastructure.db.models.portal_specialist_note import PortalSpecialistNote
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_specialists.constants import SPECIALIST_LINKS_LIST_CAP
from app.portal_specialists.schemas.specialist_detail import (
    SpecialistLinkCreate,
    SpecialistLinkRead,
    SpecialistProfileRead,
    SpecialistProfileUpdate,
)
from app.portal_specialists.services.board_realtime import publish_specialist_board_event
from app.portal_specialists.services.board_shared import (
    SPECIALIST_CARD_READ_FORBIDDEN,
    ensure_specialist_card_visible,
    require_specialist_write_access,
)
from app.portal_specialists.services.board_shared import (
    require_manager_or_admin as _require_manager_or_admin,
)
from app.portal_telegram.services.binding import delete_binding_for_user
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

_READ_FORBIDDEN_MESSAGE = SPECIALIST_CARD_READ_FORBIDDEN

# Обратная совместимость для тестов и импортов внутри модуля.
_require_write_access = require_specialist_write_access


# ---------------------------------------------------------------------------
# Профиль специалиста
# ---------------------------------------------------------------------------


async def _profile_to_read(
    *,
    specialist_sub: str,
    user_profile: PortalUserProfile,
    profile: PortalSpecialistProfile,
) -> SpecialistProfileRead:
    return SpecialistProfileRead(
        specialist_sub=specialist_sub,
        full_name=user_profile.full_name,
        email=user_profile.email,
        username=user_profile.username,
        birthdate=profile.birthdate,
        location=profile.location,
        telegram=profile.telegram,
        jira_issue_key=profile.jira_issue_key,
        direction_title=profile.direction,
        version=getattr(profile, "version", 1) or 1,
    )


async def get_specialist_profile(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
) -> SpecialistProfileRead:
    """Получить расширенный профиль без создания строки (чтение).

    Видны студенты (``portal_chat_allowed=False``) и специалисты, уже закреплённые
    на чьей-то доске. Возвращает Pydantic DTO: агрегат из двух таблиц.
    """
    _require_manager_or_admin(user, _READ_FORBIDDEN_MESSAGE)

    user_profile = await session.get(PortalUserProfile, specialist_sub)
    if user_profile is None:
        raise NotFoundError("Пользователь не найден")
    await ensure_specialist_card_visible(session, user_profile)

    profile = await session.get(PortalSpecialistProfile, specialist_sub)
    if profile is None:
        profile = PortalSpecialistProfile(specialist_sub=specialist_sub)

    return await _profile_to_read(
        specialist_sub=specialist_sub,
        user_profile=user_profile,
        profile=profile,
    )


async def get_or_create_specialist_profile(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
) -> SpecialistProfileRead:
    """Совместимое имя: только чтение, без insert (см. ``get_specialist_profile``)."""
    return await get_specialist_profile(session, user, specialist_sub)


async def update_specialist_profile(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
    data: SpecialistProfileUpdate,
) -> SpecialistProfileRead:
    """Обновить расширенный профиль специалиста."""
    await require_specialist_write_access(session, user, specialist_sub)

    user_profile = await session.get(PortalUserProfile, specialist_sub)
    if user_profile is None:
        raise NotFoundError("Пользователь не найден")

    profile = await session.get(PortalSpecialistProfile, specialist_sub)
    if profile is None:
        if data.expected_version != 1:
            raise ConflictError("Профиль специалиста изменён другим пользователем")
        profile = PortalSpecialistProfile(specialist_sub=specialist_sub, version=1)
        session.add(profile)
        await session.flush()

    updates = data.model_dump(exclude_unset=True)
    updates.pop("expected_version", None)
    if "birthdate" in updates or "telegram" in updates:
        raise ForbiddenError("Дата рождения и Telegram подтягиваются из профиля и здесь не редактируются")
    if "location" in updates and profile.jira_issue_key:
        raise ForbiddenError("Город синхронизируется из Jira — измените значение в Jira и нажмите «Обновить из Jira»")
    if not updates:
        return await _profile_to_read(
            specialist_sub=specialist_sub,
            user_profile=user_profile,
            profile=profile,
        )

    new_version = await compare_and_swap_row(
        session,
        PortalSpecialistProfile,
        entity_id=specialist_sub,
        expected_version=data.expected_version,
        values=updates,
        conflict_message="Профиль специалиста изменён другим пользователем",
        id_column_name="specialist_sub",
    )
    await session.refresh(profile)
    profile.version = new_version

    await session.commit()
    result = await _profile_to_read(
        specialist_sub=specialist_sub,
        user_profile=user_profile,
        profile=profile,
    )
    await publish_specialist_board_event(
        "specialist_profile_updated",
        specialist_sub=specialist_sub,
        actor_sub=user.sub,
    )
    return result


async def purge_specialist_from_portal(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
) -> list[uuid.UUID]:
    """Удалить данные специалиста из портала (профиль, доска, ссылки, заметки, Telegram-привязка).

    Учётная запись не затрагивается: при следующем входе профиль создаётся снова.
    Только администратор; нельзя удалить себя или пользователя с доступом к чатам портала.
    """
    if not user.is_portal_admin:
        logger.warning(
            "RBAC: удаление специалиста из портала отклонено user_sub=%s target=%s",
            user.sub,
            specialist_sub,
        )
        raise ForbiddenError("Удаление специалиста из портала — только для администратора")
    if user.sub == specialist_sub:
        raise ForbiddenError("Нельзя удалить собственный профиль")

    user_profile = await session.get(PortalUserProfile, specialist_sub)
    if user_profile is None:
        raise NotFoundError("Пользователь не найден")
    if user_profile.is_portal_admin:
        raise ForbiddenError("Нельзя удалить профиль администратора портала")
    if user_profile.portal_chat_allowed:
        raise ForbiddenError(
            "Нельзя удалить пользователя с доступом к чатам портала; допустимы только специалисты без чатов"
        )

    note_ids = list(
        (
            await session.scalars(
                select(PortalSpecialistNote.id).where(PortalSpecialistNote.specialist_sub == specialist_sub)
            )
        ).all()
    )
    await session.execute(
        delete(PortalManagerSpecialist).where(PortalManagerSpecialist.specialist_sub == specialist_sub)
    )
    await delete_binding_for_user(session, specialist_sub)
    await session.delete(user_profile)
    await session.commit()
    await publish_specialist_board_event(
        "specialist_purged",
        specialist_sub=specialist_sub,
        actor_sub=user.sub,
    )
    return note_ids


# ---------------------------------------------------------------------------
# Ссылки специалиста
# ---------------------------------------------------------------------------


async def list_specialist_links(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
) -> list[SpecialistLinkRead]:
    """Список ссылок специалиста."""
    _require_manager_or_admin(user, _READ_FORBIDDEN_MESSAGE)
    user_profile = await session.get(PortalUserProfile, specialist_sub)
    if user_profile is None:
        raise NotFoundError("Пользователь не найден")
    await ensure_specialist_card_visible(session, user_profile)

    stmt = (
        select(PortalSpecialistLink)
        .where(PortalSpecialistLink.specialist_sub == specialist_sub)
        .order_by(PortalSpecialistLink.created_at)
        .limit(SPECIALIST_LINKS_LIST_CAP)
    )
    links = list((await session.scalars(stmt)).all())
    return [SpecialistLinkRead.model_validate(link) for link in links]


async def create_specialist_link(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
    data: SpecialistLinkCreate,
) -> SpecialistLinkRead:
    """Добавить ссылку к профилю специалиста."""
    await require_specialist_write_access(session, user, specialist_sub)
    if await session.get(PortalUserProfile, specialist_sub) is None:
        raise NotFoundError("Пользователь не найден")

    link = PortalSpecialistLink(
        specialist_sub=specialist_sub,
        title=data.title,
        url=data.url,
        created_by_sub=user.sub,
    )
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return SpecialistLinkRead.model_validate(link)


async def delete_specialist_link(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
    link_id: uuid.UUID,
) -> None:
    """Удалить ссылку специалиста."""
    link = await session.get(PortalSpecialistLink, link_id)
    if link is None or link.specialist_sub != specialist_sub:
        raise NotFoundError("Ссылка не найдена")

    if not user.is_portal_admin and link.created_by_sub != user.sub:
        raise ForbiddenError("Удалять ссылку может только её автор или администратор")

    await session.delete(link)
    await session.commit()
