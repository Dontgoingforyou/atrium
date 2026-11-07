"""Юнит-тесты SQLAdmin и форматтеров portal_collab."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request


def test_fmt_agreement_body_preview_truncates() -> None:
    from app.portal_collab.admin.agreements import _fmt_agreement_body_preview

    long_body = "а" * 150
    out = _fmt_agreement_body_preview(SimpleNamespace(body=long_body), "body")
    assert len(out) == 121
    assert out.endswith("…")
    short = _fmt_agreement_body_preview(SimpleNamespace(body="коротко"), "body")
    assert short == "коротко"


@pytest.mark.asyncio
async def test_portal_agreement_admin_on_model_change() -> None:
    from app.portal_collab.admin.agreements import PortalAgreementAdmin

    admin = PortalAgreementAdmin()
    data: dict = {
        "document": ["__None"],
        "task": [],
        "source_message": "__None",
        "created_by_user": SimpleNamespace(sub="author-from-form"),
    }
    await admin.on_model_change(data, None, True, MagicMock())
    assert data["document"] is None
    assert data["task"] is None
    assert data["source_message"] is None
    assert data["created_by_sub"] == "author-from-form"


def test_portal_collab_formatters_resolve_user_and_mentions() -> None:
    from app.portal_collab.admin.formatters import (
        fmt_assignee_sub,
        fmt_author_sub,
        fmt_changed_by,
        fmt_comment_mentions,
        fmt_comment_parent_id,
        fmt_created_by,
        fmt_creator_sub,
        fmt_mentioned_names,
        fmt_user_sub,
    )

    profile = SimpleNamespace(full_name="Иван", email="i@example.com", username="iv", sub="s1")
    assert (
        fmt_created_by(SimpleNamespace(created_by_profile=profile, created_by_sub="s1"), "x") == "Иван (i@example.com)"
    )
    email_only = SimpleNamespace(full_name=None, email="only@mail.test", username=None)
    assert fmt_author_sub(SimpleNamespace(author_profile=email_only, author_sub="s"), "x") == "only@mail.test"
    assert fmt_author_sub(SimpleNamespace(author_profile=None, author_sub="only-sub"), "x") == "only-sub"
    assert fmt_user_sub(SimpleNamespace(user_profile=None, user_sub=None), "x") == "—"
    assert fmt_creator_sub(SimpleNamespace(creator_profile=None, creator_sub=None), "x") == "—"
    assert fmt_changed_by(SimpleNamespace(changed_by_profile=None, changed_by_sub="u"), "x") == "u"
    assert fmt_assignee_sub(SimpleNamespace(assignee_profile=None, assignee_sub=None), "x") == "—"
    assert fmt_assignee_sub(SimpleNamespace(assignee_profile=profile, assignee_sub="s1"), "x") == "Иван (i@example.com)"

    assert str(fmt_comment_mentions(SimpleNamespace(mentions=[], attr=[]), "mentions")) == "—"
    long_sub = "verylongsubnamexxx"
    m = fmt_comment_mentions(SimpleNamespace(mentions=[long_sub], attr="mentions"), "mentions")
    assert "verylongsubn…" in str(m)
    prof_b = SimpleNamespace(sub="user-b", full_name="B", email=None, username=None)
    m2 = fmt_comment_mentions(
        SimpleNamespace(
            mentions=["user-b"],
            _mentioned_profiles_cache=[prof_b],
            attr="mentions",
        ),
        "mentions",
    )
    assert "B" in str(m2)

    assert str(fmt_mentioned_names(SimpleNamespace(mentioned_names=None), "mentioned_names")) == "—"
    assert "Alpha" in str(fmt_mentioned_names(SimpleNamespace(mentioned_names="Alpha, Beta"), "mentioned_names"))
    assert str(fmt_mentioned_names(SimpleNamespace(mentioned_names="  ,  "), "mentioned_names")) == "—"

    pid = uuid.uuid4()
    assert fmt_comment_parent_id(SimpleNamespace(parent_id=None), "parent_id") == "—"
    assert "Ответ на комментарий" in fmt_comment_parent_id(SimpleNamespace(parent_id=pid), "parent_id")


def test_fmt_comment_mentions_escapes_html() -> None:
    from app.portal_collab.admin.formatters import fmt_comment_mentions, fmt_mentioned_names

    evil_profile = SimpleNamespace(
        sub="s1",
        full_name="<script>alert(1)</script>",
        email=None,
        username=None,
    )
    mentions = fmt_comment_mentions(
        SimpleNamespace(
            mentions=["s1"],
            _mentioned_profiles_cache=[evil_profile],
        ),
        "mentions",
    )
    s = str(mentions)
    assert "<script>" not in s
    assert "&lt;script&gt;" in s

    names = fmt_mentioned_names(
        SimpleNamespace(mentioned_names="<img onerror=alert(1)>, Safe"),
        "mentioned_names",
    )
    ns = str(names)
    assert "<img " not in ns
    assert "&lt;img" in ns
    assert "Safe" in ns


def test_fmt_status_key_known_and_unknown() -> None:
    from app.portal_collab.admin.tasks import _fmt_status_key

    assert "К выполнению" in _fmt_status_key(SimpleNamespace(status_key="todo"), "status_key")
    assert _fmt_status_key(SimpleNamespace(status_key="custom_key"), "status_key") == "custom_key"


@pytest.mark.asyncio
async def test_portal_task_comment_admin_on_model_change_sets_author_sub() -> None:
    from app.portal_collab.admin.tasks import PortalTaskCommentAdmin

    admin = PortalTaskCommentAdmin()
    data: dict = {"author_user": SimpleNamespace(sub="author-from-form")}
    await admin.on_model_change(data, None, False, MagicMock())
    assert data["author_sub"] == "author-from-form"


def test_portal_task_comment_admin_details_query() -> None:
    from app.portal_collab.admin.tasks import PortalTaskCommentAdmin

    req = Request({"type": "http", "method": "GET", "path": "/admin/portal-task-comment/details"})
    dq = PortalTaskCommentAdmin().details_query(req)
    sql = str(dq).lower()
    assert "portal_task_comment" in sql
    assert "mentioned_names" in sql or "parent" in sql


@pytest.mark.asyncio
async def test_task_link_chat_loader_get_list() -> None:
    from app.infrastructure.db.models.portal_chat import PortalChat
    from app.portal_collab.admin.tasks import _TaskLinkChatLoader

    mock_admin = MagicMock()
    mock_admin._run_query = AsyncMock(return_value=[])
    loader = _TaskLinkChatLoader(
        "chat",
        PortalChat,
        mock_admin,
        fields=(PortalChat.title,),
        order_by=PortalChat.title,
    )

    out = await loader.get_list("поиск")
    assert out == []
    mock_admin._run_query.assert_awaited_once()

    mock_admin._run_query.reset_mock()
    loader.order_by = [PortalChat.title]
    out = await loader.get_list("поиск")
    assert out == []
    mock_admin._run_query.assert_awaited_once()


@pytest.mark.asyncio
async def test_portal_time_entry_admin_on_model_change_sets_user_sub() -> None:
    from app.portal_collab.admin.timesheets import PortalTimeEntryAdmin

    admin = PortalTimeEntryAdmin()
    data: dict = {"user_user": SimpleNamespace(sub="timesheet-user-sub")}
    model = SimpleNamespace(updated_at=None)
    await admin.on_model_change(data, model, True, MagicMock())
    assert data["user_sub"] == "timesheet-user-sub"
    assert model.updated_at is not None
