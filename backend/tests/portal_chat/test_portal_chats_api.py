"""Интеграционные тесты: чаты (GET /portal/chats, POST /portal/chats, POST /portal/chats/direct).

Покрытие (testing.mdc):
- успешный доступ
- изоляция данных (обычный пользователь видит только свои чаты)
- 401 без авторизации
- обогащённые поля ответа (member_subs)
- идемпотентность get_or_create_direct_chat
"""

from __future__ import annotations

import io
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.infrastructure.db.models.portal_chat import (
    PortalChat,
    PortalChatAttachment,
    PortalChatMember,
    PortalChatMessage,
)
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.integrations.effective_admin.client import PhotoMeta
from app.main import app
from app.portal_chat.services.chat import get_or_create_direct_chat
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_oidc_settings
from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b

# ---------------------------------------------------------------------------
# GET /portal/chats  — список чатов
# ---------------------------------------------------------------------------


async def test_create_chat_ignores_unknown_field(
    client_admin: AsyncClient,
) -> None:
    """POST /chats с лишним полем `nav_node_id` в теле — Pydantic игнорирует неизвестное поле."""
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "X", "nav_node_id": str(uuid.uuid4()), "member_subs": [user_portal_regular().sub]},
    )
    assert r.status_code == 201, r.text
    assert "nav_node_id" not in r.json()


