"""Тесты сервиса списка пользователей портала."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.core.exceptions import ForbiddenError
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMember
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.integrations.profile_directory.client import PhotoMeta
from app.services.portal_user import (
    assert_subs_may_use_portal_chat,
    avatar_urls_for_subs,
    bulk_last_seen_from_profile,
    list_portal_user_subs_ordered,
    list_portal_users,
    portal_user_subs_registered,
)
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import make_oidc_settings


@pytest.mark.asyncio
async def test_portal_user_subs_registered_empty_wanted(sqlite_session: AsyncSession) -> None:
    assert await portal_user_subs_registered(sqlite_session, []) == set()
    assert await portal_user_subs_registered(sqlite_session, ["", ""]) == set()


@pytest.mark.asyncio
async def test_list_portal_users_avatar_none_when_meta_has_no_photo(sqlite_session: AsyncSession) -> None:
    meta = PhotoMeta(has_photo=False, version=None)
    with patch(
        "app.services.portal_user.get_cached_photo_meta_bulk",
        new=AsyncMock(return_value={"admin": meta}),
    ):
        users, _total = await list_portal_users(sqlite_session, skip=0, limit=500)

    admin = next(u for u in users if u.sub == "admin-sub")
    assert admin.avatar_url is None


@pytest.mark.asyncio
async def test_assert_subs_may_use_portal_chat_raises_for_disallowed(sqlite_session: AsyncSession) -> None:
    sub = "blocked-chat-sub"
    sqlite_session.add(
        PortalUserProfile(
            sub=sub,
            email="b@example.com",
            full_name="Blocked",
            username="b",
            is_portal_admin=False,
            portal_chat_allowed=False,
        )
    )
    await sqlite_session.commit()
    with pytest.raises(ForbiddenError, match="чат"):
        await assert_subs_may_use_portal_chat(sqlite_session, {sub})


@pytest.mark.asyncio
async def test_list_portal_users_excludes_ghost_without_profile(sqlite_session: AsyncSession) -> None:
    """Следы в чатах без живого профиля не попадают в пикер создания диалога."""
    ghost_sub = "ghost-deleted-user"
    now = now_utc()
    chat = PortalChat(
        title="Старый чат",
        created_by_sub="admin-sub",
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(chat)
    await sqlite_session.flush()
    sqlite_session.add(PortalChatMember(chat_id=chat.id, user_sub=ghost_sub, joined_at=now))
    await sqlite_session.commit()

    users, _total = await list_portal_users(sqlite_session, skip=0, limit=500)
    assert ghost_sub not in {u.sub for u in users}
    subs, _ = await list_portal_user_subs_ordered(sqlite_session, skip=0, limit=500)
    assert ghost_sub not in subs
    assert await portal_user_subs_registered(sqlite_session, {ghost_sub}) == set()
    with pytest.raises(ForbiddenError, match="чат"):
        await assert_subs_may_use_portal_chat(sqlite_session, {ghost_sub})


@pytest.mark.asyncio
async def test_list_portal_users_hides_fired_and_test_emails(sqlite_session: AsyncSession) -> None:
    await sqlite_session.execute(delete(PortalUserProfile))
    sqlite_session.add(PortalUserProfile(sub="ok-sub", email="ok@em.test", full_name="Ok", portal_chat_allowed=True))
    sqlite_session.add(
        PortalUserProfile(
            sub="fired-sub",
            email="fired@em.test",
            full_name="Fired",
            portal_chat_allowed=True,
        )
    )
    sqlite_session.add(
        PortalUserProfile(
            sub="test-sub",
            email="test.managerau@em.test",
            full_name="Test",
            portal_chat_allowed=True,
        )
    )
    await sqlite_session.commit()
    hidden = {"fired@em.test", "test.managerau@em.test"}
    with patch(
        "app.services.portal_user.hidden_emails_for_directory",
        new=AsyncMock(return_value=hidden),
    ):
        users, total = await list_portal_users(sqlite_session, skip=0, limit=500, http=AsyncMock())
        subs, subs_total = await list_portal_user_subs_ordered(sqlite_session, skip=0, limit=500, http=AsyncMock())
    assert {u.sub for u in users} == {"ok-sub"}
    assert total == 1
    assert subs == ["ok-sub"]
    assert subs_total == 1


@pytest.mark.asyncio
async def test_list_portal_users_hides_other_dept_and_autasks_emails(
    sqlite_session: AsyncSession,
) -> None:
    await sqlite_session.execute(delete(PortalUserProfile))
    sqlite_session.add(
        PortalUserProfile(
            sub="au-sub",
            email="sofia@em.test",
            full_name="Sofia",
            portal_chat_allowed=True,
            gid_number="10000",
        )
    )
    sqlite_session.add(
        PortalUserProfile(
            sub="dev-sub",
            email="hidden.three@example.com",
            full_name="Hidden Three",
            portal_chat_allowed=True,
            gid_number="10000",
        )
    )
    sqlite_session.add(
        PortalUserProfile(
            sub="other-gid",
            email="ceo@em.test",
            full_name="Other Dept",
            portal_chat_allowed=True,
            gid_number="20000",
        )
    )
    await sqlite_session.commit()
    with patch(
        "app.services.portal_user.hidden_emails_for_directory",
        new=AsyncMock(return_value=set()),
    ):
        users, total = await list_portal_users(sqlite_session, skip=0, limit=500, http=AsyncMock())
    assert {u.sub for u in users} == {"au-sub"}
    assert total == 1


@pytest.mark.asyncio
async def test_bulk_last_seen_from_profile_returns_map(sqlite_session: AsyncSession) -> None:
    from datetime import UTC

    seen = now_utc()
    row = await sqlite_session.get(PortalUserProfile, "admin-sub")
    assert row is not None
    row.last_seen_at = seen
    await sqlite_session.commit()

    out = await bulk_last_seen_from_profile(sqlite_session, ["admin-sub", "missing-sub"])
    got = out["admin-sub"]
    assert got is not None
    if got.tzinfo is None:
        got = got.replace(tzinfo=UTC)
    assert got == seen
    assert "missing-sub" not in out


@pytest.mark.asyncio
async def test_bulk_last_seen_from_profile_empty_wanted(sqlite_session: AsyncSession) -> None:
    assert await bulk_last_seen_from_profile(sqlite_session, []) == {}
    assert await bulk_last_seen_from_profile(sqlite_session, ["", ""]) == {}


@pytest.mark.asyncio
async def test_avatar_urls_for_subs_empty(sqlite_session: AsyncSession) -> None:
    assert await avatar_urls_for_subs(sqlite_session, []) == {}
    assert await avatar_urls_for_subs(sqlite_session, ["", ""]) == {}


@pytest.mark.asyncio
async def test_avatar_urls_for_subs_unknown_sub_omitted(sqlite_session: AsyncSession) -> None:
    assert await avatar_urls_for_subs(sqlite_session, ["no-such-sub"]) == {}


@pytest.mark.asyncio
async def test_avatar_urls_for_subs_none_when_meta_has_no_photo(sqlite_session: AsyncSession) -> None:
    meta = PhotoMeta(has_photo=False, version=None)
    with patch(
        "app.services.portal_user.get_cached_photo_meta_bulk",
        new=AsyncMock(return_value={"admin": meta}),
    ):
        out = await avatar_urls_for_subs(sqlite_session, ["admin-sub"])
    assert out["admin-sub"] is None


@pytest.mark.asyncio
async def test_avatar_urls_for_subs_proxy_when_has_photo(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_oidc_settings(
        profile_directory_base_url="https://ea.example",
        admin_session_secret="dev-secret-change-me",
    )
    monkeypatch.setattr("app.services.user_photo_url.get_settings", lambda: settings)
    meta = PhotoMeta(has_photo=True, version=2)
    with patch(
        "app.services.portal_user.get_cached_photo_meta_bulk",
        new=AsyncMock(return_value={"admin": meta}),
    ):
        out = await avatar_urls_for_subs(sqlite_session, ["admin-sub", "admin-sub", ""])
    url = out["admin-sub"]
    assert url is not None
    assert "/portal/users/admin-sub/photo" in url
    assert "v=2" in url
