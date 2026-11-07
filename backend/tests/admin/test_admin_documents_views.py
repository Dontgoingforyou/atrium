"""Юнит-тесты SQLAdmin-вьюх и форматтеров документов (`app.admin.views.documents`)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.admin.views.document_history import (
    PortalDocumentHistoryAdmin,
    PortalDocumentTagAdmin,
    _fmt_editor,
)
from app.admin.views.documents import (
    PortalDocumentAdmin,
    PortalTagAdmin,
    _fmt_author,
)
from starlette.requests import Request


@pytest.mark.parametrize(
    ("name", "email", "expected"),
    [
        ("Иван", "i@example.com", "Иван (i@example.com)"),
        ("", "only@mail.test", "only@mail.test"),
        ("Пётр", "", "Пётр"),
        ("", "", "—"),
    ],
)
def test_fmt_author_variants(name: str, email: str, expected: str) -> None:
    model = SimpleNamespace(author_display_name=name, author_email=email)
    assert _fmt_author(model, "author_display_name") == expected


@pytest.mark.parametrize(
    ("profile", "display_name", "email", "sub", "expected"),
    [
        (
            SimpleNamespace(full_name="Иван", email="i@example.com"),
            "ignored",
            "ignored@x.test",
            "sub1",
            "Иван (i@example.com)",
        ),
        (SimpleNamespace(full_name="Пётр", email=""), "ignored", "", "sub2", "Пётр"),
        (SimpleNamespace(full_name="", email="e@mail.test"), "", "", "sub3", "e@mail.test"),
        (None, "Редактор", "ed@mail.test", "sub4", "Редактор (ed@mail.test)"),
        (None, "", "only@mail.test", "sub5", "only@mail.test"),
        (None, "Только имя", "", "sub6", "Только имя"),
        (None, "", "", "fallback-sub", "fallback-sub"),
        (None, "", "", "", "—"),
    ],
)
def test_fmt_editor_variants(
    profile: SimpleNamespace | None,
    display_name: str,
    email: str,
    sub: str,
    expected: str,
) -> None:
    model = SimpleNamespace(
        changed_by_profile=profile,
        changed_by_display_name=display_name,
        changed_by_email=email,
        changed_by_sub=sub,
    )
    assert _fmt_editor(model, "changed_by_display_name") == expected


def test_document_admin_crud_flags() -> None:
    assert PortalDocumentAdmin.can_delete is False
    assert PortalDocumentAdmin.can_create is True
    assert PortalDocumentAdmin.can_edit is True
    assert PortalDocumentTagAdmin.can_edit is False
    assert PortalDocumentTagAdmin.can_create is True
    assert PortalDocumentHistoryAdmin.can_create is False
    assert PortalDocumentHistoryAdmin.can_edit is False
    assert PortalDocumentHistoryAdmin.can_delete is True


@pytest.mark.asyncio
async def test_portal_tag_admin_on_model_change_skips_empty_name() -> None:
    admin = PortalTagAdmin()
    data: dict = {"name": "   ", "slug": "old-slug"}
    await admin.on_model_change(data, None, True, MagicMock())
    assert data == {"name": "   ", "slug": "old-slug", "version": 1}


@pytest.mark.asyncio
async def test_portal_tag_admin_on_model_change_resolves_slug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolve = AsyncMock(return_value=("Мой тег", "moi-teg"))
    monkeypatch.setattr(
        "app.admin.views.documents.portal_tags_svc.resolve_name_and_slug_for_admin_form",
        resolve,
    )

    class _SessionCtx:
        async def __aenter__(self) -> MagicMock:
            return MagicMock()

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        "app.admin.views.documents.async_session_factory",
        lambda: _SessionCtx(),
    )

    tag_id = uuid.uuid4()
    admin = PortalTagAdmin()
    data: dict = {"name": "  Мой тег  "}
    model = SimpleNamespace(id=tag_id)

    await admin.on_model_change(data, model, False, MagicMock())

    assert data["name"] == "Мой тег"
    assert data["slug"] == "moi-teg"
    resolve.assert_awaited_once()
    assert resolve.await_args.kwargs["raw_name"] == "  Мой тег  "
    assert resolve.await_args.kwargs["exclude_tag_id"] == tag_id


@pytest.mark.asyncio
async def test_portal_tag_admin_on_model_change_create_exclude_id_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolve = AsyncMock(return_value=("Новый", "novyi"))
    monkeypatch.setattr(
        "app.admin.views.documents.portal_tags_svc.resolve_name_and_slug_for_admin_form",
        resolve,
    )

    class _SessionCtx:
        async def __aenter__(self) -> MagicMock:
            return MagicMock()

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        "app.admin.views.documents.async_session_factory",
        lambda: _SessionCtx(),
    )

    admin = PortalTagAdmin()
    data: dict = {"name": "Новый"}
    await admin.on_model_change(data, None, True, MagicMock())
    assert resolve.await_args.kwargs["exclude_tag_id"] is None


@pytest.mark.asyncio
async def test_portal_document_admin_on_model_change_normalizes_tags_list() -> None:
    admin = PortalDocumentAdmin()
    data: dict = {
        "tags": ["  a  ", "", None, "b"],
    }
    await admin.on_model_change(data, None, True, MagicMock())
    assert data["tags"] == ["a", "b"]


@pytest.mark.asyncio
async def test_portal_document_admin_on_model_change_normalizes_tags_string() -> None:
    admin = PortalDocumentAdmin()
    data: dict = {
        "tags": " x , , y ",
    }
    await admin.on_model_change(data, None, False, MagicMock())
    assert data["tags"] == ["x", "y"]


@pytest.mark.asyncio
async def test_portal_document_admin_on_model_change_author_and_owner_from_picker() -> None:
    admin = PortalDocumentAdmin()
    author = SimpleNamespace(sub="author-sub", full_name="Автор", email="a@example.com")
    owner = SimpleNamespace(sub="owner-sub", full_name="Владелец", email="o@example.com")
    data: dict = {
        "author_user": author,
        "owner_user": owner,
    }
    await admin.on_model_change(data, None, False, MagicMock())
    assert data["author_sub"] == "author-sub"
    assert data["author_display_name"] == "Автор"
    assert data["author_email"] == "a@example.com"
    assert data["owner_sub"] == "owner-sub"
    assert data["owner_email"] == "o@example.com"


@pytest.mark.asyncio
async def test_portal_document_admin_on_model_change_author_from_session_on_create() -> None:
    admin = PortalDocumentAdmin()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/admin/portal-document/create",
        "session": {
            "admin_sub": "session-sub",
            "admin_full_name": "Админ",
            "admin_email": "admin@example.com",
        },
    }
    req = Request(scope)
    data: dict = {}
    await admin.on_model_change(data, None, True, req)
    assert data["author_sub"] == "session-sub"
    assert data["author_display_name"] == "Админ"
    assert data["author_email"] == "admin@example.com"


@pytest.mark.asyncio
async def test_portal_document_admin_edit_does_not_overwrite_author_from_session() -> None:
    admin = PortalDocumentAdmin()
    data: dict = {
        "author_sub": "original-sub",
        "author_display_name": "Оригинал",
        "author_email": "orig@example.com",
    }
    await admin.on_model_change(data, None, False, _admin_session_request())
    assert data["author_sub"] == "original-sub"
    assert data["author_display_name"] == "Оригинал"
    assert data["author_email"] == "orig@example.com"


@pytest.mark.asyncio
async def test_portal_document_admin_tags_none_is_noop() -> None:
    admin = PortalDocumentAdmin()
    data: dict = {"tags": None}
    await admin.on_model_change(data, None, False, MagicMock())
    assert data["tags"] is None


@pytest.mark.asyncio
async def test_portal_document_admin_author_without_sub_on_create_uses_session() -> None:
    admin = PortalDocumentAdmin()
    data: dict = {"author_user": SimpleNamespace(full_name="X", email="x@t")}
    await admin.on_model_change(data, None, True, _admin_session_request())
    assert data["author_sub"] == "admin-sub"
    assert data["author_display_name"] == "Админ"
    assert data["author_email"] == "admin@example.com"


@pytest.mark.asyncio
async def test_portal_document_admin_author_without_sub_on_edit_leaves_author() -> None:
    admin = PortalDocumentAdmin()
    data: dict = {
        "author_user": SimpleNamespace(full_name="X", email="x@t"),
        "author_sub": "kept-sub",
        "author_display_name": "Kept",
        "author_email": "k@t",
    }
    await admin.on_model_change(data, None, False, _admin_session_request())
    assert data["author_sub"] == "kept-sub"
    assert data["author_display_name"] == "Kept"
    assert data["author_email"] == "k@t"


@pytest.mark.asyncio
async def test_portal_document_admin_create_empty_session_sets_empty_author_sub() -> None:
    admin = PortalDocumentAdmin()
    req = Request({"type": "http", "method": "POST", "path": "/admin/portal-document/create", "session": {}})
    data: dict = {}
    await admin.on_model_change(data, None, True, req)
    assert data["author_sub"] == ""


def _admin_session_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/admin/portal-document/edit",
        "session": {
            "admin_sub": "admin-sub",
            "admin_full_name": "Админ",
            "admin_email": "admin@example.com",
        },
    }
    return Request(scope)


class _SessionCtx:
    def __init__(self) -> None:
        self.commit = AsyncMock()

    async def __aenter__(self) -> _SessionCtx:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.mark.asyncio
async def test_portal_document_admin_after_model_change_writes_history_and_publishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_ctx = _SessionCtx()
    monkeypatch.setattr("app.admin.views.documents.async_session_factory", lambda: session_ctx)
    write_history = AsyncMock()
    monkeypatch.setattr("app.admin.views.documents.write_document_history", write_history)
    publish = AsyncMock()
    monkeypatch.setattr("app.admin.views.documents.publish_document_mutation", publish)

    admin = PortalDocumentAdmin()
    doc_id = uuid.uuid4()
    model = SimpleNamespace(id=doc_id, parent_document_id=None)

    await admin.after_model_change({}, model, True, _admin_session_request())

    session_ctx.commit.assert_awaited_once()
    write_history.assert_awaited_once()
    args, kwargs = write_history.await_args
    assert args[0] is session_ctx
    assert args[1] == doc_id
    assert args[2] == "admin-sub"
    assert args[3] == {"action": {"old": None, "new": "created"}}
    assert kwargs["changed_by_display_name"] == "Админ"
    assert kwargs["changed_by_email"] == "admin@example.com"
    publish.assert_awaited_once_with(document_id=doc_id, parent_document_id=None)


@pytest.mark.asyncio
async def test_portal_document_admin_after_model_change_update_action_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.admin.views.documents.async_session_factory", lambda: _SessionCtx())
    write_history = AsyncMock()
    monkeypatch.setattr("app.admin.views.documents.write_document_history", write_history)
    monkeypatch.setattr("app.admin.views.documents.publish_document_mutation", AsyncMock())

    admin = PortalDocumentAdmin()
    model = SimpleNamespace(id=uuid.uuid4(), parent_document_id=None)

    await admin.after_model_change({}, model, False, _admin_session_request())

    assert write_history.await_args.args[3] == {"action": {"old": None, "new": "updated"}}


@pytest.mark.asyncio
async def test_portal_document_admin_after_model_change_swallows_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Документ уже сохранён (после commit sqladmin) — сбой аудита не должен всплывать наружу."""
    monkeypatch.setattr("app.admin.views.documents.async_session_factory", lambda: _SessionCtx())
    monkeypatch.setattr(
        "app.admin.views.documents.write_document_history",
        AsyncMock(side_effect=RuntimeError("db unavailable")),
    )
    publish = AsyncMock()
    monkeypatch.setattr("app.admin.views.documents.publish_document_mutation", publish)

    admin = PortalDocumentAdmin()
    model = SimpleNamespace(id=uuid.uuid4(), parent_document_id=None)

    await admin.after_model_change({}, model, True, _admin_session_request())  # не должно поднять исключение

    publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_portal_document_admin_after_model_change_publish_fail_keeps_history_commit(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session_ctx = _SessionCtx()
    monkeypatch.setattr("app.admin.views.documents.async_session_factory", lambda: session_ctx)
    write_history = AsyncMock()
    monkeypatch.setattr("app.admin.views.documents.write_document_history", write_history)
    monkeypatch.setattr(
        "app.admin.views.documents.publish_document_mutation",
        AsyncMock(side_effect=RuntimeError("redis down")),
    )

    admin = PortalDocumentAdmin()
    model = SimpleNamespace(id=uuid.uuid4(), parent_document_id=None)

    with caplog.at_level("ERROR"):
        await admin.after_model_change({}, model, True, _admin_session_request())

    session_ctx.commit.assert_awaited_once()
    write_history.assert_awaited_once()
    assert "Не удалось записать историю" in caplog.text
