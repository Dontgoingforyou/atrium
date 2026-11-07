from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_navigation.schemas.navigation import PortalNavNodeTree
from app.portal_navigation.services.navigation import get_navigation_tree

router = APIRouter(prefix="/portal", tags=["Навигация"])


@router.get(
    "/navigation-tree",
    summary="Дерево документов для левого меню",
    response_model=list[PortalNavNodeTree],
)
async def read_navigation_tree(
    user: CurrentUser,
    db: DbSession,
) -> list[PortalNavNodeTree]:
    return await get_navigation_tree(db, user=user)
