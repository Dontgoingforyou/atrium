"""Тесты Web Push: нормализация VAPID, подписки, фоновая отправка."""

from __future__ import annotations

import builtins
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.exceptions import ValidationError
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMember
from app.infrastructure.db.models.portal_web_push import PortalWebPushSubscription
from app.portal_chat.schemas.chat import PortalChatCreate
from app.portal_chat.services import chat as chat_svc
from app.portal_chat.services.web_push import (
    delete_push_subscription,
    send_chat_message_web_push_bg,
    upsert_push_subscription,
)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid.utils import b64urlencode
from pywebpush import WebPushException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.conftest import make_oidc_settings
from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular


def _generate_ec_vapid_pem_and_public_b64() -> tuple[str, str]:
    priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    pub_b64 = b64urlencode(pub_raw)
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return pem, pub_b64


@pytest.mark.asyncio
async def test_upsert_push_subscription_invalid_keys_raises(
    sqlite_session: AsyncSession,
) -> None:
    user = user_portal_admin()
    with pytest.raises(ValidationError, match="Некорректные ключи подписки"):
        await upsert_push_subscription(
            sqlite_session,
            user,
            {"endpoint": "https://push.example/ep1", "keys": {"p256dh": "x", "auth": ""}},
        )


@pytest.mark.asyncio
async def test_upsert_push_subscription_insert_then_update(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    ep = f"https://push.example/{uuid.uuid4()}"
    data = {
        "endpoint": ep,
        "keys": {"p256dh": "p256dh-val", "auth": "auth-val"},
    }
    await upsert_push_subscription(sqlite_session, admin, data)
    row = (
        await sqlite_session.execute(select(PortalWebPushSubscription).where(PortalWebPushSubscription.endpoint == ep))
    ).scalar_one()
    assert row.user_sub == admin.sub
    assert row.p256dh == "p256dh-val"

    data2 = {
        "endpoint": ep,
        "keys": {"p256dh": "p256-new", "auth": "auth-new"},
    }
    await upsert_push_subscription(sqlite_session, regular, data2)
    await sqlite_session.refresh(row)
    assert row.user_sub == regular.sub
    assert row.p256dh == "p256-new"
    assert row.auth == "auth-new"


@pytest.mark.asyncio
async def test_delete_push_subscription_removes_row(
    sqlite_session: AsyncSession,
) -> None:
    user = user_portal_admin()
    ep = f"https://push.example/{uuid.uuid4()}"
    sqlite_session.add(
        PortalWebPushSubscription(
            user_sub=user.sub,
            endpoint=ep,
            p256dh="k",
            auth="a",
        )
    )
    await sqlite_session.commit()

    await delete_push_subscription(sqlite_session, user, ep)
    left = (
        await sqlite_session.execute(select(PortalWebPushSubscription).where(PortalWebPushSubscription.endpoint == ep))
    ).scalar_one_or_none()
    assert left is None


def _patch_web_push_settings(monkeypatch: pytest.MonkeyPatch, **vapid_over: Any) -> None:
    pem, pub = _generate_ec_vapid_pem_and_public_b64()
    s = make_oidc_settings(
        vapid_private_key=vapid_over.get("vapid_private_key", pem),
        vapid_public_key=vapid_over.get("vapid_public_key", pub),
        vapid_contact_email=vapid_over.get("vapid_contact_email", "notify@test.local"),
        portal_public_url=vapid_over.get("portal_public_url", "https://spa.example"),
    )
    monkeypatch.setattr("app.portal_chat.services.web_push.get_settings", lambda: s)


async def _eager_asyncio_to_thread(func: Any, /, *args: Any, **kwargs: Any) -> Any:
    if args or kwargs:
        return func(*args, **kwargs)
    return func()


@pytest.mark.asyncio
async def test_send_chat_message_web_push_bg_no_vapid_returns_early(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = make_oidc_settings(vapid_private_key="", vapid_public_key="", vapid_contact_email="")
    monkeypatch.setattr("app.portal_chat.services.web_push.get_settings", lambda: s)
    with patch("pywebpush.webpush") as wp:
        await send_chat_message_web_push_bg(
            uuid.uuid4(),
            "a",
            "hi",
            None,
            True,
            message_id=uuid.uuid4(),
        )
    wp.assert_not_called()


@pytest.mark.asyncio
async def test_send_chat_message_web_push_bg_truncated_pem_logs_and_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_web_push_settings(monkeypatch, vapid_private_key="-----BEGIN PRIVATE KEY-----\nABC")
    with (
        patch("pywebpush.webpush") as wp,
        patch("app.portal_chat.services.web_push.logger") as log,
    ):
        await send_chat_message_web_push_bg(uuid.uuid4(), "a", "x", None, False)
    wp.assert_not_called()
    log.error.assert_called()


@pytest.mark.asyncio
async def test_send_chat_message_web_push_bg_invalid_vapid_parse_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_web_push_settings(
        monkeypatch,
        vapid_private_key="-----BEGIN PRIVATE KEY-----\nINVALID\n-----END PRIVATE KEY-----\n",
    )
    with (
        patch("pywebpush.webpush") as wp,
        patch("app.portal_chat.services.web_push.logger") as log,
    ):
        await send_chat_message_web_push_bg(uuid.uuid4(), "a", "x", None, True)
    wp.assert_not_called()
    log.exception.assert_called()


@pytest.mark.asyncio
async def test_send_chat_message_web_push_bg_pytest_skip_guard_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_web_push_settings(monkeypatch)
    with patch("pywebpush.webpush") as wp:
        await send_chat_message_web_push_bg(uuid.uuid4(), "a", "x", "T", False)
    wp.assert_not_called()


@pytest.mark.asyncio
async def test_send_chat_message_web_push_bg_import_error_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_web_push_settings(monkeypatch)
    real_import = builtins.__import__

    def _deny_pywebpush(
        name: str,
        globals_: Any = None,
        locals_: Any = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "pywebpush":
            raise ImportError("stub")
        return real_import(name, globals_, locals_, fromlist, level)

    with (
        patch("app.portal_chat.services.web_push.skip_background_tasks_using_global_engine", return_value=False),
        patch("builtins.__import__", side_effect=_deny_pywebpush),
        patch("app.portal_chat.services.web_push.logger") as log,
    ):
        await send_chat_message_web_push_bg(uuid.uuid4(), "a", "x", None, True)
    log.warning.assert_called()


@pytest.mark.asyncio
async def test_send_chat_message_web_push_bg_no_recipients_returns(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_web_push_settings(monkeypatch)
    now = datetime.now(UTC)
    chat_id = uuid.uuid4()
    sqlite_session.add(
        PortalChat(
            id=chat_id,
            title="Solo",
            created_by_sub="solo-sub",
            created_at=now,
            updated_at=now,
            canonical_dm_key=None,
        )
    )
    sqlite_session.add(PortalChatMember(chat_id=chat_id, user_sub="solo-sub", joined_at=now))
    await sqlite_session.commit()

    factory = async_sessionmaker(sqlite_session.bind, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("app.infrastructure.db.session.async_session_factory", factory)

    with (
        patch("app.portal_chat.services.web_push.skip_background_tasks_using_global_engine", return_value=False),
        patch("app.portal_chat.services.web_push.asyncio.to_thread", new=_eager_asyncio_to_thread),
        patch("pywebpush.webpush") as wp,
    ):
        await send_chat_message_web_push_bg(chat_id, "solo-sub", "hello", None, False)
    wp.assert_not_called()


@pytest.mark.asyncio
async def test_send_chat_message_web_push_bg_dm_calls_webpush(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_web_push_settings(monkeypatch, vapid_contact_email="mailto:ops@example.com")
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, regular.sub)
    ep = f"https://push.example/{uuid.uuid4()}"
    sqlite_session.add(
        PortalWebPushSubscription(
            user_sub=regular.sub,
            endpoint=ep,
            p256dh="pk",
            auth="ak",
        )
    )
    await sqlite_session.commit()

    factory = async_sessionmaker(sqlite_session.bind, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("app.infrastructure.db.session.async_session_factory", factory)

    mid = uuid.uuid4()
    with (
        patch("app.portal_chat.services.web_push.skip_background_tasks_using_global_engine", return_value=False),
        patch("app.portal_chat.services.web_push.asyncio.to_thread", new=_eager_asyncio_to_thread),
        patch("pywebpush.webpush") as wp,
    ):
        await send_chat_message_web_push_bg(
            chat.id,
            admin.sub,
            "  Привет  ",
            None,
            True,
            message_id=mid,
        )

    wp.assert_called_once()
    _args, kwargs = wp.call_args
    assert kwargs["vapid_claims"]["sub"] == "mailto:ops@example.com"
    payload = kwargs["data"]
    assert "Привет" in payload
    assert str(chat.id) in payload
    assert str(mid) in payload


@pytest.mark.asyncio
async def test_send_chat_message_web_push_bg_group_skips_when_unread_threshold(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_web_push_settings(monkeypatch)
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="G", member_subs=[regular.sub]),
    )
    ep = f"https://push.example/{uuid.uuid4()}"
    sqlite_session.add(
        PortalWebPushSubscription(
            user_sub=regular.sub,
            endpoint=ep,
            p256dh="pk",
            auth="ak",
        )
    )
    await sqlite_session.commit()

    factory = async_sessionmaker(sqlite_session.bind, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("app.infrastructure.db.session.async_session_factory", factory)

    with (
        patch("app.portal_chat.services.web_push.skip_background_tasks_using_global_engine", return_value=False),
        patch("app.portal_chat.services.web_push.asyncio.to_thread", new=_eager_asyncio_to_thread),
        patch(
            "app.portal_chat.services.web_push.get_unread_counts_for_chat_members",
            new_callable=AsyncMock,
            return_value={regular.sub: 5},
        ),
        patch("pywebpush.webpush") as wp,
    ):
        await send_chat_message_web_push_bg(chat.id, admin.sub, "m", "Группа", False)

    wp.assert_not_called()


@pytest.mark.asyncio
async def test_send_chat_message_web_push_bg_webpush_410_deletes_subscription(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_web_push_settings(monkeypatch)
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, regular.sub)
    ep = f"https://push.example/{uuid.uuid4()}"
    sub = PortalWebPushSubscription(
        user_sub=regular.sub,
        endpoint=ep,
        p256dh="pk",
        auth="ak",
    )
    sqlite_session.add(sub)
    await sqlite_session.commit()
    sub_id = sub.id

    factory = async_sessionmaker(sqlite_session.bind, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("app.infrastructure.db.session.async_session_factory", factory)

    gone = WebPushException("gone", response=MagicMock(status_code=410))
    with (
        patch("app.portal_chat.services.web_push.skip_background_tasks_using_global_engine", return_value=False),
        patch("app.portal_chat.services.web_push.asyncio.to_thread", new=_eager_asyncio_to_thread),
        patch("pywebpush.webpush", side_effect=gone),
    ):
        await send_chat_message_web_push_bg(chat.id, admin.sub, "x", None, True)

    row = (
        await sqlite_session.execute(select(PortalWebPushSubscription).where(PortalWebPushSubscription.id == sub_id))
    ).scalar_one_or_none()
    assert row is None


@pytest.mark.asyncio
async def test_send_chat_message_web_push_bg_webpush_other_status_warns(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_web_push_settings(monkeypatch)
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, regular.sub)
    sqlite_session.add(
        PortalWebPushSubscription(
            user_sub=regular.sub,
            endpoint=f"https://push.example/{uuid.uuid4()}",
            p256dh="pk",
            auth="ak",
        )
    )
    await sqlite_session.commit()

    factory = async_sessionmaker(sqlite_session.bind, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("app.infrastructure.db.session.async_session_factory", factory)

    err = WebPushException("fail", response=MagicMock(status_code=503))
    with (
        patch("app.portal_chat.services.web_push.skip_background_tasks_using_global_engine", return_value=False),
        patch("app.portal_chat.services.web_push.asyncio.to_thread", new=_eager_asyncio_to_thread),
        patch("pywebpush.webpush", side_effect=err),
        patch("app.portal_chat.services.web_push.logger") as log,
    ):
        await send_chat_message_web_push_bg(chat.id, admin.sub, "x", None, True)

    log.warning.assert_called()


@pytest.mark.asyncio
async def test_send_chat_message_web_push_bg_webpush_unexpected_exception_logs(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_web_push_settings(monkeypatch)
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, regular.sub)
    sqlite_session.add(
        PortalWebPushSubscription(
            user_sub=regular.sub,
            endpoint=f"https://push.example/{uuid.uuid4()}",
            p256dh="pk",
            auth="ak",
        )
    )
    await sqlite_session.commit()

    factory = async_sessionmaker(sqlite_session.bind, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("app.infrastructure.db.session.async_session_factory", factory)

    with (
        patch("app.portal_chat.services.web_push.skip_background_tasks_using_global_engine", return_value=False),
        patch("app.portal_chat.services.web_push.asyncio.to_thread", new=_eager_asyncio_to_thread),
        patch("pywebpush.webpush", side_effect=RuntimeError("boom")),
        patch("app.portal_chat.services.web_push.logger") as log,
    ):
        await send_chat_message_web_push_bg(chat.id, admin.sub, "x", None, True)

    log.exception.assert_called()