async def test_list_chats_empty(client_admin: AsyncClient) -> None:
    """Пустой список при отсутствии чатов в БД."""
    r = await client_admin.get("/api/v1/portal/chats")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_chats_excludes_orphan_non_dm_without_title(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Не-DM без раздела и без названия не показываются (типичный сирота после удаления раздела)."""
    now = datetime.now(UTC)
    orphan_id = uuid.uuid4()
    sqlite_session.add(
        PortalChat(
            id=orphan_id,
            title=None,
            created_by_sub=user_portal_admin().sub,
            created_at=now,
            updated_at=now,
            canonical_dm_key=None,
        )
    )
    sqlite_session.add(
        PortalChatMember(
            chat_id=orphan_id,
            user_sub=user_portal_admin().sub,
            joined_at=now,
        )
    )
    await sqlite_session.commit()

    r = await client_admin.get("/api/v1/portal/chats")
    assert r.status_code == 200
    ids = {c["id"] for c in r.json()}
    assert str(orphan_id) not in ids


async def test_orphan_non_dm_messages_returns_404(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Доступ к сообщениям сироты — 404 (как к отсутствующему чату)."""
    now = datetime.now(UTC)
    orphan_id = uuid.uuid4()
    sqlite_session.add(
        PortalChat(
            id=orphan_id,
            title=None,
            created_by_sub=user_portal_admin().sub,
            created_at=now,
            updated_at=now,
            canonical_dm_key=None,
        )
    )
    sqlite_session.add(
        PortalChatMember(
            chat_id=orphan_id,
            user_sub=user_portal_admin().sub,
            joined_at=now,
        )
    )
    await sqlite_session.commit()

    r = await client_admin.get(f"/api/v1/portal/chats/{orphan_id}/messages")
    from tests.portal_chat.conftest import assert_api_error

    assert_api_error(r, 404, "not_found")


async def test_list_chats_member_subs_populated(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Поле member_subs содержит sub обоих участников созданного чата."""
    # Создаём чат от имени admin с ещё одним участником
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Тестовый чат", "member_subs": [user_portal_regular().sub]},
    )
    assert r.status_code == 201, r.text
    chat = r.json()
    assert set(chat["member_subs"]) == {user_portal_admin().sub, user_portal_regular().sub}

    # При листинге тоже возвращается
    r2 = await client_admin.get("/api/v1/portal/chats")
    assert r2.status_code == 200
    chats = r2.json()
    assert len(chats) == 1
    assert set(chats[0]["member_subs"]) == {user_portal_admin().sub, user_portal_regular().sub}


def _enable_user_photo_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_oidc_settings(
        effective_admin_base_url="https://ea.example",
        admin_session_secret="dev-secret-change-me",
    )
    monkeypatch.setattr("app.services.user_photo_url.get_settings", lambda: settings)


async def test_list_chats_dm_avatar_url_is_peer_photo_proxy(
    client_admin: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """У DM без group-ключа avatar_url — signed photo пира, не текущего пользователя."""
    _enable_user_photo_urls(monkeypatch)
    meta = PhotoMeta(has_photo=True, version=4)
    with patch(
        "app.services.portal_user.get_cached_photo_meta_bulk",
        new=AsyncMock(return_value={"user": meta}),
    ):
        created = await client_admin.post(
            "/api/v1/portal/chats/direct",
            json={"other_user_sub": user_portal_regular().sub},
        )
        assert created.status_code == 200, created.text
        listed = await client_admin.get("/api/v1/portal/chats")
    assert listed.status_code == 200
    dm = next(c for c in listed.json() if c["is_direct"])
    assert dm["avatar_url"] is not None
    assert f"/portal/users/{user_portal_regular().sub}/photo" in dm["avatar_url"]
    assert user_portal_admin().sub not in (dm["avatar_url"] or "")


async def test_list_chats_dm_avatar_url_none_when_peer_has_no_photo(
    client_admin: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_user_photo_urls(monkeypatch)
    meta = PhotoMeta(has_photo=False, version=None)
    with patch(
        "app.services.portal_user.get_cached_photo_meta_bulk",
        new=AsyncMock(return_value={"user": meta}),
    ):
        created = await client_admin.post(
            "/api/v1/portal/chats/direct",
            json={"other_user_sub": user_portal_regular().sub},
        )
        assert created.status_code == 200, created.text
        listed = await client_admin.get("/api/v1/portal/chats")
    dm = next(c for c in listed.json() if c["is_direct"])
    assert dm["avatar_url"] is None


async def test_list_chats_group_avatar_url_stays_presign(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    created = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Группа с аватаром", "member_subs": [user_portal_regular().sub]},
    )
    assert created.status_code == 201, created.text
    chat_id = uuid.UUID(created.json()["id"])
    row = await sqlite_session.get(PortalChat, chat_id)
    assert row is not None
    row.avatar_storage_key = "avatars/chats/g/face.jpg"
    await sqlite_session.commit()

    presigned = "https://minio.example/avatars/chats/g/face.jpg?X-Amz-Signature=abc"
    with patch("app.portal_chat.routes.chats.presign_avatar_url", return_value=presigned):
        listed = await client_admin.get("/api/v1/portal/chats")
    assert listed.status_code == 200
    group = next(c for c in listed.json() if c["id"] == str(chat_id))
    assert group["avatar_url"] == presigned
    assert "/portal/users/" not in (group["avatar_url"] or "")


async def test_list_chats_isolation_regular_user(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Обычный пользователь видит только те чаты, где он участник."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    # Чат создаётся от имени admin — regular user не добавлен в участники
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    transport = ASGITransport(app=app)
    # Чат только с admin (без regular) — через БД, т.к. POST /chats требует ≥2 участников
    now = datetime.now(UTC)
    only_admin_chat = uuid.uuid4()
    sqlite_session.add(
        PortalChat(
            id=only_admin_chat,
            title="Только admin",
            created_by_sub=user_portal_admin().sub,
            created_at=now,
            updated_at=now,
            canonical_dm_key=None,
        )
    )
    sqlite_session.add(
        PortalChatMember(
            chat_id=only_admin_chat,
            user_sub=user_portal_admin().sub,
            joined_at=now,
        )
    )
    await sqlite_session.commit()

    # Запрос от regular user — чат не должен быть виден
    app.dependency_overrides[get_current_user] = user_portal_regular
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_list = await ac.get("/api/v1/portal/chats")
    assert r_list.status_code == 200
    assert r_list.json() == []

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


# ---------------------------------------------------------------------------
# POST /portal/chats/direct  — прямые сообщения
# ---------------------------------------------------------------------------


async def test_direct_chat_creates_dm(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """POST /direct создаёт DM-чат без привязки к разделу/документу."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/portal/chats/direct",
            json={"other_user_sub": user_portal_regular().sub},
        )
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["is_direct"] is True
    assert set(data["member_subs"]) == {user_portal_admin().sub, user_portal_regular().sub}


async def test_direct_chat_forbidden_when_other_portal_chat_disallowed(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """POST /direct с пользователем без доступа к чатам портала — 403."""
    sub = "student-no-portal-chat-sub"
    sqlite_session.add(
        PortalUserProfile(
            sub=sub,
            email="st@x.local",
            full_name="Студент",
            username="st",
            is_portal_admin=False,
            portal_chat_allowed=False,
        )
    )
    await sqlite_session.commit()
    r = await client_admin.post(
        "/api/v1/portal/chats/direct",
        json={"other_user_sub": sub},
    )
    assert r.status_code == 403, r.text
    assert r.json().get("code") == "forbidden"


async def test_create_group_chat_forbidden_when_member_portal_chat_disallowed(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """POST /chats с участником без доступа к чатам портала — отказ."""
    sub = "student-group-member-sub"
    sqlite_session.add(
        PortalUserProfile(
            sub=sub,
            email="st2@x.local",
            full_name="Студент 2",
            username="st2",
            is_portal_admin=False,
            portal_chat_allowed=False,
        )
    )
    await sqlite_session.commit()
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Группа", "member_subs": [sub]},
    )
    assert r.status_code == 422, r.text
    assert r.json().get("code") == "validation_error"


async def test_direct_chat_idempotent(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Повторный POST /direct с теми же участниками возвращает тот же чат."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.post(
            "/api/v1/portal/chats/direct",
            json={"other_user_sub": user_portal_regular().sub},
        )
        r2 = await ac.post(
            "/api/v1/portal/chats/direct",
            json={"other_user_sub": user_portal_regular().sub},
        )
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"], "Повторный вызов должен возвращать тот же чат"


async def test_direct_chat_symmetric(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """DM создаётся один раз независимо от того, кто инициатор — A→B или B→A."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)

    # A создаёт чат с B
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_ab = await ac.post(
            "/api/v1/portal/chats/direct",
            json={"other_user_sub": user_portal_regular().sub},
        )
    assert r_ab.status_code == 200

    # B создаёт чат с A — должен вернуть тот же
    app.dependency_overrides[get_current_user] = user_portal_regular
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_ba = await ac.post(
            "/api/v1/portal/chats/direct",
            json={"other_user_sub": user_portal_admin().sub},
        )
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)

    assert r_ba.status_code == 200
    assert r_ab.json()["id"] == r_ba.json()["id"], "A→B и B→A должны давать один и тот же чат"


async def test_direct_chat_canonical_dm_key_set(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """При создании DM поле canonical_dm_key заполняется в формате '{min}|{max}'."""
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await get_or_create_direct_chat(sqlite_session, admin, regular.sub)

    # Убеждаемся, что ключ есть в БД и имеет правильный канонический вид
    row = (await sqlite_session.execute(sa_select(PortalChat).where(PortalChat.id == chat.id))).scalars().first()
    assert row is not None
    expected_key = "|".join(sorted([admin.sub, regular.sub]))
    assert row.canonical_dm_key == expected_key


async def test_direct_chat_sequential_get_or_create_same_chat(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Повторный get_or_create_direct_chat в одной сессии возвращает тот же чат.

    Параллельная гонка UNIQUE(canonical_dm_key) — в tests/concurrency.
    """
    admin = user_portal_admin()
    regular = user_portal_regular()

    chat1 = await get_or_create_direct_chat(sqlite_session, admin, regular.sub)
    chat2 = await get_or_create_direct_chat(sqlite_session, admin, regular.sub)

    assert chat1.id == chat2.id, "Повторный вызов должен вернуть тот же чат"
    assert chat1.canonical_dm_key == chat2.canonical_dm_key


# ---------------------------------------------------------------------------
# unread_count + POST /portal/chats/{id}/read
# ---------------------------------------------------------------------------


async def test_unread_count_in_chat_list(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """unread_count > 0 после нового сообщения от другого участника."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)

    # Admin создаёт чат с user-b
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Тест unread", "member_subs": [user_portal_regular().sub]},
        )
        assert r.status_code == 201
        chat_id = r.json()["id"]
        # Admin отправляет сообщение
        await ac.post(f"/api/v1/portal/chats/{chat_id}/messages", json={"body": "Привет!"})

    # user (regular) проверяет unread_count
    app.dependency_overrides[get_current_user] = user_portal_regular
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/portal/chats")
        assert r.status_code == 200
        chats = [c for c in r.json() if c["id"] == chat_id]
        assert len(chats) == 1
        assert chats[0]["unread_count"] == 1, "regular user должен видеть 1 непрочитанное"

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


async def test_mark_chat_read_resets_unread_count(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """POST /chats/{id}/read сбрасывает unread_count до 0."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Тест mark-read", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r.json()["id"]
        await ac.post(f"/api/v1/portal/chats/{chat_id}/messages", json={"body": "Сообщение"})

    # regular: проверяем, что unread_count=1, затем вызываем mark-read
    app.dependency_overrides[get_current_user] = user_portal_regular
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/portal/chats")
        chats = [c for c in r.json() if c["id"] == chat_id]
        assert chats[0]["unread_count"] == 1

        r = await ac.post(f"/api/v1/portal/chats/{chat_id}/read")
        assert r.status_code == 204

        r = await ac.get("/api/v1/portal/chats")
        chats = [c for c in r.json() if c["id"] == chat_id]
        assert chats[0]["unread_count"] == 0, "После mark-read счётчик должен сброситься"

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


async def test_message_receipt_sent_then_read(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """GET /messages: у автора receipt sent, пока другой не отметил чат; read после POST /read."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Тест receipt", "member_subs": [user_portal_regular().sub]},
        )
        assert r.status_code == 201
        chat_id = r.json()["id"]
        r2 = await ac.post(f"/api/v1/portal/chats/{chat_id}/messages", json={"body": "Проверка"})
        assert r2.status_code == 201
        r_list = await ac.get(f"/api/v1/portal/chats/{chat_id}/messages")
        assert r_list.status_code == 200
        msgs = r_list.json()
        assert len(msgs) == 1
        assert msgs[0]["receipt"] == "sent"

    app.dependency_overrides[get_current_user] = user_portal_regular
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/portal/chats/{chat_id}/read")
        assert r.status_code == 204

    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_list = await ac.get(f"/api/v1/portal/chats/{chat_id}/messages")
        assert r_list.status_code == 200
        msgs = r_list.json()
        assert msgs[0]["receipt"] == "read"

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


async def test_post_message_with_reply_and_toggle_reaction(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Ответ на сообщение и toggle реакции через POST .../reactions."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Reply и реакции", "member_subs": [user_portal_regular().sub]},
        )
        assert r.status_code == 201
        chat_id = r.json()["id"]
        r1 = await ac.post(f"/api/v1/portal/chats/{chat_id}/messages", json={"body": "Первое"})
        assert r1.status_code == 201
        mid = r1.json()["id"]
        r2 = await ac.post(
            f"/api/v1/portal/chats/{chat_id}/messages",
            json={"body": "Ответ", "reply_to_message_id": mid},
        )
        assert r2.status_code == 201
        body2 = r2.json()
        assert body2["reply_to_message_id"] == mid
        assert body2["reply_to"]["id"] == mid
        rx = await ac.post(
            f"/api/v1/portal/chats/{chat_id}/messages/{mid}/reactions",
            json={"emoji": "👍"},
        )
        assert rx.status_code == 200
        data = rx.json()
        thumbs = [x for x in data["reactions"] if x["emoji"] == "👍"]
        assert len(thumbs) == 1
        assert thumbs[0]["count"] == 1
        assert thumbs[0]["reacted_by_me"] is True
        rx2 = await ac.post(
            f"/api/v1/portal/chats/{chat_id}/messages/{mid}/reactions",
            json={"emoji": "👍"},
        )
        assert rx2.status_code == 200
        assert not any(x["emoji"] == "👍" for x in rx2.json()["reactions"])

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


async def test_forward_message_to_other_chat(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """POST .../messages/forward копирует текст и помечает пересланного автора."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_a = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Источник", "member_subs": [user_portal_regular().sub]},
        )
        assert r_a.status_code == 201
        chat_a = r_a.json()["id"]
        r_b = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Назначение", "member_subs": [user_portal_regular().sub]},
        )
        assert r_b.status_code == 201
        chat_b = r_b.json()["id"]

        r_msg = await ac.post(
            f"/api/v1/portal/chats/{chat_a}/messages",
            json={"body": "Текст для пересылки"},
        )
        assert r_msg.status_code == 201
        mid = r_msg.json()["id"]

        with patch(
            "app.infrastructure.storage.client.copy_object_to_new_key",
            return_value="copied-key",
        ):
            r_fwd = await ac.post(
                f"/api/v1/portal/chats/{chat_b}/messages/forward",
                json={"from_chat_id": chat_a, "message_id": mid},
            )
        assert r_fwd.status_code == 201, r_fwd.text
        data = r_fwd.json()
        assert data["chat_id"] == chat_b
        assert data["body"] == "Текст для пересылки"
        assert data["forwarded_from"]["author_sub"] == user_portal_admin().sub
        assert data["forwarded_from"]["source_message_id"] == mid

        r_same = await ac.post(
            f"/api/v1/portal/chats/{chat_a}/messages/forward",
            json={"from_chat_id": chat_a, "message_id": mid},
        )
        assert r_same.status_code == 422

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


async def test_forward_message_respects_rate_limit(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Пересылка сообщений подчиняется тому же rate limit, что и обычная отправка (не lazyway для DoS)."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_a = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Источник", "member_subs": [user_portal_regular().sub]},
        )
        chat_a = r_a.json()["id"]
        r_b = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Назначение", "member_subs": [user_portal_regular().sub]},
        )
        chat_b = r_b.json()["id"]
        r_msg = await ac.post(
            f"/api/v1/portal/chats/{chat_a}/messages",
            json={"body": "Текст"},
        )
        mid = r_msg.json()["id"]

        with patch(
            "app.portal_chat.routes.messages.enforce_chat_message_post_limit",
            new_callable=AsyncMock,
        ) as limit_mock:
            from app.core.exceptions import RateLimitError

            limit_mock.side_effect = RateLimitError("Слишком много сообщений. Подождите и повторите.")
            r_fwd = await ac.post(
                f"/api/v1/portal/chats/{chat_b}/messages/forward",
                json={"from_chat_id": chat_a, "message_id": mid},
            )
        assert r_fwd.status_code == 429, r_fwd.text
        limit_mock.assert_awaited_once_with(user_portal_admin().sub, uuid.UUID(chat_b))

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


