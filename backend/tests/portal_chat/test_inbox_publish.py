"""Публичный inbox_publish: контракт payload, не wiring менеджера ради coverage."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.portal_chat.services import inbox_publish as inbox_pub


async def test_publish_dm_inbox_update_payload() -> None:
    mgr = MagicMock(publish=AsyncMock())
    chat_id = uuid.uuid4()
    with patch.object(inbox_pub, "get_inbox_manager", return_value=mgr):
        await inbox_pub.publish_dm_inbox_update("user-sub", chat_id)
    call = mgr.publish.call_args[0]
    assert call[0] == "user-sub"
    assert call[1]["event"] == inbox_pub.EVENT_DM_INBOX_UPDATE
    assert call[1]["kind"] == "dm"
    assert call[1]["chat_id"] == str(chat_id)


async def test_publish_portal_notification_update_includes_notification_id() -> None:
    mgr = MagicMock(publish=AsyncMock())
    nid = uuid.uuid4()
    with patch.object(inbox_pub, "get_inbox_manager", return_value=mgr):
        await inbox_pub.publish_portal_notification_update("sub-2", notification_id=nid)
    mgr.publish.assert_awaited_once_with(
        "sub-2",
        {"event": inbox_pub.EVENT_PORTAL_NOTIFICATION_UPDATE, "notification_id": str(nid)},
    )


async def test_publish_chat_list_refresh_includes_message_id() -> None:
    mgr = MagicMock(publish=AsyncMock())
    chat_id = uuid.uuid4()
    message_id = uuid.uuid4()
    with patch.object(inbox_pub, "get_inbox_manager", return_value=mgr):
        await inbox_pub.publish_chat_list_refresh("user-sub", chat_id, message_id=message_id)
    assert mgr.publish.call_args[0][1]["message_id"] == str(message_id)
    assert mgr.publish.call_args[0][1]["event"] == inbox_pub.EVENT_DM_INBOX_UPDATE


async def test_publish_withdrawals_carry_only_ids() -> None:
    mgr = MagicMock(publish=AsyncMock())
    chat_id = uuid.uuid4()
    message_id = uuid.uuid4()
    with patch.object(inbox_pub, "get_inbox_manager", return_value=mgr):
        await inbox_pub.publish_portal_notification_withdrawals(["a", "b"])
        await inbox_pub.publish_chat_inbox_withdrawals(["c"], chat_id, message_id)
    bell = mgr.publish.await_args_list[0].args[1]
    chat = mgr.publish.await_args_list[2].args[1]
    assert bell == {"event": inbox_pub.EVENT_PORTAL_NOTIFICATION_WITHDRAWN}
    assert chat == {
        "event": inbox_pub.EVENT_DM_INBOX_WITHDRAWN,
        "chat_id": str(chat_id),
        "message_id": str(message_id),
    }
    assert "title" not in bell
    assert "preview_text" not in chat
