from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.infrastructure.db.models.portal_document import PortalDocument, PortalDocumentShortcut
from app.portal_documents.constants import (
    DEVELOPER_DOCS_ROOT_ID,
    VIRTUAL_DEVELOPER_DOCS_ROOT_ID,
    VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG,
    VIRTUAL_DOCS_ROOT_ID,
    VIRTUAL_DOCS_ROOT_SLUG,
)
from app.portal_documents.services.portal_document_queries import document_subtree_ids
from app.portal_navigation.schemas.navigation import NavDocumentBrief, PortalNavNodeTree
from app.schemas.auth import UserPublic
from app.services import rbac

logger = logging.getLogger(__name__)

_MAX_NAV_TREE_DOCS = 2000


async def _load_doc_rows(
    session: AsyncSession,
    *,
    only_ids: set[uuid.UUID] | None = None,
) -> list[tuple[uuid.UUID, str, str | None, uuid.UUID | None]]:
    if only_ids is not None and not only_ids:
        return []
    stmt = (
        select(
            PortalDocument.id,
            PortalDocument.title,
            PortalDocument.icon_emoji,
            PortalDocument.parent_document_id,
        )
        .where(PortalDocument.deleted_at.is_(None))
        .order_by(
            PortalDocument.sort_order.asc(),
            PortalDocument.created_at.desc(),
            PortalDocument.id.asc(),
        )
        .limit(_MAX_NAV_TREE_DOCS)
    )
    if only_ids is not None:
        stmt = stmt.where(PortalDocument.id.in_(only_ids))
    result = await session.execute(stmt)
    rows = [
        (doc_id, title, icon_emoji, parent_document_id)
        for doc_id, title, icon_emoji, parent_document_id in result.all()
    ]
    if len(rows) >= _MAX_NAV_TREE_DOCS:
        logger.warning(
            "Дерево навигации обрезано по потолку %s документов",
            _MAX_NAV_TREE_DOCS,
        )
    return rows


def _assemble_tree(
    rows: list[tuple[uuid.UUID, str, str | None, uuid.UUID | None]],
    *,
    treat_parent_as_root: uuid.UUID | None = None,
) -> list[NavDocumentBrief]:
    """Собрать дерево; ``treat_parent_as_root`` — дети этого id считаются верхним уровнем секции."""
    if not rows:
        return []

    briefs: dict[uuid.UUID, NavDocumentBrief] = {
        doc_id: NavDocumentBrief(id=doc_id, title=title, icon_emoji=icon_e) for doc_id, title, icon_e, _ in rows
    }
    roots: list[NavDocumentBrief] = []
    parent_by_id = {r[0]: r[3] for r in rows}
    for doc_id, _title, _icon_e, parent_doc_id in rows:
        if parent_doc_id == treat_parent_as_root:
            roots.append(briefs[doc_id])
            continue
        if parent_doc_id is None or parent_doc_id not in briefs:
            roots.append(briefs[doc_id])
            continue
        if _would_create_nav_cycle(doc_id, parent_doc_id, parent_by_id):
            logger.warning(
                "Цикл parent_document_id в дереве навигации: doc_id=%s parent_id=%s",
                doc_id,
                parent_doc_id,
            )
            roots.append(briefs[doc_id])
            continue
        briefs[parent_doc_id].children.append(briefs[doc_id])
    return roots


def _would_create_nav_cycle(
    doc_id: uuid.UUID,
    parent_doc_id: uuid.UUID,
    parent_by_id: dict[uuid.UUID, uuid.UUID | None],
) -> bool:
    """Проверка цикла parent_document_id при сборке дерева меню."""
    seen: set[uuid.UUID] = {doc_id}
    current: uuid.UUID | None = parent_doc_id
    while current is not None:
        if current in seen:
            return True
        seen.add(current)
        current = parent_by_id.get(current)
    return False


def _index_nav_briefs(roots: list[NavDocumentBrief]) -> dict[uuid.UUID, NavDocumentBrief]:
    indexed: dict[uuid.UUID, NavDocumentBrief] = {}
    stack = list(roots)
    while stack:
        brief = stack.pop()
        indexed[brief.id] = brief
        stack.extend(brief.children)
    return indexed


async def _attach_shortcuts(
    session: AsyncSession,
    roots: list[NavDocumentBrief],
    *,
    meta_by_id: dict[uuid.UUID, tuple[str, str | None]],
) -> None:
    """Прикрепить ярлыки одним batch-запросом; target вне видимого набора пропускается."""
    if not roots:
        return
    briefs = _index_nav_briefs(roots)
    if not briefs:
        return
    visible_ids = set(briefs.keys())
    rows = (
        await session.execute(
            select(
                PortalDocumentShortcut.source_document_id,
                PortalDocumentShortcut.target_document_id,
            ).where(PortalDocumentShortcut.source_document_id.in_(visible_ids))
        )
    ).all()
    by_source: dict[uuid.UUID, list[uuid.UUID]] = {}
    for source_id, target_id in rows:
        if target_id not in visible_ids or target_id == source_id:
            continue
        source_brief = briefs.get(source_id)
        if source_brief is None:
            continue
        child_ids = {c.id for c in source_brief.children}
        if target_id in child_ids:
            continue
        by_source.setdefault(source_id, []).append(target_id)

    for source_id, target_ids in by_source.items():
        source_brief = briefs[source_id]
        seen: set[uuid.UUID] = set()
        shortcuts: list[NavDocumentBrief] = []
        for target_id in target_ids:
            if target_id in seen:
                continue
            seen.add(target_id)
            title, icon = meta_by_id.get(target_id, ("Без названия", None))
            shortcuts.append(
                NavDocumentBrief(
                    id=target_id,
                    title=title,
                    icon_emoji=icon,
                    children=[],
                    shortcuts=[],
                )
            )
        source_brief.shortcuts = shortcuts


