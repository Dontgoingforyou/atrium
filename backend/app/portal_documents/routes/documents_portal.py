from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Query, UploadFile, status

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.api.deps_rbac import AccessibleDocument
from app.core.config import get_settings
from app.portal_collab.schemas.task import PortalTaskRead
from app.portal_collab.services import task as task_svc
from app.portal_documents.schemas.document import (
    DocumentBreadcrumbItem,
    PortalDocumentHistoryRead,
    PortalDocumentListItem,
    PortalDocumentRead,
    PortalDocumentRelatedRead,
    TourDemoDocumentEnsureRead,
)
from app.portal_documents.services import portal_document as svc
from app.portal_documents.services import tour_demo as tour_demo_svc
from app.schemas.pagination import PagedResponse
from app.schemas.rich_media import RichMediaRead
from app.services import rich_media as rich_media_svc
from app.services.file_upload_validation import open_upload_stream

portal_router = APIRouter(prefix="/portal", tags=["Документы"])


@portal_router.get(
    "/documents",
    summary="Список документов с фильтрами",
    response_model=PagedResponse[PortalDocumentListItem],
)
async def list_documents(
    user: CurrentUser,
    db: DbSession,
    tag_slug: str | None = Query(default=None),
    owner_sub: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> PagedResponse[PortalDocumentListItem]:
    document_ids = await svc.readable_document_ids_for_user(db, user)
    tag_slugs = [tag_slug] if tag_slug else None
    total = await svc.count_documents(
        db,
        tag_slugs=tag_slugs,
        owner_sub=owner_sub,
        document_ids=document_ids,
    )
    docs = await svc.list_documents(
        db,
        tag_slugs=tag_slugs,
        owner_sub=owner_sub,
        document_ids=document_ids,
        skip=skip,
        limit=limit,
    )
    items = [PortalDocumentListItem.model_validate(d) for d in docs]
    return PagedResponse(items=items, total=total, skip=skip, limit=limit)


@portal_router.post(
    "/documents/tour-demo/ensure",
    summary="Подготовить учебный документ guided tour",
    response_model=TourDemoDocumentEnsureRead,
)
async def ensure_tour_demo_document(
    user: CurrentUser,
    db: DbSession,
) -> TourDemoDocumentEnsureRead:
    doc, created = await tour_demo_svc.ensure_tour_demo_document(db, user)
    return TourDemoDocumentEnsureRead(id=doc.id, created=created)


@portal_router.delete(
    "/documents/tour-demo",
    summary="Удалить учебные документы guided tour текущего пользователя",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def purge_tour_demo_documents(
    user: CurrentUser,
    db: DbSession,
) -> None:
    await tour_demo_svc.purge_tour_demo_documents(db, user.sub)


@portal_router.get(
    "/documents/{document_id}",
    summary="Документ по ID",
)
async def get_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalDocumentRead:
    doc = await svc.ensure_user_can_read_document(db, user, document_id)
    chain = await svc.get_ancestor_titles_for_breadcrumb(db, doc)
    bc = [DocumentBreadcrumbItem(id=a, title=t) for a, t in chain]
    base = PortalDocumentRead.model_validate(doc)
    nav_slug = await svc.virtual_nav_slug_for_document(db, doc.id)
    return base.model_copy(update={"breadcrumb": bc, "nav_node_slug": nav_slug})


@portal_router.get(
    "/documents/{document_id}/related",
    summary="Связанные с документом задачи (чаты портала к документу не привязываются)",
)
async def get_document_related(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    task_skip: int = Query(default=0, ge=0),
    task_limit: int = Query(default=100, ge=1, le=500),
) -> PortalDocumentRelatedRead:
    await svc.ensure_user_can_read_document(db, user, document_id)
    tasks = await task_svc.list_tasks(
        db,
        user,
        document_id=document_id,
        skip=task_skip,
        limit=task_limit,
    )
    return PortalDocumentRelatedRead(
        chats=[],
        tasks=[PortalTaskRead.model_validate(t) for t in tasks],
    )


@portal_router.post(
    "/documents/{document_id}/rich-media",
    summary="Загрузить изображение для тела документа",
    response_model=RichMediaRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_rich_media(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> RichMediaRead:
    """Загружает изображение; в HTML сохраняйте file_path из ответа."""
    async with open_upload_stream(file, get_settings().attachment_max_size_bytes) as (file_data, file_size):
        media = await rich_media_svc.upload_document_rich_media(
            db,
            user,
            document_id,
            file_data=file_data,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            original_filename=file.filename or "image",
        )
    return rich_media_svc.rich_media_to_read(media)


@portal_router.get(
    "/documents/{document_id}/history",
    summary="История изменений документа",
)
async def get_document_history(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PortalDocumentHistoryRead]:
    await svc.ensure_user_can_read_document(db, user, document_id)
    history = await svc.list_document_history(db, document_id, skip=skip, limit=limit)
    return [PortalDocumentHistoryRead.model_validate(h) for h in history]


@portal_router.get(
    "/documents/{document_id}/children",
    summary="Дочерние документы (вложенные под родителем)",
)
async def list_document_children(
    parent: AccessibleDocument,
    user: CurrentUser,
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PortalDocumentListItem]:
    docs = await svc.list_child_documents(
        db,
        parent_document_id=parent.id,
        _user=user,
        skip=skip,
        limit=limit,
    )
    return [PortalDocumentListItem.model_validate(d) for d in docs]
