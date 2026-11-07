from __future__ import annotations

import uuid
from typing import Any

from app.infrastructure.ws.managers import (
    get_document_page_manager,
    get_nav_tree_manager,
)
from app.portal_chat.comment_thread_events import DOCUMENT_UPDATED_EVENT

# Тот же room_id, что в document_realtime route — broadcast для всех.
_NAV_TREE_ROOM_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


async def publish_document_mutation(
    *,
    document_id: uuid.UUID,
    parent_document_id: uuid.UUID | None,
    extra_document_page_ids: set[uuid.UUID] | None = None,
) -> None:
    """Сообщить подписчикам, что список/карточка документа(ов) устарели (после commit)."""
    payload: dict[str, Any] = {"event": DOCUMENT_UPDATED_EVENT}
    page_mgr = get_document_page_manager()
    await page_mgr.publish(document_id, payload)
    if parent_document_id is not None:
        await page_mgr.publish(parent_document_id, payload)
    for did in extra_document_page_ids or ():
        await page_mgr.publish(did, payload)
    await get_nav_tree_manager().publish(_NAV_TREE_ROOM_ID, payload)