async def _build_general_docs_tree(
    session: AsyncSession,
    rows: list[tuple[uuid.UUID, str, str | None, uuid.UUID | None]] | None = None,
    *,
    developer_subtree: set[uuid.UUID] | None = None,
) -> list[NavDocumentBrief]:
    """Корневые документы вне раздела «Документы для разработчиков»."""
    loaded = rows if rows is not None else await _load_doc_rows(session)
    excluded = (
        developer_subtree
        if developer_subtree is not None
        else set(await document_subtree_ids(session, DEVELOPER_DOCS_ROOT_ID, include_deleted=True))
    )
    filtered = [r for r in loaded if r[0] not in excluded]
    return _assemble_tree(filtered)


async def _build_developer_docs_tree(
    session: AsyncSession,
    rows: list[tuple[uuid.UUID, str, str | None, uuid.UUID | None]] | None = None,
    *,
    developer_subtree: set[uuid.UUID] | None = None,
) -> list[NavDocumentBrief]:
    """Документы секции: прямые потомки контейнера DEVELOPER_DOCS_ROOT как верхний уровень."""
    loaded = rows if rows is not None else await _load_doc_rows(session)
    allowed = (
        developer_subtree
        if developer_subtree is not None
        else set(await document_subtree_ids(session, DEVELOPER_DOCS_ROOT_ID, include_deleted=True))
    )
    filtered = [r for r in loaded if r[0] in allowed and r[0] != DEVELOPER_DOCS_ROOT_ID]
    return _assemble_tree(filtered, treat_parent_as_root=DEVELOPER_DOCS_ROOT_ID)


def _section_node(
    *,
    node_id: uuid.UUID,
    slug: str,
    title: str,
    sort_order: int,
    documents: list[NavDocumentBrief],
) -> PortalNavNodeTree:
    return PortalNavNodeTree(
        id=node_id,
        slug=slug,
        title=title,
        sort_order=sort_order,
        document_count_subtree=len(documents),
        documents=documents,
        children=[],
    )


def _doc_meta_by_id(
    rows: list[tuple[uuid.UUID, str, str | None, uuid.UUID | None]],
) -> dict[uuid.UUID, tuple[str, str | None]]:
    return {doc_id: (title, icon) for doc_id, title, icon, _ in rows}


async def get_navigation_tree(
    session: AsyncSession,
    *,
    user: UserPublic | None = None,
) -> list[PortalNavNodeTree]:
    """Два виртуальных раздела для полного доступа; для АУ — только developer-docs.

    Возвращает Pydantic-схему напрямую: единого ORM-объекта для дерева нет — это агрегат
    строк ``PortalDocument`` под двумя виртуальными корнями, не сущность БД (см. services.mdc).
    """
    if user is None:
        return []

    if rbac.user_can_access_documents(user):
        rows = await _load_doc_rows(session)
        meta = _doc_meta_by_id(rows)
        # include_deleted: корзина корня не должна выталкивать живых детей в «Документы».
        developer_subtree = set(await document_subtree_ids(session, DEVELOPER_DOCS_ROOT_ID, include_deleted=True))
        general = await _build_general_docs_tree(session, rows, developer_subtree=developer_subtree)
        developer = await _build_developer_docs_tree(session, rows, developer_subtree=developer_subtree)
        await _attach_shortcuts(session, [*general, *developer], meta_by_id=meta)
        return [
            _section_node(
                node_id=VIRTUAL_DOCS_ROOT_ID,
                slug=VIRTUAL_DOCS_ROOT_SLUG,
                title="Документы",
                sort_order=0,
                documents=general,
            ),
            _section_node(
                node_id=VIRTUAL_DEVELOPER_DOCS_ROOT_ID,
                slug=VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG,
                title="Документы для разработчиков",
                sort_order=10,
                documents=developer,
            ),
        ]

    if rbac.user_can_access_developer_docs(user):
        developer_subtree = set(await document_subtree_ids(session, DEVELOPER_DOCS_ROOT_ID, include_deleted=True))
        rows = await _load_doc_rows(session, only_ids=developer_subtree)
        meta = _doc_meta_by_id(rows)
        developer = await _build_developer_docs_tree(session, rows, developer_subtree=developer_subtree)
        await _attach_shortcuts(session, developer, meta_by_id=meta)
        return [
            _section_node(
                node_id=VIRTUAL_DEVELOPER_DOCS_ROOT_ID,
                slug=VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG,
                title="Документы для разработчиков",
                sort_order=0,
                documents=developer,
            ),
        ]

    logger.warning("Отказ в доступе к дереву навигации: user_sub=%s", user.sub)
    raise ForbiddenError("Нет доступа к документам")
