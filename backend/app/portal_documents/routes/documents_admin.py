from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Query

from app.api.deps import DbSession
from app.api.deps_auth import PortalAdminUser, PortalManagerOrAdminUser
from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.schemas.document import (
    DocumentBreadcrumbItem,
    PortalDocumentCreate,
    PortalDocumentIdResponse,
    PortalDocumentQuickCreate,
    PortalDocumentRead,
    PortalDocumentReorderRequest,
    PortalDocumentTrashItem,
    PortalDocumentUpdate,
)
from app.portal_documents.services import portal_document as svc
from app.portal_search.services import embedding as emb_svc
from app.portal_search.services.entity_text import document_meta, document_to_text
from app.schemas.pagination import PagedResponse

admin_router = APIRouter(prefix="/admin", tags=["Администрирование"])


def _schedule_document_embedding(bg: BackgroundTasks, doc: PortalDocument) -> None:
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        "document",
        str(doc.id),
        document_to_text(doc.title, doc.body),
        document_meta(author_sub=doc.author_sub),
    )


async def _schedule_subtree_embeddings(bg: BackgroundTasks, db: DbSession, root_id: uuid.UUID) -> None:
    subtree_ids = await svc.document_subtree_ids(db, root_id)
    subtree_docs = await svc.batch_get_documents_light(db, subtree_ids)
    for row in subtree_docs:
        bg.add_task(
            emb_svc.upsert_embedding_bg,
            "document",
            str(row.id),
            document_to_text(row.title, row.body),
            document_meta(author_sub=row.author_sub),
        )


