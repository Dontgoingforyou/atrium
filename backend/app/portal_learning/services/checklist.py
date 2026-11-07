from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import UserChecklistStatus
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.optimistic_lock import compare_and_swap_row
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_learning import (
    PortalChecklist,
    PortalChecklistItem,
    PortalUserChecklist,
    PortalUserChecklistItem,
)
from app.portal_learning.schemas.checklist import ChecklistCreate, ChecklistUpdate, MarkItemBody
from app.portal_learning.services.material import _unique_known_idp_groups
from app.schemas.auth import UserPublic

_CHECKLIST_CAS_CONFLICT = "Чек-лист изменён другим пользователем"
_CHECKLIST_ROW_FIELDS = frozenset({"title", "description", "idp_group"})

_PROGRESS_OPTIONS = (
    selectinload(PortalUserChecklist.item_marks),
    selectinload(PortalUserChecklist.checklist).selectinload(PortalChecklist.items),
)


def _checklist_visible(checklist: PortalChecklist, user: UserPublic) -> bool:
    """Чек-лист виден, если idp_group пустой или входит в idp_groups из токена."""
    if user.is_portal_admin:
        return True
    if not checklist.idp_group:
        return True
    return checklist.idp_group in user.idp_groups


def _normalize_checklist_idp_group(idp_group: str) -> str:
    """Известная группа Keycloak или '' (для всех)."""
    known = _unique_known_idp_groups([idp_group]) if idp_group else []
    return known[0] if known else ""


