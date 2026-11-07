from __future__ import annotations

import logging
import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.text_search import escape_ilike_pattern as _escape_ilike_pattern
from app.infrastructure.db.models.portal_document import (
    PortalDocument,
    PortalDocumentHistory,
)
from app.portal_documents.constants import (
    DEVELOPER_DOCS_ROOT_ID,
    VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG,
    VIRTUAL_DOCS_ROOT_SLUG,
)
from app.portal_search.services.search_filters import document_ids_for_tag_slugs_subquery
from app.schemas.auth import UserPublic
from app.services import rbac

logger = logging.getLogger(__name__)


async def document_subtree_ids(
    session: AsyncSession,
    root_id: uuid.UUID,
    *,
    include_deleted: bool = False,
) -> list[uuid.UUID]:
    """Корень и все потомки по ``parent_document_id`` — один рекурсивный CTE вместо O(уровни) запросов.

    По умолчанию исключает soft-deleted. Для корзины/purge передайте ``include_deleted=True``.
    """
    doc_table = PortalDocument.__table__
    base_conds: list[ColumnElement[bool]] = [doc_table.c.id == root_id]
    if not include_deleted:
        base_conds.append(doc_table.c.deleted_at.is_(None))
    base = sa.select(doc_table.c.id).where(*base_conds)
    cte = base.cte(name="subtree", recursive=True)
    rec_conds: list[ColumnElement[bool]] = [doc_table.c.parent_document_id == cte.c.id]
    if not include_deleted:
        rec_conds.append(doc_table.c.deleted_at.is_(None))
    rec = sa.select(doc_table.c.id).where(*rec_conds)
    cte = cte.union_all(rec)
    result = await session.execute(sa.select(cte.c.id))
    return [row.id for row in result.fetchall()]


async def is_document_in_developer_docs_subtree(session: AsyncSession, document_id: uuid.UUID) -> bool:
    """Документ — корень «Документы для разработчиков» или его потомок (только живые строки)."""
    if document_id == DEVELOPER_DOCS_ROOT_ID:
        return True
    doc_table = PortalDocument.__table__
    base = sa.select(doc_table.c.id, doc_table.c.parent_document_id).where(
        doc_table.c.id == document_id,
        doc_table.c.deleted_at.is_(None),
    )
    cte = base.cte(name="dev_docs_ancestors", recursive=True)
    rec = sa.select(doc_table.c.id, doc_table.c.parent_document_id).where(
        doc_table.c.id == cte.c.parent_document_id,
        doc_table.c.deleted_at.is_(None),
    )
    cte = cte.union_all(rec)
    found = await session.scalar(sa.select(sa.func.count()).select_from(cte).where(cte.c.id == DEVELOPER_DOCS_ROOT_ID))
    return bool(found)


async def assert_no_document_parent_cycle(
    session: AsyncSession,
    document_id: uuid.UUID,
    new_parent_id: uuid.UUID,
) -> None:
    """Нельзя сделать предком самого документа (цикл).

    Использует рекурсивный CTE для проверки за один запрос.
    """
    doc_table = PortalDocument.__table__
    base = sa.select(doc_table.c.id, doc_table.c.parent_document_id).where(
        doc_table.c.id == new_parent_id,
    )
    cte = base.cte(name="ancestors", recursive=True)
    rec = sa.select(doc_table.c.id, doc_table.c.parent_document_id).where(
        doc_table.c.id == cte.c.parent_document_id,
        doc_table.c.id != new_parent_id,
    )
    cte = cte.union_all(rec)
    found = await session.scalar(sa.select(sa.func.count()).select_from(cte).where(cte.c.id == document_id))
    if found:
        raise ConflictError("Некорректный родитель: получился цикл")


