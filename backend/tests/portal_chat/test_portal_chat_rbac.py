"""RBAC / IDOR / 401 чата: матрица auth, timesheet, членство, вложения, PATCH."""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b
from tests.portal_chat.conftest import CHAT_API, as_user, as_user_b, assert_api_error

_AUTH_UUID = "00000000-0000-0000-0000-000000000001"
_FAKE_KEY = "fake-storage-key"
_FAKE_URL = "http://minio.test/presign"


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", f"{CHAT_API}/chats", {}),
        ("POST", f"{CHAT_API}/chats", {"json": {"title": "X", "member_subs": ["user-sub"]}}),
        ("POST", f"{CHAT_API}/chats/direct", {"json": {"other_user_sub": "user-sub"}}),
        ("PATCH", f"{CHAT_API}/chats/{_AUTH_UUID}", {"json": {"expected_version": 1, "title": "X"}}),
        (
            "POST",
            f"{CHAT_API}/chats/{_AUTH_UUID}/avatar",
            {"files": {"file": ("a.jpg", b"\xff\xd8\xff\xe0", "image/jpeg")}},
        ),
        ("DELETE", f"{CHAT_API}/chats/{_AUTH_UUID}/avatar", {}),
        ("DELETE", f"{CHAT_API}/chats/{_AUTH_UUID}", {}),
        ("POST", f"{CHAT_API}/chats/{_AUTH_UUID}/members", {"json": {"user_sub": "x"}}),
        ("DELETE", f"{CHAT_API}/chats/{_AUTH_UUID}/members/x", {}),
        ("GET", f"{CHAT_API}/chats/{_AUTH_UUID}/messages", {}),
        ("POST", f"{CHAT_API}/chats/{_AUTH_UUID}/messages", {"json": {"body": "hi"}}),
        (
            "POST",
            f"{CHAT_API}/chats/{_AUTH_UUID}/messages/forward",
            {"json": {"from_chat_id": _AUTH_UUID, "message_id": _AUTH_UUID}},
        ),
        ("PATCH", f"{CHAT_API}/chats/{_AUTH_UUID}/messages/{_AUTH_UUID}", {"json": {"body": "x"}}),
        (
            "POST",
            f"{CHAT_API}/chats/{_AUTH_UUID}/messages/{_AUTH_UUID}/reactions",
            {"json": {"emoji": "👍"}},
        ),
        ("GET", f"{CHAT_API}/chats/{_AUTH_UUID}/messages/pinned", {}),
        ("POST", f"{CHAT_API}/chats/{_AUTH_UUID}/messages/{_AUTH_UUID}/pin", {}),
        ("DELETE", f"{CHAT_API}/chats/{_AUTH_UUID}/messages/{_AUTH_UUID}/pin", {}),
        ("DELETE", f"{CHAT_API}/chats/{_AUTH_UUID}/messages/{_AUTH_UUID}", {}),
        ("GET", f"{CHAT_API}/chats/{_AUTH_UUID}/messages/{_AUTH_UUID}/readers", {}),
        (
            "GET",
            f"{CHAT_API}/chats/{_AUTH_UUID}/messages/{_AUTH_UUID}/reactions/reactors",
            {"params": {"emoji": "👍"}},
        ),
        ("POST", f"{CHAT_API}/chats/{_AUTH_UUID}/read", {}),
        ("POST", f"{CHAT_API}/chats/{_AUTH_UUID}/ws-ticket", {}),
        (
            "POST",
            f"{CHAT_API}/chats/{_AUTH_UUID}/attachments",
            {"files": {"file": ("x.bin", b"x", "application/octet-stream")}},
        ),
        ("GET", f"{CHAT_API}/chats/{_AUTH_UUID}/attachments", {}),
        ("GET", f"{CHAT_API}/chats/{_AUTH_UUID}/attachments/{_AUTH_UUID}/download", {}),
        ("POST", f"{CHAT_API}/chats/{_AUTH_UUID}/attachments/{_AUTH_UUID}/transcribe", {}),
        ("POST", f"{CHAT_API}/inbox/ws-ticket", {}),
        ("GET", f"{CHAT_API}/push/vapid-public-key", {}),
        (
            "POST",
            f"{CHAT_API}/push/subscribe",
            {"json": {"endpoint": "https://e.example/1", "keys": {"p256dh": "dGVzdA", "auth": "dGVzdDI"}}},
        ),
        ("POST", f"{CHAT_API}/push/unsubscribe", {"json": {"endpoint": "https://e.example/1"}}),
    ],
)
async def test_chat_endpoints_require_auth(
    client_sqlite_only: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_sqlite_only.request(method, path, **kwargs)
    assert_api_error(r, 401, "unauthorized")


async def test_timesheet_only_forbidden_on_chat_routes(client_developer: AsyncClient) -> None:
    r = await client_developer.get(f"{CHAT_API}/chats")
    assert_api_error(r, 403, "forbidden")
    r = await client_developer.post(f"{CHAT_API}/inbox/ws-ticket")
    assert_api_error(r, 403, "forbidden")
    r = await client_developer.get(f"{CHAT_API}/push/vapid-public-key")
    assert_api_error(r, 403, "forbidden")
    r = await client_developer.post(f"{CHAT_API}/chats/{_AUTH_UUID}/messages", json={"body": "x"})
    assert_api_error(r, 403, "forbidden")


async def _group_chat(client: AsyncClient) -> str:
    r = await client.post(
        f"{CHAT_API}/chats",
        json={"title": "RBAC", "member_subs": [user_portal_regular().sub]},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_get_messages_403_non_member(client_admin: AsyncClient) -> None:
    chat_id = await _group_chat(client_admin)
    with as_user_b():
        r = await client_admin.get(f"{CHAT_API}/chats/{chat_id}/messages")
    assert_api_error(r, 403, "forbidden")


async def test_invite_403_outsider(client_admin: AsyncClient) -> None:
    chat_id = await _group_chat(client_admin)
    with as_user_b():
        r = await client_admin.post(
            f"{CHAT_API}/chats/{chat_id}/members",
            json={"user_sub": user_portal_user_b().sub},
        )
    assert_api_error(r, 403, "forbidden")


async def test_patch_message_non_author_forbidden(client_admin: AsyncClient) -> None:
    chat_id = await _group_chat(client_admin)
    r_msg = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/messages", json={"body": "моё"})
    mid = r_msg.json()["id"]
    with as_user(user_portal_regular):
        r = await client_admin.patch(
            f"{CHAT_API}/chats/{chat_id}/messages/{mid}",
            json={"body": "чужое"},
        )
    assert_api_error(r, 403, "forbidden")


async def test_download_attachment_403_non_member(client_admin: AsyncClient) -> None:
    chat_id = await _group_chat(client_admin)
    with (
        patch("app.portal_chat.services.attachment.async_upload_file", new_callable=AsyncMock, return_value=_FAKE_KEY),
        patch("app.portal_chat.services.attachment.get_presigned_url", return_value=_FAKE_URL),
    ):
        r_up = await client_admin.post(
            f"{CHAT_API}/chats/{chat_id}/attachments",
            files={"file": ("x.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    assert r_up.status_code == 201, r_up.text
    att_id = r_up.json()["id"]
    with as_user_b():
        r = await client_admin.get(f"{CHAT_API}/chats/{chat_id}/attachments/{att_id}/download")
    assert_api_error(r, 403, "forbidden")


async def test_download_attachment_wrong_chat_not_found(client_admin: AsyncClient) -> None:
    chat_a = await _group_chat(client_admin)
    r_b = await client_admin.post(
        f"{CHAT_API}/chats",
        json={"title": "Другой", "member_subs": [user_portal_regular().sub]},
    )
    chat_b = r_b.json()["id"]
    with (
        patch("app.portal_chat.services.attachment.async_upload_file", new_callable=AsyncMock, return_value=_FAKE_KEY),
        patch("app.portal_chat.services.attachment.get_presigned_url", return_value=_FAKE_URL),
    ):
        r_up = await client_admin.post(
            f"{CHAT_API}/chats/{chat_a}/attachments",
            files={"file": ("x.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    att_id = r_up.json()["id"]
    r = await client_admin.get(f"{CHAT_API}/chats/{chat_b}/attachments/{att_id}/download")
    assert_api_error(r, 404, "not_found")


async def test_forward_from_inaccessible_source_forbidden(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    r_src = await client_admin.post(
        f"{CHAT_API}/chats",
        json={"title": "Источник", "member_subs": [user_portal_regular().sub]},
    )
    chat_src = r_src.json()["id"]
    r_msg = await client_admin.post(f"{CHAT_API}/chats/{chat_src}/messages", json={"body": "секрет"})
    mid = r_msg.json()["id"]
    with as_user_b():
        r_dst = await client_admin.post(
            f"{CHAT_API}/chats/direct",
            json={"other_user_sub": user_portal_regular().sub},
        )
        assert r_dst.status_code == 200, r_dst.text
        chat_dst = r_dst.json()["id"]
        r = await client_admin.post(
            f"{CHAT_API}/chats/{chat_dst}/messages/forward",
            json={"from_chat_id": chat_src, "message_id": mid},
        )
    assert r.status_code in (403, 404)
    assert r.json().get("code") in ("forbidden", "not_found")


async def test_readers_and_reactors_http(
    client_admin: AsyncClient,
) -> None:
    chat_id = await _group_chat(client_admin)
    r_msg = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/messages", json={"body": "кто"})
    mid = r_msg.json()["id"]
    await client_admin.post(f"{CHAT_API}/chats/{chat_id}/messages/{mid}/reactions", json={"emoji": "👍"})
    r_read = await client_admin.get(f"{CHAT_API}/chats/{chat_id}/messages/{mid}/readers")
    assert r_read.status_code == 200, r_read.text
    r_rx = await client_admin.get(
        f"{CHAT_API}/chats/{chat_id}/messages/{mid}/reactions/reactors",
        params={"emoji": "👍"},
    )
    assert r_rx.status_code == 200, r_rx.text
    reactors = r_rx.json().get("reactors") or []
    assert any(x["user_sub"] == "admin-sub" for x in reactors)
    with as_user_b():
        r_forb = await client_admin.get(f"{CHAT_API}/chats/{chat_id}/messages/{mid}/readers")
    assert_api_error(r_forb, 403, "forbidden")


async def test_hidden_scope_me_peer_still_sees(
    client_admin: AsyncClient,
) -> None:
    chat_id = await _group_chat(client_admin)
    r_msg = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/messages", json={"body": "видно пиру"})
    mid = r_msg.json()["id"]
    with as_user(user_portal_regular):
        r_del = await client_admin.delete(
            f"{CHAT_API}/chats/{chat_id}/messages/{mid}",
            params={"scope": "me"},
        )
        assert r_del.status_code == 204
        r_list = await client_admin.get(f"{CHAT_API}/chats/{chat_id}/messages")
        assert mid not in {m["id"] for m in r_list.json()}
    r_peer = await client_admin.get(f"{CHAT_API}/chats/{chat_id}/messages")
    assert mid in {m["id"] for m in r_peer.json()}


async def test_rate_limit_message_and_upload_429(client_admin: AsyncClient) -> None:
    from app.core.exceptions import RateLimitError

    chat_id = await _group_chat(client_admin)
    with patch(
        "app.portal_chat.routes.messages.enforce_chat_message_post_limit",
        new_callable=AsyncMock,
        side_effect=RateLimitError("Слишком много сообщений. Подождите и повторите."),
    ):
        r = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/messages", json={"body": "spam"})
    assert_api_error(r, 429, "rate_limited")
    with patch(
        "app.portal_chat.routes.messages.enforce_chat_attachment_upload_limit",
        new_callable=AsyncMock,
        side_effect=RateLimitError("Слишком много загрузок файлов. Подождите и повторите."),
    ):
        r_up = await client_admin.post(
            f"{CHAT_API}/chats/{chat_id}/attachments",
            files={"file": ("x.bin", io.BytesIO(b"x"), "application/octet-stream")},
        )
    assert_api_error(r_up, 429, "rate_limited")


async def test_mentions_http_keeps_members_only(client_admin: AsyncClient) -> None:
    chat_id = await _group_chat(client_admin)
    r = await client_admin.post(
        f"{CHAT_API}/chats/{chat_id}/messages",
        json={
            "body": "привет",
            "mentions": [user_portal_regular().sub, user_portal_user_b().sub, "admin-sub"],
        },
    )
    assert r.status_code == 201, r.text
    assert set(r.json().get("mentions") or []) <= {user_portal_regular().sub}


async def test_around_unknown_message_404(client_admin: AsyncClient) -> None:
    chat_id = await _group_chat(client_admin)
    r = await client_admin.get(
        f"{CHAT_API}/chats/{chat_id}/messages",
        params={"around_message_id": str(uuid.uuid4())},
    )
    assert_api_error(r, 404, "not_found")


async def test_push_subscribe_invalid_keys_422(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        f"{CHAT_API}/push/subscribe",
        json={"endpoint": "https://push.example/e", "keys": {"p256dh": "x", "auth": ""}},
    )
    assert r.status_code == 422, r.text


async def test_push_unsubscribe_foreign_endpoint_idempotent(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        f"{CHAT_API}/push/unsubscribe",
        json={"endpoint": "https://push.example/someone-else"},
    )
    assert r.status_code == 204


async def test_hidden_scope_me_stays_in_peer_search(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    from app.portal_chat.services import chat as chat_svc

    chat_id = await _group_chat(client_admin)
    marker = "HIDPEERSRCH991"
    r_msg = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/messages", json={"body": marker})
    mid = r_msg.json()["id"]
    with as_user(user_portal_regular):
        r_del = await client_admin.delete(
            f"{CHAT_API}/chats/{chat_id}/messages/{mid}",
            params={"scope": "me"},
        )
        assert r_del.status_code == 204
        hidden = await chat_svc.search_messages_for_user(sqlite_session, user_portal_regular(), marker)
        assert all(row[0].id != uuid.UUID(mid) for row in hidden)
    found = await chat_svc.search_messages_for_user(sqlite_session, user_portal_admin(), marker)
    assert any(row[0].id == uuid.UUID(mid) for row in found)


async def test_pin_deleted_message_422(client_admin: AsyncClient) -> None:
    chat_id = await _group_chat(client_admin)
    r_msg = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/messages", json={"body": "пин"})
    mid = r_msg.json()["id"]
    await client_admin.delete(f"{CHAT_API}/chats/{chat_id}/messages/{mid}", params={"scope": "all"})
    r = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/messages/{mid}/pin")
    assert r.status_code in (404, 422)
    assert r.json()["code"] in ("not_found", "validation_error")


async def test_transcribe_429(client_admin: AsyncClient) -> None:
    from app.core.exceptions import RateLimitError

    chat_id = await _group_chat(client_admin)
    with patch(
        "app.portal_chat.routes.messages.enforce_chat_transcribe_limit",
        new_callable=AsyncMock,
        side_effect=RateLimitError("Слишком много запросов транскрипции."),
    ):
        r = await client_admin.post(
            f"{CHAT_API}/chats/{chat_id}/attachments/{_AUTH_UUID}/transcribe",
        )
    assert_api_error(r, 429, "rate_limited")


async def test_patch_message_author_ok(client_admin: AsyncClient) -> None:
    chat_id = await _group_chat(client_admin)
    r_msg = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/messages", json={"body": "черновик"})
    mid = r_msg.json()["id"]
    r = await client_admin.patch(f"{CHAT_API}/chats/{chat_id}/messages/{mid}", json={"body": "готово"})
    assert r.status_code == 200, r.text
    assert r.json()["body"] == "готово"


async def test_invite_member_http_ok(client_admin: AsyncClient) -> None:
    chat_id = await _group_chat(client_admin)
    r = await client_admin.post(
        f"{CHAT_API}/chats/{chat_id}/members",
        json={"user_sub": user_portal_user_b().sub},
    )
    assert r.status_code == 204, r.text
