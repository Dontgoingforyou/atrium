from __future__ import annotations

import uuid
from typing import Any

from slugify import slugify
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.optimistic_lock import compare_and_swap_row
from app.infrastructure.db.models.portal_document import PortalDocumentTag, PortalTag
from app.infrastructure.db.models.portal_task import PortalTaskTag
from app.schemas.tags import PortalTagCreate, PortalTagUpdate

_DUP_NAME_MSG = "Тег с таким названием уже существует"
_IN_USE_MSG = "Тег используется и не может быть удалён"
_TAG_CAS_CONFLICT = "Тег изменён другим пользователем"


def _normalized_name_key(display_name: str) -> str:
    return display_name.strip().lower()


async def _ensure_name_available(
    session: AsyncSession,
    *,
    name_key: str,
    exclude_tag_id: uuid.UUID | None,
) -> None:
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        stmt = select(PortalTag.id).where(func.lower(func.trim(PortalTag.name)) == name_key)
        if exclude_tag_id is not None:
            stmt = stmt.where(PortalTag.id != exclude_tag_id)
        exists = (await session.execute(stmt.limit(1))).first()
        if exists is not None:
            raise ConflictError(_DUP_NAME_MSG)
        return
    # SQLite lower() — только ASCII; кириллицу сравниваем в Python (каталог тегов маленький).
    sqlite_stmt = select(PortalTag.id, PortalTag.name)
    if exclude_tag_id is not None:
        sqlite_stmt = sqlite_stmt.where(PortalTag.id != exclude_tag_id)
    rows = (await session.execute(sqlite_stmt)).all()
    if any(_normalized_name_key(name) == name_key for _tid, name in rows):
        raise ConflictError(_DUP_NAME_MSG)


async def _allocate_unique_slug(
    session: AsyncSession,
    *,
    display_name: str,
    exclude_tag_id: uuid.UUID | None,
) -> str:
    base = slugify(display_name, separator="-", lowercase=True) or "tag"
    idx = 0
    while idx < 2000:
        candidate = base if idx == 0 else f"{base}-{idx + 1}"
        conditions = [PortalTag.slug == candidate]
        if exclude_tag_id is not None:
            conditions.append(PortalTag.id != exclude_tag_id)
        row = await session.execute(select(PortalTag.id).where(*conditions).limit(1))
        if row.first() is None:
            return candidate
        idx += 1
    raise ConflictError(_DUP_NAME_MSG)


async def list_tags(session: AsyncSession, *, skip: int = 0, limit: int = 100) -> list[PortalTag]:
    stmt = select(PortalTag).order_by(PortalTag.name).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_tag(session: AsyncSession, data: PortalTagCreate) -> PortalTag:
    """Создаёт тег; имя уникально с точностью до lower(trim); slug выделяется без коллизий."""
    display = data.name.strip()
    key = _normalized_name_key(display)
    await _ensure_name_available(session, name_key=key, exclude_tag_id=None)
    slug = await _allocate_unique_slug(session, display_name=display, exclude_tag_id=None)
    tag = PortalTag(name=display, slug=slug, color=data.color)
    session.add(tag)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError(_DUP_NAME_MSG) from e
    await session.refresh(tag)
    return tag


async def update_tag(session: AsyncSession, tag_id: uuid.UUID, data: PortalTagUpdate) -> PortalTag:
    tag = await session.get(PortalTag, tag_id)
    if tag is None:
        raise NotFoundError("Тег не найден")

    values: dict[str, Any] = {}
    if data.name is not None:
        display = data.name.strip()
        key = _normalized_name_key(display)
        await _ensure_name_available(session, name_key=key, exclude_tag_id=tag.id)
        new_slug = await _allocate_unique_slug(session, display_name=display, exclude_tag_id=tag.id)
        values["name"] = display
        values["slug"] = new_slug
    if data.color is not None:
        values["color"] = data.color

    if not values:
        return tag

    try:
        new_version = await compare_and_swap_row(
            session,
            PortalTag,
            entity_id=tag_id,
            expected_version=data.expected_version,
            values=values,
            conflict_message=_TAG_CAS_CONFLICT,
        )
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError(_DUP_NAME_MSG) from e
    await session.refresh(tag)
    tag.version = new_version
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError(_DUP_NAME_MSG) from e
    return tag


async def delete_tag(session: AsyncSession, tag_id: uuid.UUID) -> None:
    tag = await session.get(PortalTag, tag_id)
    if tag is None:
        raise NotFoundError("Тег не найден")

    doc_links = await session.scalar(
        select(func.count()).select_from(PortalDocumentTag).where(PortalDocumentTag.tag_id == tag_id)
    )
    task_links = await session.scalar(
        select(func.count()).select_from(PortalTaskTag).where(PortalTaskTag.tag_id == tag_id)
    )
    if (doc_links or 0) > 0 or (task_links or 0) > 0:
        raise ConflictError(_IN_USE_MSG)

    await session.delete(tag)
    await session.commit()


async def replace_document_tags(
    session: AsyncSession,
    document_id: uuid.UUID,
    tag_ids: list[uuid.UUID],
) -> None:
    """Заменяет теги документа через прямую работу с join-таблицей (без lazy load)."""
    unique_ids = list(dict.fromkeys(tag_ids))
    if unique_ids:
        found = set(
            (await session.execute(select(PortalTag.id).where(PortalTag.id.in_(unique_ids)))).scalars().all(),
        )
        missing = [tid for tid in unique_ids if tid not in found]
        if missing:
            raise NotFoundError("Тег не найден")
    await session.execute(delete(PortalDocumentTag).where(PortalDocumentTag.document_id == document_id))
    for tag_id in unique_ids:
        session.add(PortalDocumentTag(document_id=document_id, tag_id=tag_id))


async def resolve_name_and_slug_for_admin_form(
    session: AsyncSession,
    *,
    raw_name: str,
    exclude_tag_id: uuid.UUID | None,
) -> tuple[str, str]:
    """Единые правила имени и slug для SQLAdmin (DRY с REST)."""
    display = raw_name.strip()
    if not display:
        return display, slugify("", separator="-", lowercase=True) or "tag"
    key = _normalized_name_key(display)
    await _ensure_name_available(session, name_key=key, exclude_tag_id=exclude_tag_id)
    slug = await _allocate_unique_slug(session, display_name=display, exclude_tag_id=exclude_tag_id)
    return display, slug