async def get_ancestor_titles_for_breadcrumb(
    session: AsyncSession,
    doc: PortalDocument,
) -> list[tuple[uuid.UUID, str]]:
    """Цепочка (id, title) от корневой страницы к прямому родителю (для крошек).

    Один рекурсивный CTE вместо O(глубина) последовательных SELECT.
    """
    if doc.parent_document_id is None:
        return []
    doc_table = PortalDocument.__table__
    base = sa.select(
        doc_table.c.id,
        doc_table.c.title,
        doc_table.c.parent_document_id,
        sa.literal(1).label("depth"),
    ).where(
        doc_table.c.id == doc.parent_document_id,
        doc_table.c.deleted_at.is_(None),
    )
    cte = base.cte(name="ancestors", recursive=True)
    rec = sa.select(
        doc_table.c.id,
        doc_table.c.title,
        doc_table.c.parent_document_id,
        (cte.c.depth + 1).label("depth"),
    ).where(
        doc_table.c.id == cte.c.parent_document_id,
        doc_table.c.deleted_at.is_(None),
    )
    cte = cte.union_all(rec)
    result = await session.execute(sa.select(cte.c.id, cte.c.title).order_by(cte.c.depth.desc()))
    return [(row.id, row.title) for row in result.fetchall()]


async def virtual_nav_slug_for_document(session: AsyncSession, document_id: uuid.UUID) -> str:
    """Виртуальный slug секции сайдбара для меню переноса и крошек."""
    if await is_document_in_developer_docs_subtree(session, document_id):
        return VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG
    return VIRTUAL_DOCS_ROOT_SLUG


async def get_document(
    session: AsyncSession,
    document_id: uuid.UUID,
    *,
    include_deleted: bool = False,
) -> PortalDocument:
    """Вернуть документ с тегами или поднять NotFoundError.

    По умолчанию не возвращает строки в корзине (``deleted_at`` задан).
    """
    stmt = select(PortalDocument).where(PortalDocument.id == document_id).options(selectinload(PortalDocument.tags))
    if not include_deleted:
        stmt = stmt.where(PortalDocument.deleted_at.is_(None))
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFoundError("Документ не найден")
    return doc


def _active_document_filter() -> ColumnElement[Any]:
    return PortalDocument.deleted_at.is_(None)


def _document_list_order() -> tuple[Any, Any, Any]:
    return (
        PortalDocument.sort_order.asc(),
        PortalDocument.created_at.desc(),
        PortalDocument.id.asc(),
    )


async def ensure_user_can_read_document(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
) -> PortalDocument:
    """Загрузить документ и проверить доступ (полный доступ или АУ + developer-docs)."""
    if rbac.user_can_access_documents(user):
        return await get_document(session, document_id)

    if rbac.user_can_access_developer_docs(user):
        doc = await get_document(session, document_id)
        if await is_document_in_developer_docs_subtree(session, doc.id):
            return doc
        logger.warning(
            "Отказ в доступе к документу вне developer-docs: user_sub=%s document_id=%s",
            user.sub,
            document_id,
        )
        raise ForbiddenError("Нет доступа к документам")

    logger.warning(
        "Отказ в доступе к документам (роль запрещена): user_sub=%s document_id=%s",
        user.sub,
        document_id,
    )
    raise ForbiddenError("Нет доступа к документам")


async def user_can_read_document(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
) -> bool:
    """Проверка доступа к документу без исключений (для уведомлений @ в комментариях)."""
    try:
        await ensure_user_can_read_document(session, user, document_id)
    except (NotFoundError, ForbiddenError):
        return False
    return True


async def developer_docs_readable_ids(session: AsyncSession) -> list[uuid.UUID]:
    """Id документов раздела «Документы для разработчиков» (корень + потомки)."""
    return await document_subtree_ids(session, DEVELOPER_DOCS_ROOT_ID)


async def readable_document_ids_for_user(
    session: AsyncSession,
    user: UserPublic,
) -> list[uuid.UUID] | None:
    """Allowlist id документов для list/search: ``None`` — все активные.

    Полный доступ — без сужения; timesheet-only — поддерево developer-docs;
    иначе ``ForbiddenError``.
    """
    if rbac.user_can_access_documents(user):
        return None
    if rbac.user_can_access_developer_docs(user):
        return await developer_docs_readable_ids(session)
    logger.warning(
        "Отказ в доступе к документам (роль запрещена): user_sub=%s",
        user.sub,
    )
    raise ForbiddenError("Нет доступа к документам")