@admin_router.get(
    "/portal-documents/trash",
    summary="Корзина удалённых документов",
    response_model=PagedResponse[PortalDocumentTrashItem],
)
async def list_trash_documents(
    _user: PortalManagerOrAdminUser,
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> PagedResponse[PortalDocumentTrashItem]:
    total = await svc.count_trash_document_roots(db)
    rows = await svc.list_trash_document_roots(db, skip=skip, limit=limit)
    ttl = svc.DOCUMENT_TRASH_TTL_DAYS
    items = [PortalDocumentTrashItem.from_portal_row(r, ttl_days=ttl) for r in rows]
    return PagedResponse(items=items, total=total, skip=skip, limit=limit)


@admin_router.post(
    "/portal-documents",
    summary="Создать документ",
    status_code=201,
)
async def create_document(
    actor: PortalManagerOrAdminUser,
    db: DbSession,
    body: PortalDocumentCreate,
    bg: BackgroundTasks,
) -> PortalDocumentRead:
    doc = await svc.create_document(
        db,
        body,
        author_sub=actor.sub,
        author_display_name=actor.full_name,
        author_email=actor.email,
        author=actor,
    )
    _schedule_document_embedding(bg, doc)
    return PortalDocumentRead.model_validate(doc)


@admin_router.patch(
    "/portal-documents/{document_id}",
    summary="Обновить документ",
)
async def update_document(
    document_id: uuid.UUID,
    actor: PortalManagerOrAdminUser,
    db: DbSession,
    body: PortalDocumentUpdate,
    bg: BackgroundTasks,
) -> PortalDocumentRead:
    doc = await svc.update_document(
        db,
        document_id,
        body,
        changed_by_sub=actor.sub,
        changed_by_display_name=actor.full_name,
        changed_by_email=actor.email,
        changed_by=actor,
    )
    _schedule_document_embedding(bg, doc)
    return PortalDocumentRead.model_validate(doc)


@admin_router.patch(
    "/portal-documents/{document_id}/reorder",
    summary="Изменить порядок документа среди соседей",
)
async def reorder_portal_document(
    document_id: uuid.UUID,
    actor: PortalManagerOrAdminUser,
    db: DbSession,
    body: PortalDocumentReorderRequest,
) -> PortalDocumentRead:
    doc = await svc.reorder_document_among_siblings(
        db,
        document_id,
        before_id=body.before_id,
        after_id=body.after_id,
        changed_by_sub=actor.sub,
        changed_by_display_name=actor.full_name,
        changed_by_email=actor.email,
    )
    chain = await svc.get_ancestor_titles_for_breadcrumb(db, doc)
    bc = [DocumentBreadcrumbItem(id=a, title=t) for a, t in chain]
    base = PortalDocumentRead.model_validate(doc)
    nav_slug = await svc.virtual_nav_slug_for_document(db, doc.id)
    return base.model_copy(update={"breadcrumb": bc, "nav_node_slug": nav_slug})


@admin_router.post(
    "/portal-documents/{document_id}/restore",
    summary="Восстановить документ из корзины",
)
async def restore_portal_document(
    document_id: uuid.UUID,
    actor: PortalManagerOrAdminUser,
    db: DbSession,
    bg: BackgroundTasks,
) -> PortalDocumentRead:
    doc = await svc.restore_document(
        db,
        document_id,
        changed_by_sub=actor.sub,
        changed_by_display_name=actor.full_name,
        changed_by_email=actor.email,
    )
    await _schedule_subtree_embeddings(bg, db, doc.id)
    chain = await svc.get_ancestor_titles_for_breadcrumb(db, doc)
    bc = [DocumentBreadcrumbItem(id=a, title=t) for a, t in chain]
    base = PortalDocumentRead.model_validate(doc)
    nav_slug = await svc.virtual_nav_slug_for_document(db, doc.id)
    return base.model_copy(update={"breadcrumb": bc, "nav_node_slug": nav_slug})


@admin_router.post(
    "/portal-documents/{document_id}/duplicate",
    summary="Создать копию документа с поддеревом",
    status_code=201,
)
async def duplicate_portal_document(
    document_id: uuid.UUID,
    actor: PortalManagerOrAdminUser,
    db: DbSession,
    bg: BackgroundTasks,
) -> PortalDocumentIdResponse:
    doc = await svc.duplicate_document_subtree(
        db,
        document_id,
        author_sub=actor.sub,
        author_display_name=actor.full_name,
        author_email=actor.email,
        author=actor,
    )
    await _schedule_subtree_embeddings(bg, db, doc.id)
    return PortalDocumentIdResponse(id=doc.id)


@admin_router.delete(
    "/portal-documents/{document_id}/purge",
    summary="Удалить документ безвозвратно",
    description="Удаляет строку из БД, дочерние страницы и связанное избранное.",
    status_code=204,
)
async def purge_portal_document(
    document_id: uuid.UUID,
    _admin: PortalAdminUser,
    db: DbSession,
) -> None:
    await svc.permanently_purge_document(db, document_id)


@admin_router.delete(
    "/portal-documents/{document_id}",
    summary="Переместить документ в корзину",
    description=(
        "Помечает документ и поддерево как удалённые. Избранное скрывается в списке и возвращается при restore."
    ),
    status_code=204,
)
async def soft_delete_portal_document(
    document_id: uuid.UUID,
    actor: PortalManagerOrAdminUser,
    db: DbSession,
    bg: BackgroundTasks,
) -> None:
    tree_ids = await svc.soft_delete_document(
        db,
        document_id,
        deleted_by_sub=actor.sub,
        deleted_by_display_name=actor.full_name,
        deleted_by_email=actor.email,
    )
    for eid in tree_ids:
        bg.add_task(emb_svc.delete_embedding_bg, "document", str(eid))
    from app.portal_collab.services import notification as notification_svc

    bg.add_task(notification_svc.notify_document_trashed_bg, str(document_id), actor.sub)


@admin_router.post(
    "/portal-documents/quick-create",
    summary="Мгновенное создание документа (Notion-patтерn)",
    description=(
        "Создаёт документ с заголовком «Без названия», "
        "возвращает только его id. Фронтенд немедленно переходит на страницу "
        "нового документа, где заголовок автофокусирован для редактирования."
    ),
    status_code=201,
)
async def quick_create_document(
    actor: PortalManagerOrAdminUser,
    db: DbSession,
    body: PortalDocumentQuickCreate,
    bg: BackgroundTasks,
) -> PortalDocumentIdResponse:
    doc = await svc.create_document(
        db,
        PortalDocumentCreate(
            title="Без названия",
            parent_document_id=body.parent_document_id,
        ),
        author_sub=actor.sub,
        author_display_name=actor.full_name,
        author_email=actor.email,
        author=actor,
    )
    _schedule_document_embedding(bg, doc)
    return PortalDocumentIdResponse(id=doc.id)