async def test_mark_chat_read_403_non_member(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """403 при попытке mark-read для чата, в котором пользователь не участник."""
    from tests.helpers.portal_test_users import user_portal_user_b

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Закрытый чат", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r.json()["id"]

    # user_b не является участником чата
    app.dependency_overrides[get_current_user] = user_portal_user_b
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/portal/chats/{chat_id}/read")
        assert r.status_code == 403

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


# ---------------------------------------------------------------------------
# POST /portal/chats/{id}/attachments  — загрузка вложений
# ---------------------------------------------------------------------------

_FAKE_STORAGE_KEY = "test-storage-key-abc123"
_FAKE_PRESIGNED_URL = "http://minio.test/chat-attachments/test-storage-key-abc123?X-Amz-Signature=fake"


def _mock_storage() -> MagicMock:
    """Мок storage-клиента: upload_file → фиксированный ключ; get_presigned_url → фиксированный URL."""
    m = MagicMock()
    m.upload_file.return_value = _FAKE_STORAGE_KEY
    m.get_presigned_url.return_value = _FAKE_PRESIGNED_URL
    m.delete_object.return_value = None
    return m


async def test_upload_attachment_success(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """POST .../attachments: участник чата успешно загружает файл."""
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Чат с вложением", "member_subs": [user_portal_regular().sub]},
    )
    assert r_chat.status_code == 201
    chat_id = r_chat.json()["id"]

    with (
        patch(  # noqa: E501
            "app.portal_chat.services.attachment.async_upload_file",
            new_callable=AsyncMock,
            return_value=_FAKE_STORAGE_KEY,
        ),
        patch("app.portal_chat.services.attachment.get_presigned_url", return_value=_FAKE_PRESIGNED_URL),
    ):
        r = await client_admin.post(
            f"/api/v1/portal/chats/{chat_id}/attachments",
            files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")},
        )

    assert r.status_code == 201, r.text
    data = r.json()
    assert data["original_filename"] == "test.txt"
    assert data["content_type"] == "text/plain"
    assert data["file_size"] == 11
    assert "id" in data
    assert data["download_url"] == _FAKE_PRESIGNED_URL


async def test_upload_attachment_403_non_member(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """403 при загрузке вложения в чат, где пользователь не участник."""
    from tests.helpers.portal_test_users import user_portal_user_b

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)

    # admin создаёт чат без user_b
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Закрытый", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r.json()["id"]

    # user_b пытается загрузить вложение
    app.dependency_overrides[get_current_user] = user_portal_user_b
    with (
        patch(  # noqa: E501
            "app.portal_chat.services.attachment.async_upload_file",
            new_callable=AsyncMock,
            return_value=_FAKE_STORAGE_KEY,
        ),
        patch("app.portal_chat.services.attachment.get_presigned_url", return_value=_FAKE_PRESIGNED_URL),
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                f"/api/v1/portal/chats/{chat_id}/attachments",
                files={"file": ("x.txt", io.BytesIO(b"x"), "text/plain")},
            )
    assert r.status_code == 403

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


async def test_post_message_with_attachment(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Сообщение с вложением: attachment_ids привязываются к сообщению и возвращаются в ответе."""
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Чат с файлом", "member_subs": [user_portal_regular().sub]},
    )
    assert r_chat.status_code == 201
    chat_id = r_chat.json()["id"]

    with (
        patch(  # noqa: E501
            "app.portal_chat.services.attachment.async_upload_file",
            new_callable=AsyncMock,
            return_value=_FAKE_STORAGE_KEY,
        ),
        patch("app.portal_chat.services.attachment.get_presigned_url", return_value=_FAKE_PRESIGNED_URL),
        patch("app.infrastructure.storage.client.get_presigned_url", return_value=_FAKE_PRESIGNED_URL),
    ):
        r_att = await client_admin.post(
            f"/api/v1/portal/chats/{chat_id}/attachments",
            files={"file": ("photo.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 4), "image/png")},
        )
        assert r_att.status_code == 201, r_att.text
        att_id = r_att.json()["id"]

        r_msg = await client_admin.post(
            f"/api/v1/portal/chats/{chat_id}/messages",
            json={"body": "", "attachment_ids": [att_id]},
        )

    assert r_msg.status_code == 201, r_msg.text
    msg = r_msg.json()
    assert len(msg["attachments"]) == 1
    assert msg["attachments"][0]["id"] == att_id
    assert msg["attachments"][0]["original_filename"] == "photo.png"


async def test_post_message_empty_body_without_attachment_422(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Пустое тело без вложений → 422."""
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Чат", "member_subs": [user_portal_regular().sub]},
    )
    chat_id = r_chat.json()["id"]

    r = await client_admin.post(
        f"/api/v1/portal/chats/{chat_id}/messages",
        json={"body": "", "attachment_ids": []},
    )
    assert r.status_code == 422


async def test_delete_message_for_all_purges_attachment_and_calls_minio(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """DELETE messages?scope=all удаляет строку вложения и вызывает MinIO delete_object."""
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Del attach", "member_subs": [user_portal_regular().sub]},
    )
    assert r_chat.status_code == 201
    chat_id = r_chat.json()["id"]

    delete_mock = AsyncMock()
    with (
        patch(  # noqa: E501
            "app.portal_chat.services.attachment.async_upload_file",
            new_callable=AsyncMock,
            return_value=_FAKE_STORAGE_KEY,
        ),
        patch("app.portal_chat.services.attachment.get_presigned_url", return_value=_FAKE_PRESIGNED_URL),
        patch("app.infrastructure.storage.client.get_presigned_url", return_value=_FAKE_PRESIGNED_URL),
        patch("app.portal_chat.services._mutations.async_delete_object", delete_mock),
    ):
        r_att = await client_admin.post(
            f"/api/v1/portal/chats/{chat_id}/attachments",
            files={"file": ("f.txt", io.BytesIO(b"x"), "text/plain")},
        )
        assert r_att.status_code == 201
        att_id = r_att.json()["id"]
        r_msg = await client_admin.post(
            f"/api/v1/portal/chats/{chat_id}/messages",
            json={"body": "текст", "attachment_ids": [att_id]},
        )
        assert r_msg.status_code == 201
        msg_id = r_msg.json()["id"]
        r_del = await client_admin.delete(
            f"/api/v1/portal/chats/{chat_id}/messages/{msg_id}",
            params={"scope": "all"},
        )

    assert r_del.status_code == 204
    delete_mock.assert_called_once_with(_FAKE_STORAGE_KEY)
    att = await sqlite_session.get(PortalChatAttachment, uuid.UUID(att_id))
    assert att is None
    msg = await sqlite_session.get(PortalChatMessage, uuid.UUID(msg_id))
    assert msg is not None
    assert msg.deleted_for_all_at is not None


async def test_create_group_chat_requires_title_and_members(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "", "member_subs": [user_portal_regular().sub]},
    )
    assert r.status_code == 422
    r2 = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Ок", "member_subs": []},
    )
    assert r2.status_code == 422


