"""GET /chats/{id}/messages?around_message_id — окно истории вокруг сообщения."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers.portal_test_users import user_portal_regular


@pytest.mark.asyncio
async def test_list_messages_around_message_id_returns_window(client_admin: AsyncClient) -> None:
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Around", "member_subs": [user_portal_regular().sub]},
    )
    assert r_chat.status_code == 201, r_chat.text
    chat_id = r_chat.json()["id"]
    msg_ids: list[str] = []
    for body in ("first", "anchor", "last"):
        r_msg = await client_admin.post(
            f"/api/v1/portal/chats/{chat_id}/messages",
            json={"body": body},
        )
        assert r_msg.status_code == 201, r_msg.text
        msg_ids.append(r_msg.json()["id"])

    anchor = msg_ids[1]
    r = await client_admin.get(
        f"/api/v1/portal/chats/{chat_id}/messages",
        params={"around_message_id": anchor, "limit": 50},
    )
    assert r.status_code == 200, r.text
    bodies = [m["body"] for m in r.json()]
    assert "anchor" in bodies
    assert "first" in bodies or "last" in bodies
