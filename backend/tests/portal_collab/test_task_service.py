"""Публичный сервис задач: RBAC, теги, due_at, видимость."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.enums import TaskPriority, TaskStatus
from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMember
from app.infrastructure.db.models.portal_document import PortalDocument, PortalTag
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskColumn
from app.portal_collab.schemas.task import PortalTaskCreate, PortalTaskUpdate
from app.portal_collab.services import task as task_svc
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_portal_admin,
    user_portal_no_idp_groups,
    user_portal_regular,
    user_portal_user_b,
)


def _now() -> datetime:
    return datetime.now(UTC)


@pytest.mark.asyncio
async def test_create_task_with_tag_ids_roundtrip(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    tag = PortalTag(name="SvcTag", slug=f"svc-tag-{uuid.uuid4().hex[:8]}", color="#112233")
    sqlite_session.add(tag)
    await sqlite_session.commit()
    await sqlite_session.refresh(tag)

    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="С тегом", tag_ids=[tag.id], assignee_sub="admin-sub"),
    )
    assert len(task.tags) == 1
    assert task.tags[0].id == tag.id

    updated = await task_svc.update_task(
        sqlite_session,
        admin,
        task.id,
        PortalTaskUpdate(expected_version=1, tag_ids=[]),
    )
    assert updated.tags == []


@pytest.mark.asyncio
async def test_update_task_clears_description_with_null(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="С описанием", description="<p>Текст</p>", assignee_sub="admin-sub"),
    )
    assert task.description == "<p>Текст</p>"

    updated = await task_svc.update_task(
        sqlite_session,
        admin,
        task.id,
        PortalTaskUpdate(expected_version=1, description=None),
    )
    assert updated.description is None


@pytest.mark.asyncio
async def test_update_task_clears_due_at_with_null(sqlite_session: AsyncSession) -> None:
    from datetime import UTC, datetime

    admin = user_portal_admin()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(
            title="Со сроком",
            assignee_sub="admin-sub",
            due_at=datetime(2030, 1, 15, 12, 0, tzinfo=UTC),
        ),
    )
    assert task.due_at is not None

    updated = await task_svc.update_task(
        sqlite_session,
        admin,
        task.id,
        PortalTaskUpdate(expected_version=1, due_at=None),
    )
    assert updated.due_at is None


@pytest.mark.asyncio
async def test_list_tasks_forbidden_assignee_filter_for_regular_user(sqlite_session: AsyncSession) -> None:
    user = user_portal_no_idp_groups()
    with pytest.raises(ForbiddenError, match="исполнител"):
        await task_svc.list_tasks(sqlite_session, user, assignee_sub=["user-b"])


@pytest.mark.asyncio
async def test_create_task_document_not_found(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    with pytest.raises(NotFoundError, match="Документ не найден"):
        await task_svc.create_task(
            sqlite_session,
            admin,
            PortalTaskCreate(title="Без документа", document_id=uuid.uuid4(), assignee_sub="admin-sub"),
        )


@pytest.mark.asyncio
async def test_create_task_forbidden_chat_not_member(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    user = user_portal_regular()
    now = _now()
    chat = PortalChat(title="Закрытый", created_by_sub=admin.sub, created_at=now, updated_at=now)
    sqlite_session.add(chat)
    await sqlite_session.flush()
    sqlite_session.add(PortalChatMember(chat_id=chat.id, user_sub=admin.sub))
    await sqlite_session.commit()

    with pytest.raises(ForbiddenError, match="чат"):
        await task_svc.create_task(
            sqlite_session,
            user,
            PortalTaskCreate(title="Чужой чат", chat_id=chat.id, assignee_sub="admin-sub"),
        )


@pytest.mark.asyncio
async def test_create_task_forbidden_source_message(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _no_msg(_session, _user, _mid: uuid.UUID) -> bool:
        return False

    monkeypatch.setattr("app.portal_collab.services._task_mutations.chat_svc.user_can_access_message", _no_msg)

    admin = user_portal_admin()
    with pytest.raises(ForbiddenError, match="сообщен"):
        await task_svc.create_task(
            sqlite_session,
            admin,
            PortalTaskCreate(title="Нет сообщения", source_message_id=uuid.uuid4(), assignee_sub="admin-sub"),
        )


@pytest.mark.asyncio
async def test_create_task_publishes_assignment_notification_ids(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()
    assignee = user_portal_user_b()
    captured: list[tuple[list[str], dict[str, uuid.UUID] | None]] = []

    async def _record(
        subs: list[str],
        *,
        notification_ids_by_sub: dict[str, uuid.UUID] | None = None,
    ) -> None:
        captured.append((list(subs), notification_ids_by_sub))

    monkeypatch.setattr(
        "app.portal_chat.services.inbox_publish.publish_portal_notification_updates",
        _record,
    )

    await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Назначение с id", assignee_sub=assignee.sub),
    )
    assert len(captured) == 1
    subs, ids_by_sub = captured[0]
    assert subs == [assignee.sub]
    assert ids_by_sub is not None
    assert assignee.sub in ids_by_sub
    assert isinstance(ids_by_sub[assignee.sub], uuid.UUID)


@pytest.mark.asyncio
async def test_delete_task_withdraws_assignment_notifications(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Удаление задачи и подзадачи снимает уведомления у тех, кому их уже отправили."""
    admin = user_portal_admin()
    assignee = user_portal_user_b()
    child_assignee = user_portal_regular()
    captured: list[list[str]] = []

    async def _record(subs: list[str]) -> None:
        captured.append(list(subs))

    monkeypatch.setattr(
        "app.portal_chat.services.inbox_publish.publish_portal_notification_withdrawals",
        _record,
    )

    parent = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Родитель", assignee_sub=assignee.sub),
    )
    await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Подзадача", assignee_sub=child_assignee.sub, parent_task_id=parent.id),
    )
    await task_svc.delete_task(sqlite_session, admin, parent.id)

    assert len(captured) == 1
    assert set(captured[0]) == {assignee.sub, child_assignee.sub}
    assert admin.sub not in captured[0]


