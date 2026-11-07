from __future__ import annotations

import logging
import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.core.utils import now_utc as _now_utc
from app.infrastructure.storage.client import (
    async_delete_object,
    async_upload_bytes_to_key,
)
from app.infrastructure.ws.managers import get_chat_manager
from app.portal_chat.services.group_chat import _require_group_chat
from app.schemas.auth import UserPublic
from app.services.avatar_presign import async_presign_avatar_url
from app.services.avatar_upload_common import (
    clamp_focal_01,
    read_and_validate_avatar_upload,
    storage_key_for_group_chat_avatar,
)

logger = logging.getLogger(__name__)


async def save_group_chat_avatar(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    file: UploadFile,
    avatar_focal_x: float | None = None,
    avatar_focal_y: float | None = None,
) -> dict[str, object]:
    chat = await _require_group_chat(session, user, chat_id)
    if chat.created_by_sub != user.sub:
        raise ForbiddenError("Менять аватар может только создатель чата")

    validated = await read_and_validate_avatar_upload(file)
    key = storage_key_for_group_chat_avatar(chat_id, validated.ext)
    old_key = chat.avatar_storage_key

    try:
        await async_upload_bytes_to_key(data=validated.raw, storage_key=key, content_type=validated.content_type)
        chat.avatar_storage_key = key
        if avatar_focal_x is not None and avatar_focal_y is not None:
            chat.avatar_focal_x = clamp_focal_01(avatar_focal_x)
            chat.avatar_focal_y = clamp_focal_01(avatar_focal_y)
        chat.updated_at = _now_utc()
        await session.commit()
        await session.refresh(chat)
    except Exception:
        await session.rollback()
        try:
            await async_delete_object(key)
        except Exception as del_exc:
            logger.warning("Не удалось удалить частично загруженный аватар чата key=%s: %s", key, del_exc)
        raise

    if old_key and old_key != key:
        try:
            await async_delete_object(old_key)
        except Exception as exc:
            logger.warning("Не удалось удалить старый аватар чата key=%s: %s", old_key, exc)

    url = await async_presign_avatar_url(key)
    await get_chat_manager().publish(
        chat_id,
        {"event": "chat_meta_updated", "chat_id": str(chat_id), "title": chat.title},
    )
    return {
        "avatar_url": url,
        "avatar_focal_x": chat.avatar_focal_x,
        "avatar_focal_y": chat.avatar_focal_y,
    }


async def clear_group_chat_avatar(session: AsyncSession, user: UserPublic, chat_id: uuid.UUID) -> None:
    chat = await _require_group_chat(session, user, chat_id)
    if chat.created_by_sub != user.sub:
        raise ForbiddenError("Менять аватар может только создатель чата")
    if not chat.avatar_storage_key:
        return
    old_key = chat.avatar_storage_key
    chat.avatar_storage_key = None
    chat.avatar_focal_x = None
    chat.avatar_focal_y = None
    chat.updated_at = _now_utc()
    await session.commit()
    try:
        await async_delete_object(old_key)
    except Exception as exc:
        logger.warning("Не удалось удалить аватар чата из хранилища key=%s: %s", old_key, exc)
    await get_chat_manager().publish(
        chat_id,
        {"event": "chat_meta_updated", "chat_id": str(chat_id), "title": chat.title},
    )