def _apply_document_list_filters(
    stmt: sa.Select[tuple[PortalDocument]],
    *,
    tag_slugs: list[str] | None = None,
    owner_sub: str | None = None,
    document_ids: list[uuid.UUID] | None = None,
) -> sa.Select[tuple[PortalDocument]]:
    if document_ids is not None:
        stmt = stmt.where(PortalDocument.id.in_(document_ids))
    if owner_sub is not None:
        stmt = stmt.where(PortalDocument.owner_sub == owner_sub)
    if tag_slugs:
        stmt = stmt.where(PortalDocument.id.in_(document_ids_for_tag_slugs_subquery(tag_slugs)))
    return stmt


async def count_documents(
    session: AsyncSession,
    *,
    tag_slugs: list[str] | None = None,
    owner_sub: str | None = None,
    document_ids: list[uuid.UUID] | None = None,
) -> int:
    filtered = _apply_document_list_filters(
        select(PortalDocument).where(_active_document_filter()),
        tag_slugs=tag_slugs,
        owner_sub=owner_sub,
        document_ids=document_ids,
    )
    return int(await session.scalar(select(func.count()).select_from(filtered.subquery())) or 0)


async def list_documents(
    session: AsyncSession,
    *,
    tag_slugs: list[str] | None = None,
    owner_sub: str | None = None,
    document_ids: list[uuid.UUID] | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalDocument]:
    stmt = select(PortalDocument).options(selectinload(PortalDocument.tags)).where(_active_document_filter())
    stmt = _apply_document_list_filters(
        stmt,
        tag_slugs=tag_slugs,
        owner_sub=owner_sub,
        document_ids=document_ids,
    )

    stmt = stmt.order_by(*_document_list_order()).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def list_child_documents(
    session: AsyncSession,
    *,
    parent_document_id: uuid.UUID,
    _user: UserPublic,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalDocument]:
    """Список вложенных документов (дочерние по parent_document_id). Доступ к родителю — на стороне вызова (RBAC)."""
    stmt = (
        select(PortalDocument)
        .options(selectinload(PortalDocument.tags))
        .where(
            PortalDocument.parent_document_id == parent_document_id,
            _active_document_filter(),
        )
    )
    stmt = stmt.order_by(*_document_list_order()).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def search_documents(
    session: AsyncSession,
    q: str,
    *,
    tag_slugs: list[str] | None = None,
    document_ids: list[uuid.UUID] | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalDocument]:
    """Поиск по подстроке (без учёта регистра) в заголовке и теле."""
    stmt = select(PortalDocument).options(selectinload(PortalDocument.tags)).where(_active_document_filter())

    if document_ids is not None:
        stmt = stmt.where(PortalDocument.id.in_(document_ids))
    if tag_slugs:
        stmt = stmt.where(PortalDocument.id.in_(document_ids_for_tag_slugs_subquery(tag_slugs)))

    pl = f"%{_escape_ilike_pattern(q.lower())}%"
    stmt = stmt.where(
        or_(
            func.lower(PortalDocument.title).like(pl, escape="\\"),
            func.lower(PortalDocument.body).like(pl, escape="\\"),
        )
    )

    stmt = stmt.order_by(*_document_list_order()).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def batch_get_documents_light(
    session: AsyncSession,
    document_ids: list[uuid.UUID],
) -> list[PortalDocument]:
    """Загрузить документы по списку id без тегов и удалённых.

    Использует load_only для экономии трафика — возвращает только поля,
    нужные для генерации эмбеддингов (title, body, author_sub).
    """
    from sqlalchemy.orm import load_only  # noqa: PLC0415

    if not document_ids:
        return []
    stmt = (
        select(PortalDocument)
        .where(PortalDocument.id.in_(document_ids), _active_document_filter())
        .options(
            load_only(
                PortalDocument.id,
                PortalDocument.title,
                PortalDocument.body,
                PortalDocument.author_sub,
            )
        )
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def list_document_history(
    session: AsyncSession,
    document_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalDocumentHistory]:
    stmt = (
        select(PortalDocumentHistory)
        .where(PortalDocumentHistory.document_id == document_id)
        .order_by(PortalDocumentHistory.changed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
