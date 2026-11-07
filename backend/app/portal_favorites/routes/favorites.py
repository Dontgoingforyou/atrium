from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_favorites.schemas.favorite import PortalFavoriteCreate, PortalFavoriteRead
from app.portal_favorites.services import favorite as svc

router = APIRouter(prefix="/portal", tags=["Избранное"])

# SPA забирает полный набор (звезда на карточке ищет id во всём списке), как чаты/задачи.
# PagedResponse не отдаём — контракт list[T]; потолок совпадает с le= Query.
_SPA_FAVORITES_LIMIT = 500


@router.get(
    "/favorites",
    summary="Список избранного текущего пользователя",
    response_model=list[PortalFavoriteRead],
)
async def list_favorites(
    user: CurrentUser,
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=_SPA_FAVORITES_LIMIT, ge=1, le=_SPA_FAVORITES_LIMIT),
) -> list[PortalFavoriteRead]:
    return await svc.list_favorites(db, user, skip=skip, limit=limit)


@router.post(
    "/favorites",
    summary="Добавить объект в избранное",
    response_model=PortalFavoriteRead,
    status_code=201,
)
async def create_favorite(
    user: CurrentUser,
    db: DbSession,
    body: PortalFavoriteCreate,
) -> PortalFavoriteRead:
    return await svc.add_favorite(db, user, body)


@router.delete(
    "/favorites/{favorite_id}",
    summary="Удалить запись из избранного",
    status_code=204,
)
async def delete_favorite(
    favorite_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await svc.remove_favorite(db, user, favorite_id)
