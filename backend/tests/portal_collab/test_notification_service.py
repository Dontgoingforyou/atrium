"""Сервисные тесты: ветки notification.py, слабо покрытые только HTTP."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMember
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_document_comment import PortalDocumentComment
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskComment
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.services import notification as notification_svc
from app.portal_collab.services._notification_access import (
    NOTIFICATION_TYPE_COMMENT,
    NOTIFICATION_TYPE_MENTION,
    batch_task_access_check,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_manager, user_portal_regular, user_portal_user_b


def _now() -> datetime:
    return datetime.now(UTC)


@pytest.mark.asyncio
async def test_create_mention_skips_recipient_without_task_access(sqlite_session: AsyncSession) -> None:
    """Упоминание пользователя без связи с задачей не создаёт запись."""
    now = _now()
    task = PortalTask(
        title="Чужая",
        creator_sub="alice",
        assignee_sub="bob",
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    comment = PortalTaskComment(
        task_id=task.id,
        parent_id=None,
        author_sub="alice",
        body="@carol",
        mentions=["user-b"],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(comment)
    await sqlite_session.flush()

    notified = await notification_svc.create_mention_notifications(sqlite_session, task, comment, "alice")
    assert notified == {}
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_create_comment_notifications_notifies_participants_not_author(
    sqlite_session: AsyncSession,
) -> None:
    """Комментарий без @ — creator и assignee, автор исключён."""
    now = _now()
    task = PortalTask(
        title="Участники",
        creator_sub="user-sub",
        assignee_sub="user-b",
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    comment = PortalTaskComment(
        task_id=task.id,
        parent_id=None,
        author_sub=user_portal_manager().sub,
        body="без упоминания",
        mentions=[],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(comment)
    await sqlite_session.flush()

    notified = await notification_svc.create_comment_notifications(
        sqlite_session,
        task,
        comment,
        user_portal_manager().sub,
    )
    assert set(notified) == {"user-sub", "user-b"}
    rows = (
        (await sqlite_session.execute(select(PortalNotification).where(PortalNotification.comment_id == comment.id)))
        .scalars()
        .all()
    )
    assert {row.recipient_sub: row.type for row in rows} == {
        "user-sub": NOTIFICATION_TYPE_COMMENT,
        "user-b": NOTIFICATION_TYPE_COMMENT,
    }
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_create_comment_notifications_skips_already_mentioned(
    sqlite_session: AsyncSession,
) -> None:
    """Уже получивший task_mention не получает второй тип на тот же комментарий."""
    now = _now()
    task = PortalTask(
        title="Mention first",
        creator_sub="user-sub",
        assignee_sub="user-b",
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    comment = PortalTaskComment(
        task_id=task.id,
        parent_id=None,
        author_sub="user-sub",
        body="@user-b",
        mentions=["user-b"],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(comment)
    await sqlite_session.flush()

    mentioned = await notification_svc.create_mention_notifications(sqlite_session, task, comment, "user-sub")
    assert list(mentioned) == ["user-b"]
    extra = await notification_svc.create_comment_notifications(
        sqlite_session,
        task,
        comment,
        "user-sub",
        already_notified=set(mentioned),
    )
    assert extra == {}
    rows = (
        (await sqlite_session.execute(select(PortalNotification).where(PortalNotification.comment_id == comment.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].type == NOTIFICATION_TYPE_MENTION
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_create_comment_notifications_skips_without_task_access(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _no_access(
        _session: AsyncSession,
        _candidate_subs: set[str],
        _task: PortalTask,
        _profiles_by_sub: dict[str, object],
    ) -> set[str]:
        return set()

    monkeypatch.setattr(
        "app.portal_collab.services._notification_task.batch_task_access_check",
        _no_access,
    )
    now = _now()
    task = PortalTask(
        title="Нет доступа",
        creator_sub="user-sub",
        assignee_sub="user-b",
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    comment = PortalTaskComment(
        task_id=task.id,
        parent_id=None,
        author_sub="user-sub",
        body="текст",
        mentions=[],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(comment)
    await sqlite_session.flush()

    notified = await notification_svc.create_comment_notifications(sqlite_session, task, comment, "user-sub")
    assert notified == {}
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_create_mention_notifies_portal_admin_recipient(sqlite_session: AsyncSession) -> None:
    """Получатель с is_portal_admin в профиле видит задачу через кэш профиля."""
    prof = (
        await sqlite_session.execute(select(PortalUserProfile).where(PortalUserProfile.sub == "user-b"))
    ).scalar_one()
    prof.is_portal_admin = True
    await sqlite_session.flush()

    now = _now()
    task = PortalTask(
        title="Секрет",
        creator_sub="alice",
        assignee_sub="bob",
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    comment = PortalTaskComment(
        task_id=task.id,
        parent_id=None,
        author_sub="alice",
        body="@admin",
        mentions=["user-b"],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(comment)
    await sqlite_session.flush()

    notified = await notification_svc.create_mention_notifications(sqlite_session, task, comment, "alice")
    assert list(notified) == ["user-b"]
    assert isinstance(notified["user-b"], uuid.UUID)

    prof.is_portal_admin = False
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_create_mention_notifies_chat_member(sqlite_session: AsyncSession) -> None:
    """Участник чата задачи получает уведомление об @."""
    now = _now()
    chat = PortalChat(title="c", created_by_sub="user-sub", created_at=now, updated_at=now)
    sqlite_session.add(chat)
    await sqlite_session.flush()
    sqlite_session.add_all(
        [
            PortalChatMember(chat_id=chat.id, user_sub="user-sub"),
            PortalChatMember(chat_id=chat.id, user_sub="user-b"),
        ]
    )
    task = PortalTask(
        title="В чате",
        creator_sub="user-sub",
        assignee_sub=None,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        chat_id=chat.id,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    comment = PortalTaskComment(
        task_id=task.id,
        parent_id=None,
        author_sub="user-sub",
        body="@b",
        mentions=["user-b"],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(comment)
    await sqlite_session.flush()

    notified = await notification_svc.create_mention_notifications(sqlite_session, task, comment, "user-sub")
    assert list(notified) == ["user-b"]
    assert isinstance(notified["user-b"], uuid.UUID)
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_batch_task_access_check_includes_junction_co_assignee(
    sqlite_session: AsyncSession,
) -> None:
    """Co-assignee из portal_task_assignee проходит проверку, даже если не task.assignee_sub."""
    now = _now()
    task = PortalTask(
        title="Multi",
        creator_sub="user-sub",
        assignee_sub="user-b",
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    sqlite_session.add(PortalTaskAssignee(task_id=task.id, assignee_sub="user-b"))
    sqlite_session.add(PortalTaskAssignee(task_id=task.id, assignee_sub=user_portal_manager().sub))
    await sqlite_session.flush()

    profiles = {
        "user-b": PortalUserProfile(
            sub="user-b",
            email="b@example.com",
            full_name="B",
            username="b",
            is_portal_admin=False,
        ),
        user_portal_manager().sub: PortalUserProfile(
            sub=user_portal_manager().sub,
            email=user_portal_manager().email,
            full_name=user_portal_manager().full_name,
            username=user_portal_manager().username,
            is_portal_admin=False,
        ),
    }

    can_access = await batch_task_access_check(
        sqlite_session,
        {user_portal_manager().sub},
        task,
        profiles,
    )
    assert user_portal_manager().sub in can_access
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_create_assignment_notifications_for_co_assignee(
    sqlite_session: AsyncSession,
) -> None:
    """create_assignment_notifications уведомляет второго исполнителя после sync_task_assignees."""
    from app.portal_collab.services._task_assignees import sync_task_assignees

    now = _now()
    task = PortalTask(
        title="Notify both",
        creator_sub="user-sub",
        assignee_sub="user-b",
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    await sync_task_assignees(sqlite_session, task, ["user-b", user_portal_manager().sub])

    notified = await notification_svc.create_assignment_notifications(
        sqlite_session,
        task,
        "user-sub",
        ["user-b", user_portal_manager().sub],
    )
    assert set(notified) == {"user-b", user_portal_manager().sub}
    assert all(isinstance(nid, uuid.UUID) for nid in notified.values())
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_create_assignment_returns_none_when_recipient_cannot_view(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _no_access(
        _session: AsyncSession,
        _candidate_subs: set[str],
        _task: PortalTask,
        _profiles_by_sub: dict[str, object],
    ) -> set[str]:
        return set()

    monkeypatch.setattr(
        "app.portal_collab.services._notification_create.batch_task_access_check",
        _no_access,
    )

    now = _now()
    task = PortalTask(
        title="X",
        creator_sub="user-sub",
        assignee_sub="user-b",
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()

    assert await notification_svc.create_assignment_notification(sqlite_session, task, "user-sub") is None
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_create_document_mention_skips_without_recipient_profile(sqlite_session: AsyncSession) -> None:
    now = _now()
    doc = PortalDocument(
        title="Д",
        author_sub="user-sub",
        author_display_name="U",
        author_email="u@e.com",
        owner_sub="user-sub",
        body="b",
        parent_document_id=None,
    )
    sqlite_session.add(doc)
    await sqlite_session.flush()
    dcom = PortalDocumentComment(
        document_id=doc.id,
        parent_id=None,
        author_sub="user-sub",
        body="x",
        mentions=["ghost-sub-no-profile"],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(dcom)
    await sqlite_session.flush()

    notified = await notification_svc.create_document_mention_notifications(
        sqlite_session,
        doc,
        dcom,
        "user-sub",
    )
    assert notified == {}
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_create_document_mention_skips_without_document_access(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _no_access(_mentioned: set[str], _profiles: dict) -> set[str]:
        return set()

    monkeypatch.setattr(
        "app.portal_collab.services._notification_create.batch_document_access_check",
        _no_access,
    )

    now = _now()
    doc = PortalDocument(
        title="Д2",
        author_sub="user-sub",
        author_display_name="U",
        author_email="u@e.com",
        owner_sub="user-sub",
        body="b",
        parent_document_id=None,
    )
    sqlite_session.add(doc)
    await sqlite_session.flush()
    dcom = PortalDocumentComment(
        document_id=doc.id,
        parent_id=None,
        author_sub="user-sub",
        body="x",
        mentions=["user-b"],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(dcom)
    await sqlite_session.flush()

    notified = await notification_svc.create_document_mention_notifications(
        sqlite_session,
        doc,
        dcom,
        "user-sub",
    )
    assert notified == {}
    await sqlite_session.rollback()


@pytest.mark.asyncio
async def test_mark_all_and_delete_all_return_counts(sqlite_session: AsyncSession) -> None:
    user = user_portal_user_b()
    now = _now()
    t1 = PortalTask(
        title="T1",
        creator_sub="user-sub",
        assignee_sub=user.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    t2 = PortalTask(
        title="T2",
        creator_sub="user-sub",
        assignee_sub=user.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add_all([t1, t2])
    await sqlite_session.flush()
    c2 = PortalTaskComment(
        task_id=t2.id,
        parent_id=None,
        author_sub="user-sub",
        body="m",
        mentions=[user.sub],
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(c2)
    await sqlite_session.flush()
    sqlite_session.add_all(
        [
            PortalNotification(
                recipient_sub=user.sub,
                type="task_assigned",
                task_id=t1.id,
                comment_id=None,
                author_sub="user-sub",
                created_at=now,
            ),
            PortalNotification(
                recipient_sub=user.sub,
                type="task_mention",
                task_id=t2.id,
                comment_id=c2.id,
                author_sub="user-sub",
                created_at=now,
            ),
        ]
    )
    await sqlite_session.commit()

    n_marked = await notification_svc.mark_all_notifications_read(sqlite_session, user)
    assert n_marked >= 1

    n_deleted = await notification_svc.delete_all_notifications(sqlite_session, user)
    assert n_deleted >= 1

    rest = (
        (await sqlite_session.execute(select(PortalNotification).where(PortalNotification.recipient_sub == user.sub)))
        .scalars()
        .all()
    )
    assert rest == []


@pytest.mark.asyncio
async def test_get_notification_for_user_ok_and_forbidden(sqlite_session: AsyncSession) -> None:
    from app.core.exceptions import ForbiddenError, NotFoundError

    user = user_portal_regular()
    other = user_portal_user_b()
    now = _now()
    task = PortalTask(
        title="GT",
        creator_sub=user.sub,
        assignee_sub=None,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    n = PortalNotification(
        recipient_sub=user.sub,
        type="task_assigned",
        task_id=task.id,
        comment_id=None,
        author_sub=other.sub,
        created_at=now,
    )
    sqlite_session.add(n)
    await sqlite_session.commit()
    await sqlite_session.refresh(n)

    got = await notification_svc.get_notification_for_user(sqlite_session, user, n.id)
    assert got.id == n.id

    with pytest.raises(ForbiddenError, match="доступа"):
        await notification_svc.get_notification_for_user(sqlite_session, other, n.id)

    with pytest.raises(NotFoundError, match="не найдено"):
        await notification_svc.get_notification_for_user(sqlite_session, user, uuid.uuid4())


@pytest.mark.asyncio
async def test_create_document_trashed_notifications_for_admins(sqlite_session: AsyncSession) -> None:
    """При удалении документа уведомляются админы с notify_document_trash, кроме удалившего."""
    admin_on = PortalUserProfile(
        sub="admin-on",
        email="a1@e.com",
        is_portal_admin=True,
        notify_document_trash=True,
    )
    admin_off = PortalUserProfile(
        sub="admin-off",
        email="a2@e.com",
        is_portal_admin=True,
        notify_document_trash=False,
    )
    deleter = PortalUserProfile(
        sub="deleter",
        email="d@e.com",
        is_portal_admin=True,
        notify_document_trash=True,
    )
    sqlite_session.add_all([admin_on, admin_off, deleter])
    seed_admin = await sqlite_session.get(PortalUserProfile, "admin-sub")
    if seed_admin is not None:
        seed_admin.notify_document_trash = False
    doc = PortalDocument(
        title="Удаляемый",
        author_sub="deleter",
        author_display_name="D",
        author_email="d@e.com",
        owner_sub="deleter",
        body="b",
        parent_document_id=None,
    )
    sqlite_session.add(doc)
    await sqlite_session.flush()

    notified = await notification_svc.create_document_trashed_notifications(
        sqlite_session,
        doc.id,
        "deleter",
    )
    assert list(notified) == ["admin-on"]
    assert isinstance(notified["admin-on"], uuid.UUID)

    rows = (
        (
            await sqlite_session.execute(
                select(PortalNotification).where(
                    PortalNotification.document_id == doc.id,
                    PortalNotification.type == "document_trashed",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].type == "document_trashed"
    assert rows[0].document_id == doc.id
    assert rows[0].author_sub == "deleter"
    await sqlite_session.rollback()
