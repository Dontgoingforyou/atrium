"""Глобальный поиск по сообщениям: исключение удалённых и скрытых."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_portal_search_chat_message_not_found_after_delete_for_all(
    client_admin: AsyncClient,
) -> None:
    marker = "DELSEARCHMARK772"
    r_chat = await client_admin.post(
        "/api/v1/portal/chats/direct",
        json={"other_user_sub": "user-b"},
    )
    assert r_chat.status_code == 200, r_chat.text
    chat_id = r_chat.json()["id"]

    r_msg = await client_admin.post(
        f"/api/v1/portal/chats/{chat_id}/messages",
        json={"body": f"prefix {marker} suffix"},
    )
    assert r_msg.status_code == 201, r_msg.text
    mid = r_msg.json()["id"]

    r_find = await client_admin.get(
        f"/api/v1/portal/search?q={marker}&types=chat_message",
    )
    assert r_find.status_code == 200
    hits_before = [h for h in r_find.json() if h["entity_type"] == "chat_message"]
    assert any(h["message"]["id"] == mid for h in hits_before)

    r_del = await client_admin.delete(
        f"/api/v1/portal/chats/{chat_id}/messages/{mid}",
        params={"scope": "all"},
    )
    assert r_del.status_code == 204, r_del.text

    r_after = await client_admin.get(
        f"/api/v1/portal/search?q={marker}&types=chat_message",
    )
    assert r_after.status_code == 200
    hits_after = [h for h in r_after.json() if h["entity_type"] == "chat_message"]
    assert not any(h["message"]["id"] == mid for h in hits_after)
