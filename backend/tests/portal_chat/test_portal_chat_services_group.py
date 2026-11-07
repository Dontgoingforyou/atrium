"""Юнит-тесты групповых чатов (group_chat)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.portal_chat.schemas.chat import PortalChatCreate
from app.portal_chat.services import chat as chat_svc
from app.portal_chat.services import group_chat as group_svc
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b


@pytest.fixture(autouse=True)
def _mock_group_ws_and_inbox() -> object:
    mgr = MagicMock(publish=AsyncMock(), disconnect_user=AsyncMock())
    with (
        patch("app.infrastructure.ws.managers.get_chat_manager", return_value=mgr),
        patch("app.portal_chat.services.group_chat.get_chat_manager", return_value=mgr),
        patch("app.infrastructure.ws.inbox_manager.get_inbox_manager", return_value=mgr),
        patch("app.portal_chat.services.group_chat.publish_chat_list_refresh", new_callable=AsyncMock),
    ):
        yield


async def test_require_group_chat_rejects_dm(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    dm = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    with pytest.raises(ForbiddenError, match="только для группового"):
        await group_svc.patch_group_chat_title(sqlite_session, admin, dm.id, title="X", expected_version=1)


async def test_patch_group_chat_title_success(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Старое", member_subs=[user_portal_regular().sub]),
    )
    out = await group_svc.patch_group_chat_title(
        sqlite_session, admin, chat.id, title="  Новое имя  ", expected_version=chat.version
    )
    assert out.title == "Новое имя"


async def test_patch_group_chat_title_non_creator_forbidden(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Группа", member_subs=[regular.sub]),
    )
    with pytest.raises(ForbiddenError, match="только создатель"):
        await group_svc.patch_group_chat_title(
            sqlite_session, regular, chat.id, title="Взлом", expected_version=chat.version
        )


async def test_patch_group_chat_title_empty_validation(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Г", member_subs=[user_portal_regular().sub]),
    )
    with pytest.raises(ValidationError, match="не может быть пустым"):
        await group_svc.patch_group_chat_title(
            sqlite_session, admin, chat.id, title="   ", expected_version=chat.version
        )


async def test_patch_group_chat_title_truncates_to_255(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Коротко", member_subs=[user_portal_regular().sub]),
    )
    long_title = "Я" * 300
    out = await group_svc.patch_group_chat_title(
        sqlite_session, admin, chat.id, title=long_title, expected_version=chat.version
    )
    assert len(out.title) == 255
    assert out.title == "Я" * 255


async def test_add_member_success(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Команда", member_subs=[user_portal_regular().sub]),
    )
    row = await group_svc.add_member_to_group_chat(
        sqlite_session,
        admin,
        chat.id,
        new_member_sub=user_portal_user_b().sub,
    )
    assert row.user_sub == user_portal_user_b().sub
    members = await chat_svc.list_chat_members(sqlite_session, chat.id)
    subs = {m.user_sub for m in members}
    assert user_portal_user_b().sub in subs


async def test_add_member_self_validation(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Сам себе", member_subs=[user_portal_regular().sub]),
    )
    with pytest.raises(ValidationError, match="Нельзя добавить себя"):
        await group_svc.add_member_to_group_chat(sqlite_session, admin, chat.id, new_member_sub=admin.sub)


async def test_add_member_unknown_user_validation(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Известные", member_subs=[user_portal_regular().sub]),
    )
    with pytest.raises(ValidationError, match="не найден"):
        await group_svc.add_member_to_group_chat(
            sqlite_session,
            admin,
            chat.id,
            new_member_sub="totally-unknown-sub-not-in-portal",
        )


async def test_add_member_already_in_chat_conflict(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Дубль", member_subs=[regular.sub]),
    )
    with pytest.raises(ConflictError, match="уже в чате"):
        await group_svc.add_member_to_group_chat(sqlite_session, admin, chat.id, new_member_sub=regular.sub)


async def test_add_member_by_non_creator_member_allowed(sqlite_session: AsyncSession) -> None:
    """Любой участник группы может пригласить нового человека."""
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Права", member_subs=[regular.sub]),
    )
    row = await group_svc.add_member_to_group_chat(
        sqlite_session,
        regular,
        chat.id,
        new_member_sub=user_portal_user_b().sub,
    )
    assert row.user_sub == user_portal_user_b().sub


async def test_remove_member_success_kick_by_creator(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Исключение", member_subs=[regular.sub]),
    )
    await group_svc.remove_member_from_group_chat(sqlite_session, admin, chat.id, target_sub=regular.sub)
    subs = {m.user_sub for m in await chat_svc.list_chat_members(sqlite_session, chat.id)}
    assert regular.sub not in subs


async def test_remove_member_self_leave_non_creator(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Выход", member_subs=[regular.sub]),
    )
    await group_svc.remove_member_from_group_chat(sqlite_session, regular, chat.id, target_sub=regular.sub)
    subs = {m.user_sub for m in await chat_svc.list_chat_members(sqlite_session, chat.id)}
    assert regular.sub not in subs


async def test_remove_member_creator_cannot_be_removed(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Владелец", member_subs=[user_portal_regular().sub]),
    )
    with pytest.raises(ForbiddenError, match="Создатель"):
        await group_svc.remove_member_from_group_chat(sqlite_session, admin, chat.id, target_sub=admin.sub)


async def test_remove_member_outsider_forbidden(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    outsider = user_portal_user_b()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Трое", member_subs=[regular.sub, outsider.sub]),
    )
    with pytest.raises(ForbiddenError, match="только создатель"):
        await group_svc.remove_member_from_group_chat(sqlite_session, regular, chat.id, target_sub=outsider.sub)


async def test_remove_member_not_in_chat_not_found(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Двое", member_subs=[user_portal_regular().sub]),
    )
    with pytest.raises(NotFoundError, match="Участник не найден"):
        await group_svc.remove_member_from_group_chat(
            sqlite_session,
            admin,
            chat.id,
            target_sub=user_portal_user_b().sub,
        )
