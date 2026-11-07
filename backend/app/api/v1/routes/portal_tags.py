from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser, PortalManagerOrAdminUser
from app.schemas.tags import PortalTagCreate, PortalTagRead, PortalTagUpdate
from app.services import portal_tags as tags_svc

router = APIRouter(prefix="/portal", tags=["Теги"])


@router.get(
    "/tags",
    summary="Список тегов",
)
async def list_tags(
    _user: CurrentUser,
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PortalTagRead]:
    # Без PagedResponse: теги документов —
    # заведомо ограниченный набор (≤ 100 в организации), а не растущая со временем лента.
    tags = await tags_svc.list_tags(db, skip=skip, limit=limit)
    return [PortalTagRead.model_validate(t) for t in tags]


@router.post(
    "/tags",
    summary="Создать тег",
    status_code=201,
)
async def create_tag(
    _user: PortalManagerOrAdminUser,
    db: DbSession,
    body: PortalTagCreate,
) -> PortalTagRead:
    tag = await tags_svc.create_tag(db, body)
    return PortalTagRead.model_validate(tag)


@router.patch(
    "/tags/{tag_id}",
    summary="Обновить тег",
)
async def update_tag(
    _user: PortalManagerOrAdminUser,
    db: DbSession,
    tag_id: uuid.UUID,
    body: PortalTagUpdate,
) -> PortalTagRead:
    tag = await tags_svc.update_tag(db, tag_id, body)
    return PortalTagRead.model_validate(tag)


@router.delete(
    "/tags/{tag_id}",
    summary="Удалить тег",
    status_code=204,
)
async def delete_tag(
    _user: PortalManagerOrAdminUser,
    db: DbSession,
    tag_id: uuid.UUID,
) -> None:
    await tags_svc.delete_tag(db, tag_id)
