"""Записи на доске воронки специалистов (чтение и мутации)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.optimistic_lock import compare_and_swap_row
from app.core.permissions import is_manager_or_admin
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_specialists.constants import SPECIALIST_BOARD_LIST_CAP
from app.portal_specialists.schemas.board import (
    ManagerSpecialistAdd,
    ManagerSpecialistEntryRead,
    ManagerSpecialistPatch,
    ManagerSpecialistReorder,
    SpecialistManagerRef,
)
from app.portal_specialists.services.board_realtime import publish_specialist_board_event
from app.portal_specialists.services.board_shared import (
    build_entry_read,
    ensure_column_key_exists,
    ensure_specialist_can_join_board,
    require_manager_or_admin,
)
from app.schemas.auth import UserPublic
from app.services.user_photo_url import build_user_photo_proxy_url

logger = logging.getLogger(__name__)


async def list_board_entries(
    session: AsyncSession,
    user: UserPublic,
    *,
    manager_sub: str | None = None,
    directory: bool = False,
) -> list[ManagerSpecialistEntryRead]:
    """Список специалистов на доске воронки.

    Менеджер видит только свою доску. Администратор без manager_sub видит все доски;
    с manager_sub — конкретную доску.

    ``directory=True`` — справочник «Все специалисты»: менеджер и админ видят все
    закрепления (только чтение; мутации по-прежнему только со своей доски).
    """
    require_manager_or_admin(user)

    effective_sub: str | None
    if user.is_portal_admin:
        effective_sub = manager_sub
    elif directory and is_manager_or_admin(user):
        effective_sub = manager_sub
    else:
        effective_sub = user.sub

    specialist_profile = aliased(PortalUserProfile)
    manager_profile = aliased(PortalUserProfile)
    spec_profile = aliased(PortalSpecialistProfile)

    stmt = (
        select(
            PortalManagerSpecialist.id,
            PortalManagerSpecialist.manager_sub,
            PortalManagerSpecialist.specialist_sub,
            PortalManagerSpecialist.column_key,
            PortalManagerSpecialist.position,
            PortalManagerSpecialist.version,
            PortalManagerSpecialist.status_id,
            PortalManagerSpecialist.created_at,
            specialist_profile.full_name.label("specialist_name"),
            specialist_profile.email.label("specialist_email"),
            manager_profile.full_name.label("manager_name"),
            spec_profile.direction.label("status_title"),
        )
        .outerjoin(specialist_profile, specialist_profile.sub == PortalManagerSpecialist.specialist_sub)
        .outerjoin(manager_profile, manager_profile.sub == PortalManagerSpecialist.manager_sub)
        .outerjoin(spec_profile, spec_profile.specialist_sub == PortalManagerSpecialist.specialist_sub)
        .order_by(PortalManagerSpecialist.column_key, PortalManagerSpecialist.position)
        .limit(SPECIALIST_BOARD_LIST_CAP)
    )
    if effective_sub is not None:
        stmt = stmt.where(PortalManagerSpecialist.manager_sub == effective_sub)

    rows = (await session.execute(stmt)).all()
    s = get_settings()
    return [build_entry_read(row, s) for row in rows]


async def add_to_board(
    session: AsyncSession,
    user: UserPublic,
    data: ManagerSpecialistAdd,
    *,
    target_manager_sub: str | None = None,
) -> PortalManagerSpecialist:
    """Добавить специалиста на доску воронки."""
    require_manager_or_admin(user)
    if user.is_portal_admin:
        effective_manager = target_manager_sub or user.sub
    else:
        if target_manager_sub is not None and target_manager_sub != user.sub:
            logger.warning(
                "IDOR: менеджер user_sub=%s пытался добавить на доску manager_sub=%s",
                user.sub,
                target_manager_sub,
            )
            raise ForbiddenError("Нельзя добавлять специалистов на чужую доску")
        effective_manager = user.sub
    await ensure_specialist_can_join_board(session, data.specialist_sub)
    await ensure_column_key_exists(session, data.column_key)
    entry = PortalManagerSpecialist(
        manager_sub=effective_manager,
        specialist_sub=data.specialist_sub,
        column_key=data.column_key,
    )
    session.add(entry)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError("Специалист уже добавлен на вашу доску") from e
    await session.refresh(entry)
    await publish_specialist_board_event(
        "board_entry_added",
        specialist_sub=entry.specialist_sub,
        manager_sub=entry.manager_sub,
        actor_sub=user.sub,
    )
    return entry


async def reassign_manager(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
    *,
    from_manager_sub: str,
    to_manager_sub: str,
) -> PortalManagerSpecialist:
    """Перенести закрепление специалиста с одного менеджера на другого (только admin)."""
    if not user.is_portal_admin:
        logger.warning(
            "RBAC: смена менеджера специалиста отклонена user_sub=%s specialist_sub=%s",
            user.sub,
            specialist_sub,
        )
        raise ForbiddenError("Смена менеджера — только для администратора портала")
    if from_manager_sub == to_manager_sub:
        raise ConflictError("Новый менеджер совпадает с текущим")

    stmt = select(PortalManagerSpecialist).where(
        PortalManagerSpecialist.specialist_sub == specialist_sub,
        PortalManagerSpecialist.manager_sub == from_manager_sub,
    )
    entry = (await session.execute(stmt)).scalar_one_or_none()
    if entry is None:
        raise NotFoundError("Закрепление специалиста у указанного менеджера не найдено")

    dup_stmt = select(PortalManagerSpecialist).where(
        PortalManagerSpecialist.specialist_sub == specialist_sub,
        PortalManagerSpecialist.manager_sub == to_manager_sub,
    )
    if (await session.execute(dup_stmt)).scalar_one_or_none() is not None:
        raise ConflictError("Специалист уже закреплён за выбранным менеджером")

    entry.manager_sub = to_manager_sub
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError("Не удалось сменить менеджера: конфликт закрепления") from e
    await session.refresh(entry)
    await publish_specialist_board_event(
        "board_manager_reassigned",
        specialist_sub=specialist_sub,
        manager_sub=to_manager_sub,
        actor_sub=user.sub,
        extra={"from_manager_sub": from_manager_sub},
    )
    return entry


async def move_on_board(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
    data: ManagerSpecialistPatch,
    *,
    target_manager_sub: str | None = None,
) -> PortalManagerSpecialist:
    """Переместить специалиста / сменить статус."""
    require_manager_or_admin(user)

    effective_manager = target_manager_sub if (user.is_portal_admin and target_manager_sub) else user.sub

    stmt = select(PortalManagerSpecialist).where(
        PortalManagerSpecialist.specialist_sub == specialist_sub,
        PortalManagerSpecialist.manager_sub == effective_manager,
    )
    entry = (await session.execute(stmt)).scalar_one_or_none()
    if entry is None:
        logger.warning(
            "IDOR/NotFound: user_sub=%s tried to move specialist_sub=%s on board manager_sub=%s",
            user.sub,
            specialist_sub,
            effective_manager,
        )
        raise NotFoundError("Запись специалиста на доске не найдена")

    values: dict[str, object] = {}
    if data.column_key is not None:
        await ensure_column_key_exists(session, data.column_key)
        values["column_key"] = data.column_key
    if data.position is not None:
        values["position"] = data.position

    if values:
        new_version = await compare_and_swap_row(
            session,
            PortalManagerSpecialist,
            entity_id=entry.id,
            expected_version=data.expected_version,
            values=values,
            conflict_message="Запись на доске изменена другим пользователем",
        )
        await session.commit()
        await session.refresh(entry)
        entry.version = new_version
        await publish_specialist_board_event(
            "board_entry_updated",
            specialist_sub=entry.specialist_sub,
            manager_sub=entry.manager_sub,
            actor_sub=user.sub,
        )
    return entry


def _resolve_reorder_insert_index(
    others: list[PortalManagerSpecialist],
    after_entry_id: uuid.UUID | None,
    before_entry_id: uuid.UUID | None,
) -> int:
    if after_entry_id is not None:
        idx = next((i for i, entry in enumerate(others) if entry.id == after_entry_id), None)
        return idx + 1 if idx is not None else len(others)
    if before_entry_id is not None:
        idx = next((i for i, entry in enumerate(others) if entry.id == before_entry_id), None)
        return idx if idx is not None else 0
    return 0


async def reorder_on_board(
    session: AsyncSession,
    user: UserPublic,
    data: ManagerSpecialistReorder,
    *,
    target_manager_sub: str | None = None,
) -> PortalManagerSpecialist:
    """Переместить запись по якорю внутри доски одного менеджера."""
    require_manager_or_admin(user)
    effective_manager = target_manager_sub if (user.is_portal_admin and target_manager_sub) else user.sub
    await ensure_column_key_exists(session, data.column_key)

    stmt = select(PortalManagerSpecialist).where(
        PortalManagerSpecialist.manager_sub == effective_manager,
        or_(
            PortalManagerSpecialist.column_key == data.column_key,
            PortalManagerSpecialist.id == data.entry_id,
        ),
    )
    if session.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    locked = list((await session.execute(stmt)).scalars().all())
    moving = next((entry for entry in locked if entry.id == data.entry_id), None)
    if moving is None:
        logger.warning(
            "IDOR/NotFound: user_sub=%s tried to reorder entry_id=%s on board manager_sub=%s",
            user.sub,
            data.entry_id,
            effective_manager,
        )
        raise NotFoundError("Запись специалиста на доске не найдена")

    others = [entry for entry in locked if entry.column_key == data.column_key and entry.id != data.entry_id]
    others.sort(key=lambda entry: (entry.position, entry.created_at, entry.id))
    insert_at = _resolve_reorder_insert_index(
        others,
        data.after_entry_id,
        data.before_entry_id,
    )
    others.insert(insert_at, moving)
    for position, entry in enumerate(others):
        entry.position = position
    moving.column_key = data.column_key

    await session.commit()
    await session.refresh(moving)
    await publish_specialist_board_event(
        "board_entry_updated",
        specialist_sub=moving.specialist_sub,
        manager_sub=moving.manager_sub,
        actor_sub=user.sub,
    )
    return moving


async def remove_from_board(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
    *,
    target_manager_sub: str | None = None,
) -> None:
    """Убрать специалиста с доски воронки."""
    require_manager_or_admin(user)

    effective_manager = target_manager_sub if (user.is_portal_admin and target_manager_sub) else user.sub

    stmt = select(PortalManagerSpecialist).where(
        PortalManagerSpecialist.specialist_sub == specialist_sub,
        PortalManagerSpecialist.manager_sub == effective_manager,
    )
    entry = (await session.execute(stmt)).scalar_one_or_none()
    if entry is None:
        logger.warning(
            "IDOR/NotFound: user_sub=%s tried to remove specialist_sub=%s from board manager_sub=%s",
            user.sub,
            specialist_sub,
            effective_manager,
        )
        raise NotFoundError("Запись специалиста на доске не найдена")

    await session.delete(entry)
    await session.commit()
    await publish_specialist_board_event(
        "board_entry_removed",
        specialist_sub=specialist_sub,
        manager_sub=effective_manager,
        actor_sub=user.sub,
    )


async def list_managers_for_specialist(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
) -> list[SpecialistManagerRef]:
    """Список менеджеров, за которыми закреплён специалист (только portal_admin)."""
    if not user.is_portal_admin:
        logger.warning(
            "Отказ в доступе: user_sub=%s resource=board/by-specialist specialist=%s",
            user.sub,
            specialist_sub,
        )
        raise ForbiddenError("Просмотр менеджеров специалиста — только для администратора портала")

    manager_profile = aliased(PortalUserProfile)
    spec_profile = aliased(PortalSpecialistProfile)

    stmt = (
        select(
            PortalManagerSpecialist.specialist_sub,
            PortalManagerSpecialist.manager_sub,
            PortalManagerSpecialist.column_key,
            PortalManagerSpecialist.status_id,
            PortalManagerSpecialist.created_at,
            manager_profile.full_name.label("manager_name"),
            manager_profile.email.label("manager_email"),
            spec_profile.direction.label("status_title"),
        )
        .outerjoin(manager_profile, manager_profile.sub == PortalManagerSpecialist.manager_sub)
        .outerjoin(spec_profile, spec_profile.specialist_sub == PortalManagerSpecialist.specialist_sub)
        .where(PortalManagerSpecialist.specialist_sub == specialist_sub)
        .order_by(PortalManagerSpecialist.created_at)
    )

    rows = (await session.execute(stmt)).all()
    out: list[SpecialistManagerRef] = []
    for row in rows:
        manager_avatar_url = build_user_photo_proxy_url(user_sub=row.manager_sub, email=row.manager_email)
        out.append(
            SpecialistManagerRef(
                manager_sub=row.manager_sub,
                manager_display_name=row.manager_name,
                manager_avatar_url=manager_avatar_url,
                manager_avatar_focal_x=None,
                manager_avatar_focal_y=None,
                column_key=row.column_key,
                status_id=row.status_id,
                status_title=row.status_title,
                status_color=None,
                created_at=row.created_at,
            ),
        )
    return out