@pytest.mark.asyncio
async def test_delete_task_without_recipients_skips_withdraw(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()
    captured: list[list[str]] = []

    async def _record(subs: list[str]) -> None:
        captured.append(list(subs))

    monkeypatch.setattr(
        "app.portal_chat.services.inbox_publish.publish_portal_notification_withdrawals",
        _record,
    )

    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Только себе", assignee_sub=admin.sub),
    )
    await task_svc.delete_task(sqlite_session, admin, task.id)
    assert captured == []


@pytest.mark.asyncio
async def test_list_task_history_after_update(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="История", assignee_sub="admin-sub"),
    )
    await task_svc.update_task(
        sqlite_session,
        admin,
        task.id,
        PortalTaskUpdate(expected_version=1, title="Новый заголовок"),
    )
    hist = await task_svc.list_task_history(sqlite_session, admin, task.id)
    assert len(hist) >= 2
    actions = {h.diff.get("action", {}).get("new") for h in hist if "action" in h.diff}
    assert "created" in actions
    assert any("title" in h.diff for h in hist)


@pytest.mark.asyncio
async def test_reorder_task_within_status(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    t1 = await task_svc.create_task(sqlite_session, admin, PortalTaskCreate(title="Первая", assignee_sub="admin-sub"))
    t2 = await task_svc.create_task(sqlite_session, admin, PortalTaskCreate(title="Вторая", assignee_sub="admin-sub"))
    status = TaskStatus.TODO.value
    moved = await task_svc.reorder_task(sqlite_session, admin, t2.id, status=status, before_task_id=t1.id)
    assert moved.id == t2.id
    rows = await task_svc.list_tasks(sqlite_session, admin, status=[status], limit=10)
    titles = [r.title for r in rows if r.id in (t1.id, t2.id)]
    assert "Вторая" in titles


@pytest.mark.asyncio
async def test_search_tasks_for_user_by_title(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    marker = f"UNIQSRCH{uuid.uuid4().hex[:8]}"
    await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title=f"Задача {marker}", assignee_sub="admin-sub"),
    )
    found = await task_svc.search_tasks_for_user(sqlite_session, admin, marker.lower())
    assert any(marker in t.title for t in found)