async def test_group_chat_patch_title_and_members_flow(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Нельзя смешивать client_admin и client_user в одном тесте (get_current_user)."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    transport = ASGITransport(app=app)

    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Команда", "member_subs": [user_portal_regular().sub]},
        )
        assert r.status_code == 201, r.text
        chat_id = r.json()["id"]

        r_patch = await ac.patch(
            f"/api/v1/portal/chats/{chat_id}",
            json={"expected_version": 1, "title": "Команда Альфа"},
        )
        assert r_patch.status_code == 200
        assert r_patch.json()["title"] == "Команда Альфа"

        r_inv = await ac.post(
            f"/api/v1/portal/chats/{chat_id}/members",
            json={"user_sub": user_portal_user_b().sub},
        )
        assert r_inv.status_code == 204

        r_list = await ac.get("/api/v1/portal/chats")
        chat = next(c for c in r_list.json() if c["id"] == chat_id)
        assert user_portal_user_b().sub in chat["member_subs"]

    app.dependency_overrides[get_current_user] = user_portal_regular
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_leave = await ac.delete(
            f"/api/v1/portal/chats/{chat_id}/members/{user_portal_regular().sub}",
        )
        assert r_leave.status_code == 204

    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_list2 = await ac.get("/api/v1/portal/chats")
        chat2 = next(c for c in r_list2.json() if c["id"] == chat_id)
        assert user_portal_regular().sub not in chat2["member_subs"]

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


