"""Публичные сервисы колонок доски и комментариев задач."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_task import PortalTaskColumn
from app.portal_collab.schemas.task import (
    PortalTaskColumnCreate,
    PortalTaskColumnUpdate,
    PortalTaskCreate,
    PortalTaskUpdate,
    TaskBoardPrefWrite,
    TaskCommentCreate,
    TaskCommentUpdate,
)
from app.portal_collab.services import task as task_svc
from app.portal_collab.services import task_board_pref as board_pref_svc
from app.portal_collab.services import task_column as column_svc
from app.portal_collab.services import task_comment as comment_svc
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_manager_students_outstaff,
    user_portal_admin,
    user_portal_no_idp_groups,
    user_portal_regular,
)


@pytest.mark.asyncio
async def test_task_board_pref_service_get_empty_put_insert_get_mapping(sqlite_session: AsyncSession) -> None:
    user = user_portal_regular()
    empty = await board_pref_svc.get_task_board_pref(sqlite_session, user)
    assert empty.column_order == []
    assert empty.hidden_status_keys == []
    assert empty.title_overrides == {}

    body = TaskBoardPrefWrite(
        column_order=["done", "todo"],
        hidden_status_keys=["cancelled"],
        title_overrides={"todo": "Входящие"},
    )
    saved = await board_pref_svc.put_task_board_pref(sqlite_session, user, body)
    assert saved.column_order == ["done", "todo"]
    assert saved.hidden_status_keys == ["cancelled"]
    assert saved.title_overrides == {"todo": "Входящие"}

    loaded = await board_pref_svc.get_task_board_pref(sqlite_session, user)
    assert loaded.column_order == ["done", "todo"]
    assert loaded.hidden_status_keys == ["cancelled"]
    assert loaded.title_overrides == {"todo": "Входящие"}

    body2 = TaskBoardPrefWrite(
        column_order=["todo"],
        hidden_status_keys=[],
        title_overrides={},
    )
    updated = await board_pref_svc.put_task_board_pref(sqlite_session, user, body2)
    assert updated.column_order == ["todo"]


@pytest.mark.asyncio
async def test_task_column_service_list_global_only(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    sk = f"g_{uuid.uuid4().hex[:8]}"
    await column_svc.create_task_column(
        sqlite_session,
        admin,
        PortalTaskColumnCreate(title="Глобальная", color="#111111", status_key=sk, position=10),
    )
    cols = await column_svc.list_task_columns(sqlite_session, admin)
    assert any(c.status_key == sk for c in cols)


@pytest.mark.asyncio
async def test_task_column_service_create_forbidden_without_team_role(sqlite_session: AsyncSession) -> None:
    user = user_portal_no_idp_groups()
    with pytest.raises(ForbiddenError, match="колонками"):
        await column_svc.create_task_column(
            sqlite_session,
            user,
            PortalTaskColumnCreate(
                title="X",
                color="#ffffff",
                status_key=f"x_{uuid.uuid4().hex[:6]}",
                position=0,
            ),
        )


@pytest.mark.asyncio
async def test_task_column_service_update_delete_not_found(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    missing = uuid.uuid4()
    with pytest.raises(NotFoundError, match="Колонка"):
        await column_svc.update_task_column(
            sqlite_session,
            admin,
            missing,
            PortalTaskColumnUpdate(title="Нет такой"),
        )
    with pytest.raises(NotFoundError, match="Колонка"):
        await column_svc.delete_task_column(sqlite_session, admin, missing)


@pytest.mark.asyncio
async def test_task_column_service_update_partial_fields(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    sk = f"p_{uuid.uuid4().hex[:8]}"
    col = await column_svc.create_task_column(
        sqlite_session,
        admin,
        PortalTaskColumnCreate(title="Было", color="#aaaaaa", status_key=sk, position=3),
    )
    u1 = await column_svc.update_task_column(sqlite_session, admin, col.id, PortalTaskColumnUpdate(title="Стало"))
    assert u1.title == "Стало" and u1.color == "#aaaaaa"
    u2 = await column_svc.update_task_column(sqlite_session, admin, col.id, PortalTaskColumnUpdate(position=9))
    assert u2.position == 9
    u3 = await column_svc.update_task_column(sqlite_session, admin, col.id, PortalTaskColumnUpdate(color="#bbbbbb"))
    assert u3.color == "#bbbbbb"


@pytest.mark.asyncio
async def test_task_column_service_delete_empty_column_ok(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    sk = f"del_{uuid.uuid4().hex[:8]}"
    col = await column_svc.create_task_column(
        sqlite_session,
        admin,
        PortalTaskColumnCreate(title="На удаление", color="#ccc", status_key=sk, position=0),
    )
    await column_svc.delete_task_column(sqlite_session, admin, col.id)
    assert await sqlite_session.get(PortalTaskColumn, col.id) is None


@pytest.mark.parametrize(
    ("n_tasks", "needle"),
    [
        (1, "задача"),
        (3, "задачи"),
        (6, "задач"),
    ],
)
@pytest.mark.asyncio
async def test_task_column_service_delete_conflict_russian_grammar(
    sqlite_session: AsyncSession,
    n_tasks: int,
    needle: str,
) -> None:
    admin = user_portal_admin()
    sk = f"st_{uuid.uuid4().hex[:8]}"
    col = await column_svc.create_task_column(
        sqlite_session,
        admin,
        PortalTaskColumnCreate(title="Удалить нельзя", color="#000000", status_key=sk, position=0),
    )
    for _ in range(n_tasks):
        t = await task_svc.create_task(
            sqlite_session,
            admin,
            PortalTaskCreate(title="В колонке", assignee_sub="admin-sub"),
        )
        await task_svc.update_task(sqlite_session, admin, t.id, PortalTaskUpdate(expected_version=1, status=sk))

    with pytest.raises(ConflictError) as exc:
        await column_svc.delete_task_column(sqlite_session, admin, col.id)
    assert needle in exc.value.message.lower()


@pytest.mark.asyncio
async def test_task_comment_update_not_found_comment_id(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    task = await task_svc.create_task(sqlite_session, admin, PortalTaskCreate(title="T", assignee_sub="admin-sub"))
    with pytest.raises(NotFoundError, match="Комментарий"):
        await comment_svc.update_comment(
            sqlite_session,
            admin,
            task.id,
            uuid.uuid4(),
            TaskCommentUpdate(expected_version=1, body="x"),
        )


@pytest.mark.asyncio
async def test_task_comment_create_parent_belongs_to_other_task(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()
    t1 = await task_svc.create_task(sqlite_session, admin, PortalTaskCreate(title="A", assignee_sub="admin-sub"))
    t2 = await task_svc.create_task(sqlite_session, admin, PortalTaskCreate(title="B", assignee_sub="admin-sub"))

    class _FakeMgr:
        async def publish(self, _task_id: uuid.UUID, _payload: dict) -> None:
            return None

    monkeypatch.setattr(
        "app.portal_collab.services.task_comment.get_task_comments_manager",
        lambda: _FakeMgr(),
    )
    monkeypatch.setattr(
        "app.portal_chat.services.inbox_publish.publish_portal_notification_update",
        lambda _sub, **_kw: None,
    )

    root = await comment_svc.create_comment(
        sqlite_session,
        admin,
        t1.id,
        TaskCommentCreate(body="К t1", mentions=[]),
    )

    with pytest.raises(NotFoundError, match="Родительск"):
        await comment_svc.create_comment(
            sqlite_session,
            admin,
            t2.id,
            TaskCommentCreate(body="Чужой parent", mentions=[], parent_id=root.id),
        )


@pytest.mark.asyncio
async def test_task_comment_create_publishes_inbox_for_each_notified_sub(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Упоминания", assignee_sub="admin-sub"),
    )

    nid_one, nid_two = uuid.uuid4(), uuid.uuid4()
    notified: dict[str, uuid.UUID] = {"sub-one": nid_one, "sub-two": nid_two}

    async def _fake_mentions(*_a: Any, **_kw: Any) -> dict[str, uuid.UUID]:
        return dict(notified)

    pubs: list[tuple[list[str], dict[str, uuid.UUID] | None]] = []

    async def _record_pub(
        subs: list[str],
        *,
        notification_ids_by_sub: dict[str, uuid.UUID] | None = None,
    ) -> None:
        pubs.append((list(subs), notification_ids_by_sub))

    class _FakeMgr:
        async def publish(self, _task_id: uuid.UUID, _payload: dict) -> None:
            return None

    monkeypatch.setattr(
        "app.portal_collab.services.task_comment.notification_svc.create_mention_notifications",
        _fake_mentions,
    )
    monkeypatch.setattr(
        "app.portal_collab.services.task_comment.publish_portal_notification_updates",
        _record_pub,
    )
    monkeypatch.setattr(
        "app.portal_collab.services.task_comment.get_task_comments_manager",
        lambda: _FakeMgr(),
    )

    await comment_svc.create_comment(
        sqlite_session,
        admin,
        task.id,
        TaskCommentCreate(body="Привет", mentions=[]),
    )
    assert pubs == [(["sub-one", "sub-two"], notified)]


@pytest.mark.asyncio
async def test_task_comment_update_body_and_mentions(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()
    task = await task_svc.create_task(sqlite_session, admin, PortalTaskCreate(title="Правки", assignee_sub="admin-sub"))

    class _FakeMgr:
        async def publish(self, _task_id: uuid.UUID, _payload: dict) -> None:
            return None

    monkeypatch.setattr(
        "app.portal_collab.services.task_comment.get_task_comments_manager",
        lambda: _FakeMgr(),
    )

    c = await comment_svc.create_comment(
        sqlite_session,
        admin,
        task.id,
        TaskCommentCreate(body="Старое", mentions=["a"]),
    )
    assert c.mentions == ["a"]

    upd = await comment_svc.update_comment(
        sqlite_session,
        admin,
        task.id,
        c.id,
        TaskCommentUpdate(expected_version=1, body="Новое", mentions=["b", "c"]),
    )
    assert upd.body == "Новое"
    assert upd.mentions == ["b", "c"]


@pytest.mark.asyncio
async def test_task_comment_update_delete_forbidden_non_author(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()
    foreign = user_portal_regular()
    # Инициатор задачи — foreign, иначе get_task отсекает чужого пользователя раньше проверки автора комментария.
    task = await task_svc.create_task(
        sqlite_session,
        foreign,
        PortalTaskCreate(title="Чужой коммент", assignee_sub="user-sub"),
    )

    class _FakeMgr:
        async def publish(self, _task_id: uuid.UUID, _payload: dict) -> None:
            return None

    monkeypatch.setattr(
        "app.portal_collab.services.task_comment.get_task_comments_manager",
        lambda: _FakeMgr(),
    )

    c = await comment_svc.create_comment(
        sqlite_session,
        admin,
        task.id,
        TaskCommentCreate(body="Только админ", mentions=[]),
    )
    with pytest.raises(ForbiddenError, match="изменение"):
        await comment_svc.update_comment(
            sqlite_session,
            foreign,
            task.id,
            c.id,
            TaskCommentUpdate(expected_version=1, body="Взлом"),
        )
    with pytest.raises(ForbiddenError, match="удаление"):
        await comment_svc.delete_comment(sqlite_session, foreign, task.id, c.id)


@pytest.mark.asyncio
async def test_task_comment_delete_by_author_publishes(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = user_portal_regular()

    class _FakeMgr:
        async def publish(self, _task_id: uuid.UUID, _payload: dict) -> None:
            return None

    monkeypatch.setattr(
        "app.portal_collab.services.task_comment.get_task_comments_manager",
        lambda: _FakeMgr(),
    )

    task = await task_svc.create_task(
        sqlite_session,
        owner,
        PortalTaskCreate(title="Удаление комментария", assignee_sub="user-sub"),
    )
    c = await comment_svc.create_comment(
        sqlite_session,
        owner,
        task.id,
        TaskCommentCreate(body="Временный", mentions=[]),
    )
    await comment_svc.delete_comment(sqlite_session, owner, task.id, c.id)


@pytest.mark.asyncio
async def test_task_column_exclude_from_kpi_admin_only(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    manager = user_manager_students_outstaff()
    regular = user_portal_regular()
    sk = f"kpi_{uuid.uuid4().hex[:8]}"
    col = await column_svc.create_task_column(
        sqlite_session,
        admin,
        PortalTaskColumnCreate(title="KPI test", color="#ccc", status_key=sk, position=0),
    )

    with pytest.raises(ForbiddenError, match="KPI"):
        await column_svc.update_task_column(
            sqlite_session,
            regular,
            col.id,
            PortalTaskColumnUpdate(exclude_from_kpi=True),
        )
    with pytest.raises(ForbiddenError, match="KPI"):
        await column_svc.update_task_column(
            sqlite_session,
            manager,
            col.id,
            PortalTaskColumnUpdate(exclude_from_kpi=True),
        )

    updated = await column_svc.update_task_column(
        sqlite_session,
        admin,
        col.id,
        PortalTaskColumnUpdate(exclude_from_kpi=True),
    )
    assert updated.exclude_from_kpi is True

    keys = await column_svc.kpi_excluded_status_keys(sqlite_session)
    assert sk in keys