async def list_checklists(
    session: AsyncSession,
    user: UserPublic,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[PortalChecklist]:
    """Список чек-листов, видимых пользователю."""
    stmt = (
        select(PortalChecklist).options(selectinload(PortalChecklist.items)).order_by(PortalChecklist.created_at.desc())
    )
    rows = list((await session.scalars(stmt)).all())
    visible = [r for r in rows if _checklist_visible(r, user)]
    return visible[offset : offset + limit]


async def get_checklist(
    session: AsyncSession,
    user: UserPublic,
    checklist_id: uuid.UUID,
) -> PortalChecklist:
    stmt = (
        select(PortalChecklist).where(PortalChecklist.id == checklist_id).options(selectinload(PortalChecklist.items))
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None or not _checklist_visible(row, user):
        raise NotFoundError("Чек-лист не найден")
    return row


async def create_checklist(
    session: AsyncSession,
    user: UserPublic,
    data: ChecklistCreate,
) -> PortalChecklist:
    if not user.is_portal_admin:
        raise ForbiddenError("Создание чек-листов доступно только администраторам")
    checklist = PortalChecklist(
        title=data.title,
        description=data.description,
        idp_group=_normalize_checklist_idp_group(data.idp_group),
    )
    session.add(checklist)
    await session.flush()
    for idx, text in enumerate(data.items):
        item = PortalChecklistItem(checklist_id=checklist.id, order_index=idx, text=text)
        session.add(item)
    await session.commit()
    stmt = (
        select(PortalChecklist).where(PortalChecklist.id == checklist.id).options(selectinload(PortalChecklist.items))
    )
    return (await session.execute(stmt)).scalar_one()


async def _replace_checklist_items(session: AsyncSession, checklist: PortalChecklist, texts: list[str]) -> None:
    """Удаляет прогресс пользователей и пункты, затем создаёт новые пункты."""
    await session.execute(delete(PortalUserChecklist).where(PortalUserChecklist.checklist_id == checklist.id))
    for item in list(checklist.items):
        await session.delete(item)
    checklist.items.clear()
    await session.flush()
    for idx, text in enumerate(texts):
        checklist.items.append(PortalChecklistItem(order_index=idx, text=text))


async def update_checklist(
    session: AsyncSession,
    user: UserPublic,
    checklist_id: uuid.UUID,
    data: ChecklistUpdate,
) -> PortalChecklist:
    if not user.is_portal_admin:
        raise ForbiddenError("Редактирование чек-листов доступно только администраторам")
    stmt = (
        select(PortalChecklist).where(PortalChecklist.id == checklist_id).options(selectinload(PortalChecklist.items))
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Чек-лист не найден")
    patch = data.model_dump(exclude_unset=True)
    patch.pop("expected_version", None)
    replace_items = patch.pop("items", None)
    if "idp_group" in patch:
        patch["idp_group"] = _normalize_checklist_idp_group(patch["idp_group"] or "")
    has_row_changes = bool(_CHECKLIST_ROW_FIELDS.intersection(patch))
    if not has_row_changes and replace_items is None:
        return row

    values: dict[str, Any] = {"updated_at": _now_utc()}
    if data.title is not None:
        values["title"] = data.title
    if "description" in patch:
        values["description"] = patch["description"]
    if "idp_group" in patch:
        values["idp_group"] = patch["idp_group"]

    new_version = await compare_and_swap_row(
        session,
        PortalChecklist,
        entity_id=checklist_id,
        expected_version=data.expected_version,
        values=values,
        conflict_message=_CHECKLIST_CAS_CONFLICT,
    )
    await session.refresh(row)
    row.version = new_version

    if replace_items is not None:
        await _replace_checklist_items(session, row, replace_items)
    await session.commit()
    session.expire(row, ["items"])
    stmt_reload = (
        select(PortalChecklist).where(PortalChecklist.id == checklist_id).options(selectinload(PortalChecklist.items))
    )
    return (await session.execute(stmt_reload)).scalar_one()


async def delete_checklist(session: AsyncSession, user: UserPublic, checklist_id: uuid.UUID) -> None:
    if not user.is_portal_admin:
        raise ForbiddenError("Удаление чек-листов доступно только администраторам")
    exists = await session.get(PortalChecklist, checklist_id)
    if exists is None:
        raise NotFoundError("Чек-лист не найден")
    # Явный SQL: shared test-session + noload иначе ORM пытается SET checklist_id=NULL.
    uc_ids = (
        (await session.execute(select(PortalUserChecklist.id).where(PortalUserChecklist.checklist_id == checklist_id)))
        .scalars()
        .all()
    )
    if uc_ids:
        await session.execute(
            delete(PortalUserChecklistItem).where(PortalUserChecklistItem.user_checklist_id.in_(uc_ids))
        )
    await session.execute(delete(PortalUserChecklist).where(PortalUserChecklist.checklist_id == checklist_id))
    await session.execute(delete(PortalChecklistItem).where(PortalChecklistItem.checklist_id == checklist_id))
    await session.execute(delete(PortalChecklist).where(PortalChecklist.id == checklist_id))
    await session.commit()
    session.expire_all()


async def start_checklist(
    session: AsyncSession,
    user: UserPublic,
    checklist_id: uuid.UUID,
) -> PortalUserChecklist:
    """Начать прохождение чек-листа. Если уже начато — возвращает текущий прогресс."""
    stmt_cl = (
        select(PortalChecklist).where(PortalChecklist.id == checklist_id).options(selectinload(PortalChecklist.items))
    )
    checklist = (await session.execute(stmt_cl)).scalar_one_or_none()
    if checklist is None or not _checklist_visible(checklist, user):
        raise NotFoundError("Чек-лист не найден")

    stmt_uc = (
        select(PortalUserChecklist)
        .where(
            PortalUserChecklist.user_sub == user.sub,
            PortalUserChecklist.checklist_id == checklist_id,
        )
        .options(*_PROGRESS_OPTIONS)
    )
    existing = (await session.execute(stmt_uc)).scalar_one_or_none()
    if existing is not None:
        return existing

    uc = PortalUserChecklist(
        user_sub=user.sub,
        checklist_id=checklist_id,
        status=UserChecklistStatus.IN_PROGRESS.value,
    )
    try:
        session.add(uc)
        await session.flush()
        for item in checklist.items:
            session.add(PortalUserChecklistItem(user_checklist_id=uc.id, item_id=item.id, is_done=False))
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raced = (await session.execute(stmt_uc)).scalar_one_or_none()
        if raced is not None:
            return raced
        raise

    stmt_result = select(PortalUserChecklist).where(PortalUserChecklist.id == uc.id).options(*_PROGRESS_OPTIONS)
    return (await session.execute(stmt_result)).scalar_one()


async def get_my_progress(
    session: AsyncSession,
    user: UserPublic,
    checklist_id: uuid.UUID,
) -> PortalUserChecklist:
    stmt = (
        select(PortalUserChecklist)
        .where(
            PortalUserChecklist.user_sub == user.sub,
            PortalUserChecklist.checklist_id == checklist_id,
        )
        .options(*_PROGRESS_OPTIONS)
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Прохождение не найдено. Сначала начните чек-лист.")
    if not _checklist_visible(row.checklist, user):
        raise NotFoundError("Чек-лист не найден")
    return row


async def mark_item(
    session: AsyncSession,
    user: UserPublic,
    checklist_id: uuid.UUID,
    item_id: uuid.UUID,
    body: MarkItemBody,
) -> PortalUserChecklist:
    """Отметить пункт чек-листа как выполненный / не выполненный."""
    stmt_uc = (
        select(PortalUserChecklist)
        .where(
            PortalUserChecklist.user_sub == user.sub,
            PortalUserChecklist.checklist_id == checklist_id,
        )
        .options(*_PROGRESS_OPTIONS)
    )
    uc = (await session.execute(stmt_uc)).scalar_one_or_none()
    if uc is None:
        raise NotFoundError("Прохождение не найдено. Сначала начните чек-лист.")
    if not _checklist_visible(uc.checklist, user):
        raise NotFoundError("Чек-лист не найден")

    item_row = await session.get(PortalChecklistItem, item_id)
    if item_row is None or item_row.checklist_id != checklist_id:
        raise NotFoundError("Пункт чек-листа не найден")

    stmt_mark = select(PortalUserChecklistItem).where(
        PortalUserChecklistItem.user_checklist_id == uc.id,
        PortalUserChecklistItem.item_id == item_id,
    )
    mark = (await session.execute(stmt_mark)).scalar_one_or_none()
    if mark is None:
        mark = PortalUserChecklistItem(user_checklist_id=uc.id, item_id=item_id, is_done=False)
        session.add(mark)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            uc = (await session.execute(stmt_uc)).scalar_one()
            mark = (
                await session.execute(
                    select(PortalUserChecklistItem).where(
                        PortalUserChecklistItem.user_checklist_id == uc.id,
                        PortalUserChecklistItem.item_id == item_id,
                    )
                )
            ).scalar_one()

    mark.is_done = body.is_done
    mark.done_at = _now_utc() if body.is_done else None

    all_marks = [m for m in uc.item_marks if m.id != mark.id] + [mark]
    total_items = len(uc.checklist.items)
    done_count = sum(1 for m in all_marks if m.is_done)
    if total_items > 0 and done_count == total_items:
        uc.status = UserChecklistStatus.COMPLETED.value
        uc.completed_at = _now_utc()
    else:
        uc.status = UserChecklistStatus.IN_PROGRESS.value
        uc.completed_at = None

    await session.commit()

    stmt_result = select(PortalUserChecklist).where(PortalUserChecklist.id == uc.id).options(*_PROGRESS_OPTIONS)
    return (await session.execute(stmt_result)).scalar_one()