async def test_group_chat_creator_cannot_leave(
    client_admin: AsyncClient,
) -> None:
    r = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Владелец", "member_subs": [user_portal_regular().sub]},
    )
    cid = r.json()["id"]
    r_del = await client_admin.delete(f"/api/v1/portal/chats/{cid}/members/{user_portal_admin().sub}")
    assert r_del.status_code == 403


async def test_group_chat_non_creator_cannot_patch_title(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    transport = ASGITransport(app=app)
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Группа прав", "member_subs": [user_portal_regular().sub]},
        )
        cid = r.json()["id"]

    app.dependency_overrides[get_current_user] = user_portal_regular
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_patch = await ac.patch(
            f"/api/v1/portal/chats/{cid}",
            json={"expected_version": 1, "title": "Взлом"},
        )
        assert r_patch.status_code == 403

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


# ---------------------------------------------------------------------------
# 403 — не-участник чата не может отправлять сообщения и ставить реакции
# ---------------------------------------------------------------------------


async def test_post_message_403_non_member(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """POST .../messages → 403, если пользователь не участник чата."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Закрытый", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r.json()["id"]

    app.dependency_overrides[get_current_user] = user_portal_user_b
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/portal/chats/{chat_id}/messages", json={"body": "Взлом"})
        assert r.status_code == 403

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


async def test_toggle_reaction_403_non_member(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """POST .../messages/{id}/reactions → 403, если пользователь не участник."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_chat = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Реакции доступ", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r_chat.json()["id"]
        r_msg = await ac.post(f"/api/v1/portal/chats/{chat_id}/messages", json={"body": "Тест"})
        mid = r_msg.json()["id"]

    app.dependency_overrides[get_current_user] = user_portal_user_b
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/portal/chats/{chat_id}/messages/{mid}/reactions",
            json={"emoji": "👍"},
        )
        assert r.status_code == 403

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


