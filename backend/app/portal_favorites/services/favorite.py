from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import FavoriteTargetType
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_favorite import PortalFavorite
from app.portal_documents.services.portal_document_queries import ensure_user_can_read_document
from app.portal_favorites.schemas.favorite import PortalFavoriteCreate, PortalFavoriteRead
from app.schemas.auth import UserPublic


def _favorite_to_read(fav: PortalFavorite, title: str) -> PortalFavoriteRead:
    return PortalFavoriteRead(
        id=fav.id,
        target_type=FavoriteTargetType(fav.target_type),
        target_id=fav.target_id,
        created_at=fav.created_at,
        title=title,
    )


async def add_favorite(
    session: AsyncSession,
    user: UserPublic,
    data: PortalFavoriteCreate,
) -> PortalFavoriteRead:
    """Добавить в избранное: документ должен существовать, не быть в корзине и быть доступен пользователю."""
    if data.target_type == FavoriteTargetType.DOCUMENT:
        doc = await ensure_user_can_read_document(session, user, data.target_id)
        title = doc.title
    elif data.target_type == FavoriteTargetType.NAVIGATION_NODE:
        raise NotFoundError("Разделы удалены; добавьте документ в избранное")
    else:
        raise BadRequestError("Неизвестный тип цели")

    row = PortalFavorite(
        user_sub=user.sub,
        target_type=data.target_type.value,
        target_id=data.target_id,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError("Объект уже в избранном") from e
    await session.refresh(row)
    return _favorite_to_read(row, title)


async def remove_favorite(session: AsyncSession, user: UserPublic, favorite_id: uuid.UUID) -> None:
    row = await session.get(PortalFavorite, favorite_id)
    if row is None or row.user_sub != user.sub:
        raise NotFoundError("Запись избранного не найдена")
    await session.delete(row)
    await session.commit()


async def remove_favorites_for_documents(session: AsyncSession, document_ids: list[uuid.UUID]) -> None:
    """Массово убрать документы из избранного всех пользователей.

    Фасад для `portal_documents` при безвозвратном удалении / TTL-очистке корзины.
    Soft-delete избранное не трогает: список и так скрывает документы в корзине, restore вернёт звёзды.
    """
    if not document_ids:
        return
    await session.execute(
        delete(PortalFavorite).where(
            PortalFavorite.target_type == FavoriteTargetType.DOCUMENT.value,
            PortalFavorite.target_id.in_(document_ids),
        )
    )


async def list_favorites(
    session: AsyncSession,
    user: UserPublic,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalFavoriteRead]:
    """Список избранного: только живые документы; LIMIT после JOIN, чтобы «дыры» не съедали страницу."""
    stmt = (
        select(PortalFavorite, PortalDocument.title)
        .join(PortalDocument, PortalDocument.id == PortalFavorite.target_id)
        .where(
            PortalFavorite.user_sub == user.sub,
            PortalFavorite.target_type == FavoriteTargetType.DOCUMENT.value,
            PortalDocument.deleted_at.is_(None),
        )
        .order_by(PortalFavorite.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [_favorite_to_read(fav, title) for fav, title in rows]
