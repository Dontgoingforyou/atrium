"""Параллельные CAS-update для сущностей с expected_version (кроме doc/task/material)."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.enums import TaskPriority, TaskStatus
from app.core.exceptions import ConflictError
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMember
from app.infrastructure.db.models.portal_document import PortalDocument, PortalTag
from app.infrastructure.db.models.portal_document_comment import PortalDocumentComment
from app.infrastructure.db.models.portal_learning import PortalChecklist
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskComment
from app.infrastructure.db.models.portal_time_entry import PortalTimeEntry
from app.portal_chat.services import group_chat as group_chat_svc
from app.portal_collab.schemas.task import TaskCommentUpdate
from app.portal_collab.services import task_comment as task_comment_svc
from app.portal_documents.schemas.document_comment import DocumentCommentUpdate
from app.portal_documents.services import document_comment as doc_comment_svc
from app.portal_learning.schemas.checklist import ChecklistUpdate
from app.portal_learning.services import checklist as checklist_svc
from app.portal_specialists.schemas.specialist_detail import SpecialistProfileUpdate
from app.portal_specialists.services import specialist_detail as specialist_svc
from app.portal_time_entries.schemas.time_entry import PortalTimeEntryUpdate
from app.portal_time_entries.services import time_entry as time_entry_svc
from app.schemas.tags import PortalTagUpdate
from app.services import portal_tags as tags_svc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.concurrency.conftest import profile_from_user
from tests.helpers.portal_test_users import user_portal_admin

type _TryUpdate = Callable[[AsyncSession], Awaitable[object]]


async def _parallel_cas(
    factory: async_sessionmaker[AsyncSession],
    try_a: _TryUpdate,
    try_b: _TryUpdate,
) -> list[str]:
    outcomes: list[str] = []

    async def run(fn: _TryUpdate) -> None:
        async with factory() as sess:
            try:
                await fn(sess)
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    await asyncio.gather(run(try_a), run(try_b))
    return outcomes


@pytest.mark.asyncio
async def test_parallel_update_specialist_profile_same_version_one_ok(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(specialist_svc, "publish_specialist_board_event", AsyncMock())
    user = user_portal_admin()
    async with sqlite_concurrency_factory() as s:
        s.add(profile_from_user(user))
        await s.flush()
        s.add(PortalSpecialistProfile(specialist_sub=user.sub, location="old", version=1))
        await s.commit()

    outcomes = await _parallel_cas(
        sqlite_concurrency_factory,
        lambda sess: specialist_svc.update_specialist_profile(
            sess, user, user.sub, SpecialistProfileUpdate(expected_version=1, location="from-a")
        ),
        lambda sess: specialist_svc.update_specialist_profile(
            sess, user, user.sub, SpecialistProfileUpdate(expected_version=1, location="from-b")
        ),
    )
    assert sorted(outcomes) == ["conflict", "ok"]
    async with sqlite_concurrency_factory() as s:
        row = await s.get(PortalSpecialistProfile, user.sub)
        assert row is not None
        assert row.version == 2
        assert row.location in ("from-a", "from-b")


@pytest.mark.asyncio
async def test_parallel_update_checklist_same_version_one_ok(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    admin = user_portal_admin()
    checklist_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(PortalChecklist(id=checklist_id, title="Онбординг", idp_group="", version=1))
        await s.commit()

    outcomes = await _parallel_cas(
        sqlite_concurrency_factory,
        lambda sess: checklist_svc.update_checklist(
            sess, admin, checklist_id, ChecklistUpdate(expected_version=1, title="from-a")
        ),
        lambda sess: checklist_svc.update_checklist(
            sess, admin, checklist_id, ChecklistUpdate(expected_version=1, title="from-b")
        ),
    )
    assert sorted(outcomes) == ["conflict", "ok"]
    async with sqlite_concurrency_factory() as s:
        row = (await s.execute(select(PortalChecklist).where(PortalChecklist.id == checklist_id))).scalar_one()
        assert row.version == 2
        assert row.title in ("from-a", "from-b")


@pytest.mark.asyncio
async def test_parallel_update_document_comment_same_version_one_ok(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doc_comment_svc.thread_svc, "publish_thread_updated", AsyncMock())
    user = user_portal_admin()
    doc_id, comment_id = uuid.uuid4(), uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(PortalDocument(id=doc_id, title="Doc", author_sub=user.sub, body="x", version=1))
        s.add(
            PortalDocumentComment(
                id=comment_id,
                document_id=doc_id,
                author_sub=user.sub,
                body="old",
                version=1,
            )
        )
        await s.commit()

    outcomes = await _parallel_cas(
        sqlite_concurrency_factory,
        lambda sess: doc_comment_svc.update_comment(
            sess, user, doc_id, comment_id, DocumentCommentUpdate(expected_version=1, body="from-a")
        ),
        lambda sess: doc_comment_svc.update_comment(
            sess, user, doc_id, comment_id, DocumentCommentUpdate(expected_version=1, body="from-b")
        ),
    )
    assert sorted(outcomes) == ["conflict", "ok"]
    async with sqlite_concurrency_factory() as s:
        row = (
            await s.execute(select(PortalDocumentComment).where(PortalDocumentComment.id == comment_id))
        ).scalar_one()
        assert row.version == 2
        assert row.body in ("from-a", "from-b")


@pytest.mark.asyncio
async def test_parallel_update_task_comment_same_version_one_ok(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(task_comment_svc.thread_svc, "publish_thread_updated", AsyncMock())
    user = user_portal_admin()
    task_id, comment_id = uuid.uuid4(), uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(
            PortalTask(
                id=task_id,
                title="Задача",
                creator_sub=user.sub,
                status=TaskStatus.TODO.value,
                priority=TaskPriority.MEDIUM.value,
                version=1,
            )
        )
        s.add(
            PortalTaskComment(
                id=comment_id,
                task_id=task_id,
                author_sub=user.sub,
                body="old",
                version=1,
            )
        )
        await s.commit()

    outcomes = await _parallel_cas(
        sqlite_concurrency_factory,
        lambda sess: task_comment_svc.update_comment(
            sess, user, task_id, comment_id, TaskCommentUpdate(expected_version=1, body="from-a")
        ),
        lambda sess: task_comment_svc.update_comment(
            sess, user, task_id, comment_id, TaskCommentUpdate(expected_version=1, body="from-b")
        ),
    )
    assert sorted(outcomes) == ["conflict", "ok"]
    async with sqlite_concurrency_factory() as s:
        row = (await s.execute(select(PortalTaskComment).where(PortalTaskComment.id == comment_id))).scalar_one()
        assert row.version == 2
        assert row.body in ("from-a", "from-b")


@pytest.mark.asyncio
async def test_parallel_update_tag_same_version_one_ok(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    tag_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(PortalTag(id=tag_id, name="Тег", slug="teg", color="#111111", version=1))
        await s.commit()

    outcomes = await _parallel_cas(
        sqlite_concurrency_factory,
        lambda sess: tags_svc.update_tag(sess, tag_id, PortalTagUpdate(expected_version=1, color="#AAAAAA")),
        lambda sess: tags_svc.update_tag(sess, tag_id, PortalTagUpdate(expected_version=1, color="#BBBBBB")),
    )
    assert sorted(outcomes) == ["conflict", "ok"]
    async with sqlite_concurrency_factory() as s:
        row = (await s.execute(select(PortalTag).where(PortalTag.id == tag_id))).scalar_one()
        assert row.version == 2
        assert row.color in ("#AAAAAA", "#BBBBBB")


@pytest.mark.asyncio
async def test_parallel_patch_group_chat_title_same_version_one_ok(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = MagicMock()
    manager.publish = AsyncMock()
    monkeypatch.setattr(group_chat_svc, "get_chat_manager", lambda: manager)
    user = user_portal_admin()
    chat_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(profile_from_user(user))
        s.add(PortalChat(id=chat_id, title="Группа", created_by_sub=user.sub, version=1))
        s.add(PortalChatMember(chat_id=chat_id, user_sub=user.sub))
        await s.commit()

    outcomes = await _parallel_cas(
        sqlite_concurrency_factory,
        lambda sess: group_chat_svc.patch_group_chat_title(sess, user, chat_id, title="from-a", expected_version=1),
        lambda sess: group_chat_svc.patch_group_chat_title(sess, user, chat_id, title="from-b", expected_version=1),
    )
    assert sorted(outcomes) == ["conflict", "ok"]
    async with sqlite_concurrency_factory() as s:
        row = (await s.execute(select(PortalChat).where(PortalChat.id == chat_id))).scalar_one()
        assert row.version == 2
        assert row.title in ("from-a", "from-b")


@pytest.mark.asyncio
async def test_parallel_update_time_entry_same_version_one_ok(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = user_portal_admin()
    entry_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(
            PortalTimeEntry(
                id=entry_id,
                user_sub=user.sub,
                worked_on=date(2026, 9, 1),
                minutes=60,
                note="old",
                version=1,
            )
        )
        await s.commit()

    outcomes = await _parallel_cas(
        sqlite_concurrency_factory,
        lambda sess: time_entry_svc.update_time_entry(
            sess, user, entry_id, PortalTimeEntryUpdate(expected_version=1, note="from-a")
        ),
        lambda sess: time_entry_svc.update_time_entry(
            sess, user, entry_id, PortalTimeEntryUpdate(expected_version=1, note="from-b")
        ),
    )
    assert sorted(outcomes) == ["conflict", "ok"]
    async with sqlite_concurrency_factory() as s:
        row = (await s.execute(select(PortalTimeEntry).where(PortalTimeEntry.id == entry_id))).scalar_one()
        assert row.version == 2
        assert row.note in ("from-a", "from-b")