async def test_forward_message_403_non_member_target(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """POST .../messages/forward → 403, если пользователь не участник чата-назначения."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_src = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Источник", "member_subs": [user_portal_regular().sub]},
        )
        chat_src = r_src.json()["id"]
        r_msg = await ac.post(f"/api/v1/portal/chats/{chat_src}/messages", json={"body": "Переслать"})
        mid = r_msg.json()["id"]
        # Чат-назначение без user_b
        r_dst = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Назначение без user_b", "member_subs": [user_portal_regular().sub]},
        )
        chat_dst = r_dst.json()["id"]

    app.dependency_overrides[get_current_user] = user_portal_user_b
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/portal/chats/{chat_dst}/messages/forward",
            json={"from_chat_id": chat_src, "message_id": mid},
        )
        assert r.status_code == 403

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


_FAKE_KEY = "fake-storage-key"
_FAKE_URL = "http://minio.test/presign"


async def test_get_attachment_download_returns_presigned(client_admin: AsyncClient) -> None:
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Att DL", "member_subs": [user_portal_regular().sub]},
    )
    chat_id = r_chat.json()["id"]
    with (
        patch("app.portal_chat.services.attachment.async_upload_file", new_callable=AsyncMock, return_value=_FAKE_KEY),
        patch("app.portal_chat.services.attachment.get_presigned_url", return_value=_FAKE_URL),
    ):
        r_up = await client_admin.post(
            f"/api/v1/portal/chats/{chat_id}/attachments",
            files={"file": ("x.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
    assert r_up.status_code == 201
    att_id = r_up.json()["id"]
    with patch("app.portal_chat.services.attachment.get_presigned_url", return_value=_FAKE_URL):
        r_get = await client_admin.get(f"/api/v1/portal/chats/{chat_id}/attachments/{att_id}/download")
    assert r_get.status_code == 200
    assert r_get.json()["download_url"] == _FAKE_URL


async def test_list_chats_respects_skip(client_admin: AsyncClient) -> None:
    for i in range(2):
        await client_admin.post(
            "/api/v1/portal/chats",
            json={"title": f"C{i}", "member_subs": [user_portal_regular().sub]},
        )
    r_all = await client_admin.get("/api/v1/portal/chats", params={"skip": 0, "limit": 10})
    r = await client_admin.get("/api/v1/portal/chats", params={"skip": 1, "limit": 10})
    assert r.status_code == 200
    assert len(r.json()) == len(r_all.json()) - 1
    assert {c["id"] for c in r.json()}.issubset({c["id"] for c in r_all.json()})


async def test_list_messages_skip_limit(client_admin: AsyncClient) -> None:
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Hist", "member_subs": [user_portal_regular().sub]},
    )
    chat_id = r_chat.json()["id"]
    await client_admin.post(f"/api/v1/portal/chats/{chat_id}/messages", json={"body": "одно"})
    r = await client_admin.get(
        f"/api/v1/portal/chats/{chat_id}/messages",
        params={"skip": 0, "limit": 10},
    )
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_delete_message_scope_me_hides_for_user(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    app.dependency_overrides[get_db_session] = _db
    transport = ASGITransport(app=app)
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_chat = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Hide me", "member_subs": [user_portal_regular().sub]},
        )
        assert r_chat.status_code == 201, r_chat.text
        chat_id = r_chat.json()["id"]

        app.dependency_overrides[get_current_user] = user_portal_regular
        r_msg = await ac.post(f"/api/v1/portal/chats/{chat_id}/messages", json={"body": "временное"})
        assert r_msg.status_code == 201
        msg_id = r_msg.json()["id"]
        r_del = await ac.delete(
            f"/api/v1/portal/chats/{chat_id}/messages/{msg_id}",
            params={"scope": "me"},
        )
        assert r_del.status_code == 204
        r_list = await ac.get(f"/api/v1/portal/chats/{chat_id}/messages")
        assert r_list.status_code == 200
        assert msg_id not in {m["id"] for m in r_list.json()}

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)