@pytest.mark.asyncio
async def test_list_tasks_filter_document_id(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    doc = PortalDocument(
        title="Док задачи",
        author_sub=admin.sub,
        author_display_name="A",
        author_email="a@e.com",
        owner_sub=admin.sub,
        body="x",
        parent_document_id=None,
    )
    sqlite_session.add(doc)
    await sqlite_session.flush()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Привязка к документу", document_id=doc.id, assignee_sub="admin-sub"),
    )
    rows = await task_svc.list_tasks(sqlite_session, admin, document_id=doc.id)
    assert any(r.id == task.id for r in rows)


@pytest.mark.asyncio
async def test_update_task_document_id_patch(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    doc = PortalDocument(
        title="Д2",
        author_sub=admin.sub,
        author_display_name="A",
        author_email="a@e.com",
        owner_sub=admin.sub,
        body="b",
        parent_document_id=None,
    )
    sqlite_session.add(doc)
    await sqlite_session.flush()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Без док", assignee_sub="admin-sub"),
    )
    updated = await task_svc.update_task(
        sqlite_session,
        admin,
        task.id,
        PortalTaskUpdate(expected_version=1, document_id=doc.id),
    )
    assert updated.document_id == doc.id


@pytest.mark.asyncio
async def test_user_can_view_task_via_source_message(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.infrastructure.db.models.portal_chat import PortalChatMessage

    async def _yes(_session, _user, _mid: uuid.UUID) -> bool:
        return True

    monkeypatch.setattr("app.portal_collab.services._task_queries.chat_svc.user_can_access_message", _yes)

    admin = user_portal_admin()
    user = user_portal_regular()
    now = _now()
    chat = PortalChat(title="c", created_by_sub=admin.sub, created_at=now, updated_at=now)
    sqlite_session.add(chat)
    await sqlite_session.flush()
    msg = PortalChatMessage(chat_id=chat.id, author_sub=admin.sub, body="m", created_at=now, updated_at=now)
    sqlite_session.add(msg)
    await sqlite_session.flush()
    task = PortalTask(
        title="Из сообщения",
        creator_sub=admin.sub,
        assignee_sub=None,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        source_message_id=msg.id,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.commit()
    await sqlite_session.refresh(task)

    assert await task_svc.user_can_view_task(sqlite_session, user, task) is True


@pytest.mark.asyncio
async def test_update_task_assignee_subs_forbidden_for_non_creator_assignee(
    sqlite_session: AsyncSession,
) -> None:
    """Исполнитель не может назначать других пользователей на задачу (IDOR / эскалация прав)."""
    admin = user_portal_admin()
    assignee = user_portal_regular()
    now = _now()
    task = PortalTask(
        title="Чужие исполнители",
        creator_sub=admin.sub,
        assignee_sub=assignee.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee

    sqlite_session.add(PortalTaskAssignee(task_id=task.id, assignee_sub=assignee.sub))
    await sqlite_session.commit()

    with pytest.raises(ForbiddenError, match="исполнител"):
        await task_svc.update_task(
            sqlite_session,
            assignee,
            task.id,
            PortalTaskUpdate(expected_version=1, assignee_subs=["user-b", "user-c"]),
        )


@pytest.mark.asyncio
async def test_update_task_allowed_for_portal_admin_assignee_not_creator(
    sqlite_session: AsyncSession,
) -> None:
    """Администратор-исполнитель может редактировать задачу (соавторство)."""
    admin = user_portal_admin()
    other_creator = user_portal_regular()
    now = _now()
    task = PortalTask(
        title="Назначена админу",
        creator_sub=other_creator.sub,
        assignee_sub=admin.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee

    sqlite_session.add(PortalTaskAssignee(task_id=task.id, assignee_sub=admin.sub))
    await sqlite_session.commit()

    updated = await task_svc.update_task(
        sqlite_session,
        admin,
        task.id,
        PortalTaskUpdate(expected_version=1, title="Правка исполнителем-админом"),
    )
    assert updated.title == "Правка исполнителем-админом"


@pytest.mark.asyncio
async def test_update_task_allowed_for_portal_admin_not_assignee(
    sqlite_session: AsyncSession,
) -> None:
    """Администратор без авторства и без назначения может редактировать чужую задачу."""
    admin = user_portal_admin()
    assignee = user_portal_regular()
    now = _now()
    task = PortalTask(
        title="Чужая задача",
        creator_sub=assignee.sub,
        assignee_sub=assignee.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee

    sqlite_session.add(PortalTaskAssignee(task_id=task.id, assignee_sub=assignee.sub))
    await sqlite_session.commit()

    updated = await task_svc.update_task(
        sqlite_session,
        admin,
        task.id,
        PortalTaskUpdate(expected_version=1, title="Правка админом"),
    )
    assert updated.title == "Правка админом"


@pytest.mark.asyncio
async def test_update_task_allowed_for_assignee_not_creator(
    sqlite_session: AsyncSession,
) -> None:
    """Исполнитель без авторства может редактировать задачу (соавторство)."""
    creator = user_portal_admin()
    assignee = user_portal_regular()
    now = _now()
    task = PortalTask(
        title="Назначена исполнителю",
        creator_sub=creator.sub,
        assignee_sub=assignee.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add(task)
    await sqlite_session.flush()
    from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee

    sqlite_session.add(PortalTaskAssignee(task_id=task.id, assignee_sub=assignee.sub))
    await sqlite_session.commit()

    updated = await task_svc.update_task(
        sqlite_session,
        assignee,
        task.id,
        PortalTaskUpdate(expected_version=1, title="Правка исполнителем"),
    )
    assert updated.title == "Правка исполнителем"


@pytest.mark.asyncio
async def test_reorder_task_allowed_for_assignee_not_creator(
    sqlite_session: AsyncSession,
) -> None:
    """Исполнитель может перемещать задачу на доске."""
    creator = user_portal_admin()
    assignee = user_portal_regular()
    now = _now()
    t1 = PortalTask(
        title="Первая",
        creator_sub=creator.sub,
        assignee_sub=assignee.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        position=0,
        created_at=now,
        updated_at=now,
    )
    t2 = PortalTask(
        title="Вторая",
        creator_sub=creator.sub,
        assignee_sub=assignee.sub,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        position=1,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add_all([t1, t2])
    await sqlite_session.flush()
    from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee

    sqlite_session.add(PortalTaskAssignee(task_id=t1.id, assignee_sub=assignee.sub))
    sqlite_session.add(PortalTaskAssignee(task_id=t2.id, assignee_sub=assignee.sub))
    await sqlite_session.commit()

    moved = await task_svc.reorder_task(
        sqlite_session,
        assignee,
        t2.id,
        status=TaskStatus.TODO.value,
        before_task_id=t1.id,
    )
    assert moved.id == t2.id
    assert moved.position == 0


@pytest.mark.asyncio
async def test_list_tasks_done_this_month_excludes_previous_month(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    now = _now()
    prev_month = datetime(now.year, now.month, 1, tzinfo=UTC) - timedelta(days=1)
    this_month = datetime(now.year, now.month, 2, tzinfo=UTC)
    old = PortalTask(
        title="Закрыта в прошлом месяце",
        creator_sub=admin.sub,
        assignee_sub=admin.sub,
        status=TaskStatus.DONE.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=prev_month,
        updated_at=prev_month,
    )
    fresh = PortalTask(
        title="Закрыта в этом месяце",
        creator_sub=admin.sub,
        assignee_sub=admin.sub,
        status=TaskStatus.DONE.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=this_month,
        updated_at=this_month,
    )
    sqlite_session.add_all([old, fresh])
    await sqlite_session.commit()

    rows = await task_svc.list_tasks(sqlite_session, admin, done_this_month=True, limit=200)
    titles = {t.title for t in rows}
    assert "Закрыта в этом месяце" in titles
    assert "Закрыта в прошлом месяце" not in titles


@pytest.mark.asyncio
async def test_list_tasks_no_assignee_ignores_junction_only(sqlite_session: AsyncSession) -> None:
    from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
    from app.portal_collab.services import task_home as task_home_svc
    from app.portal_collab.services.task_column import kpi_excluded_status_keys

    admin = user_portal_admin()
    now = _now()
    bare = PortalTask(
        title="По-настоящему без исполнителя",
        creator_sub=admin.sub,
        assignee_sub=None,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    junction = PortalTask(
        title="Только junction",
        creator_sub=admin.sub,
        assignee_sub=None,
        status=TaskStatus.TODO.value,
        priority=TaskPriority.MEDIUM.value,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add_all([bare, junction])
    await sqlite_session.flush()
    sqlite_session.add(PortalTaskAssignee(task_id=junction.id, assignee_sub="junction-only-sub"))
    await sqlite_session.commit()

    rows = await task_svc.list_tasks(sqlite_session, admin, no_assignee=True, limit=200)
    titles = {t.title for t in rows}
    assert "По-настоящему без исполнителя" in titles
    assert "Только junction" not in titles

    kpi_excluded = await kpi_excluded_status_keys(sqlite_session)
    home_count = await task_home_svc.count_admin_team_no_assignee(sqlite_session, admin, kpi_excluded=kpi_excluded)
    assert len(rows) == home_count


@pytest.mark.asyncio
async def test_list_tasks_kpi_open_only_matches_home_open_count(sqlite_session: AsyncSession) -> None:
    from app.infrastructure.db.models.portal_task import PortalTaskColumn
    from app.portal_collab.services import task_home as task_home_svc
    from app.portal_collab.services.task_column import kpi_excluded_status_keys

    admin = user_portal_admin()
    now = _now()
    sqlite_session.add(
        PortalTaskColumn(
            title="Закрыто",
            status_key="col_closed_kpi",
            color="#333333",
            position=9,
            exclude_from_kpi=True,
        )
    )
    sqlite_session.add_all(
        [
            PortalTask(
                title="KPI открытая",
                creator_sub=admin.sub,
                assignee_sub=admin.sub,
                status=TaskStatus.TODO.value,
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
            PortalTask(
                title="Вне KPI",
                creator_sub=admin.sub,
                assignee_sub=admin.sub,
                status="col_closed_kpi",
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await sqlite_session.commit()

    rows = await task_svc.list_tasks(sqlite_session, admin, kpi_open_only=True, limit=200)
    titles = {t.title for t in rows}
    assert "KPI открытая" in titles
    assert "Вне KPI" not in titles

    kpi_excluded = await kpi_excluded_status_keys(sqlite_session)
    home_open, _ = await task_home_svc.count_admin_team_tasks_home_summary(
        sqlite_session, admin, kpi_excluded=kpi_excluded
    )
    assert len(rows) == home_open


def _prod_like_closed_columns() -> list[PortalTaskColumn]:
    """Как на проде: «На согласовании» с ключом done, «Готово» без флага KPI."""
    return [
        PortalTaskColumn(
            title="На согласовании",
            status_key="done",
            color="#3b82f6",
            position=8,
            exclude_from_kpi=True,
        ),
        PortalTaskColumn(
            title="Готово",
            status_key="col_o4kqsv03",
            color="#1a9000",
            position=9,
            exclude_from_kpi=False,
        ),
    ]


@pytest.mark.asyncio
async def test_list_tasks_ready_without_kpi_flag_is_closed_not_open(sqlite_session: AsyncSession) -> None:
    """«Готово» без exclude_from_kpi — закрытая: в месяце, не open, не overdue."""
    from datetime import time

    from app.portal_collab.services import task_home as task_home_svc
    from app.portal_collab.services._task_due_calendar import today_portal
    from app.portal_collab.services.task_column import kpi_excluded_status_keys

    admin = user_portal_admin()
    now = _now()
    overdue = datetime.combine(today_portal(now) - timedelta(days=2), time.min, tzinfo=UTC)
    sqlite_session.add_all(_prod_like_closed_columns())
    sqlite_session.add_all(
        [
            PortalTask(
                title="Готово без флага",
                creator_sub=admin.sub,
                assignee_sub=admin.sub,
                status="col_o4kqsv03",
                priority=TaskPriority.MEDIUM.value,
                due_at=overdue,
                created_at=now,
                updated_at=now,
            ),
            PortalTask(
                title="Открытая",
                creator_sub=admin.sub,
                assignee_sub=admin.sub,
                status=TaskStatus.TODO.value,
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await sqlite_session.commit()

    month_rows = await task_svc.list_tasks(sqlite_session, admin, done_this_month=True, limit=200)
    assert {t.title for t in month_rows} == {"Готово без флага"}

    open_rows = await task_svc.list_tasks(sqlite_session, admin, kpi_open_only=True, limit=200)
    assert {t.title for t in open_rows} == {"Открытая"}

    overdue_rows = await task_svc.list_tasks(sqlite_session, admin, overdue_only=True, limit=200)
    assert all(t.title != "Готово без флага" for t in overdue_rows)

    kpi_excluded = await kpi_excluded_status_keys(sqlite_session)
    home_open, home_overdue = await task_home_svc.count_admin_team_tasks_home_summary(
        sqlite_session, admin, kpi_excluded=kpi_excluded
    )
    assert len(open_rows) == home_open
    assert len(overdue_rows) == home_overdue


@pytest.mark.asyncio
async def test_list_tasks_approval_key_done_in_month_not_in_status_done(sqlite_session: AsyncSession) -> None:
    """Title «На согласовании» при status_key=done: в месячном фильтре, не в чипе «Завершена»."""
    admin = user_portal_admin()
    now = _now()
    sqlite_session.add_all(_prod_like_closed_columns())
    sqlite_session.add_all(
        [
            PortalTask(
                title="На согласовании за месяц",
                creator_sub=admin.sub,
                assignee_sub=admin.sub,
                status=TaskStatus.DONE.value,
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
            PortalTask(
                title="Готово за месяц",
                creator_sub=admin.sub,
                assignee_sub=admin.sub,
                status="col_o4kqsv03",
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await sqlite_session.commit()

    month_rows = await task_svc.list_tasks(sqlite_session, admin, done_this_month=True, limit=200)
    assert {t.title for t in month_rows} == {"На согласовании за месяц", "Готово за месяц"}

    done_chip = await task_svc.list_tasks(sqlite_session, admin, status=["done"], limit=200)
    assert {t.title for t in done_chip} == {"Готово за месяц"}
    assert all(t.status == "col_o4kqsv03" for t in done_chip)


@pytest.mark.asyncio
async def test_export_column_uses_exact_status_key_not_done_chip(
    sqlite_session: AsyncSession,
) -> None:
    """Выгрузка колонки «На согласовании» (ключ done) — её задачи, не «Готово»."""
    admin = user_portal_admin()
    now = _now()
    approval_col, done_col = _prod_like_closed_columns()
    sqlite_session.add_all([approval_col, done_col])
    sqlite_session.add_all(
        [
            PortalTask(
                title="Задача на согласовании",
                creator_sub=admin.sub,
                assignee_sub=admin.sub,
                status=TaskStatus.DONE.value,
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
            PortalTask(
                title="Задача готово",
                creator_sub=admin.sub,
                assignee_sub=admin.sub,
                status="col_o4kqsv03",
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await sqlite_session.commit()
    await sqlite_session.refresh(approval_col)
    await sqlite_session.refresh(done_col)

    approval_bytes, _, _ = await task_svc.export_column_tasks_txt(sqlite_session, admin, approval_col.id)
    approval_txt = approval_bytes.decode("utf-8-sig")
    assert "Колонка: На согласовании" in approval_txt
    assert "Задача на согласовании" in approval_txt
    assert "Задача готово" not in approval_txt

    done_bytes, _, _ = await task_svc.export_column_tasks_txt(sqlite_session, admin, done_col.id)
    done_txt = done_bytes.decode("utf-8-sig")
    assert "Колонка: Готово" in done_txt
    assert "Задача готово" in done_txt
    assert "Задача на согласовании" not in done_txt

    done_chip = await task_svc.list_tasks(sqlite_session, admin, status=["done"], limit=200)
    assert {t.title for t in done_chip} == {"Задача готово"}
