"""Доступ к изображениям rich-text (presigned URL по стабильному id)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.schemas.rich_media import RichMediaRead
from app.services import rich_media as rich_media_svc

router = APIRouter(prefix="/portal", tags=["Rich-text медиа"])


@router.get(
    "/rich-media/{media_id}",
    summary="Получить временный URL изображения rich-text",
    response_model=RichMediaRead,
)
async def get_rich_media(
    media_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> RichMediaRead:
    """Возвращает presigned URL для отображения изображения в редакторе и просмотре HTML."""
    media = await rich_media_svc.get_rich_media_for_user(db, user, media_id)
    return rich_media_svc.rich_media_to_read(media)
