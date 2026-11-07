"""Прямые вызовы task_home для веток счётчиков и превью (главная)."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import pytest
from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskColumn
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.services import task_home as task_home_svc
from app.portal_collab.services._task_due_calendar import today_portal
from app.portal_collab.services.task_column import kpi_excluded_status_keys
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular


def _now() -> datetime:
    return datetime.now(UTC)


def _due_on_portal_day(now: datetime, *, days_ago: int) -> datetime:
    """Полночь UTC календарного дня портала со сдвигом (как date-only due_at с фронта)."""
    day = today_portal(now) - timedelta(days=days_ago)
    return datetime.combine(day, time.min, tzinfo=UTC)


@pytest.mark.asyncio
async def test_count_my_tasks_home_open_and_overdue(sqlite_session: AsyncSession) -> None:
    user = user_portal_regular()
    now = _now()
    overdue = _due_on_portal_day(now, days_ago=1)
    sqlite_session.add_all(
        [
            PortalTask(
                title="Просрочена",
                creator_sub=user.sub,
                assignee_sub=user.sub,
                status=TaskStatus.TODO.value,
                priority=TaskPriority.MEDIUM.value,
                due_at=overdue,
                created_at=now,
                updated_at=now,
            ),
            PortalTask(
                title="В срок",
                creator_sub=user.sub,
                assignee_sub=user.sub,
                status=TaskStatus.IN_PROGRESS.value,
                priority=TaskPriority.LOW.value,
                due_at=now + timedelta(days=3),
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await sqlite_session.commit()
    kpi_excluded = await kpi_excluded_status_keys(sqlite_session)

    open_n, overdue_n = await task_home_svc.count_my_tasks_home_summary(sqlite_session, user, kpi_excluded=kpi_excluded)
    assert open_n >= 2
    assert overdue_n >= 1

    preview = await task_home_svc.list_my_tasks_home_preview(sqlite_session, user, limit=8, kpi_excluded=kpi_excluded)
    titles = {t.title for t in preview}
    assert "Просрочена" in titles


@pytest.mark.asyncio
async def test_due_today_not_counted_overdue(sqlite_session: AsyncSession) -> None:
    """Срок «сегодня» (полночь UTC этого дня портала) не входит в просроченные."""
    user = user_portal_regular()
    now = _now()
    sqlite_session.add(
        PortalTask(
            title="Срок сегодня",
            creator_sub=user.sub,
            assignee_sub=user.sub,
            status=TaskStatus.TODO.value,
            priority=TaskPriority.MEDIUM.value,
            due_at=_due_on_portal_day(now, days_ago=0),
            created_at=now,
            updated_at=now,
        )
    )
    await sqlite_session.commit()
    kpi_excluded = await kpi_excluded_status_keys(sqlite_session)

    _open_n, overdue_n = await task_home_svc.count_my_tasks_home_summary(
        sqlite_session, user, kpi_excluded=kpi_excluded
    )
    assert overdue_n == 0


@pytest.mark.asyncio
async def test_due_yesterday_counted_overdue(sqlite_session: AsyncSession) -> None:
    user = user_portal_regular()
    now = _now()
    sqlite_session.add(
        PortalTask(
            title="Срок вчера",
            creator_sub=user.sub,
            assignee_sub=user.sub,
            status=TaskStatus.TODO.value,
            priority=TaskPriority.MEDIUM.value,
            due_at=_due_on_portal_day(now, days_ago=1),
            created_at=now,
            updated_at=now,
        )
    )
    await sqlite_session.commit()
    kpi_excluded = await kpi_excluded_status_keys(sqlite_session)

    _open_n, overdue_n = await task_home_svc.count_my_tasks_home_summary(
        sqlite_session, user, kpi_excluded=kpi_excluded
    )
    assert overdue_n == 1


@pytest.mark.asyncio
async def test_done_task_with_past_due_not_counted_overdue(sqlite_session: AsyncSession) -> None:
    """Задача «Готово» с прошедшим сроком не входит в просроченные."""
    user = user_portal_regular()
    admin = user_portal_admin()
    now = _now()
    overdue = now - timedelta(days=2)
    sqlite_session.add(
        PortalTask(
            title="Готово но срок прошёл",
            creator_sub=user.sub,
            assignee_sub=user.sub,
            status=TaskStatus.DONE.value,
            priority=TaskPriority.MEDIUM.value,
            due_at=overdue,
            created_at=now - timedelta(days=5),
            updated_at=now,
        )
    )
    await sqlite_session.commit()
    kpi_excluded = await kpi_excluded_status_keys(sqlite_session)

    _open_n, overdue_n = await task_home_svc.count_my_tasks_home_summary(
        sqlite_session, user, kpi_excluded=kpi_excluded
    )
    assert overdue_n == 0

    overdue_preview = await task_home_svc.list_assignee_open_tasks_home_preview(
        sqlite_session,
        admin,
        user.sub,
        limit=8,
        kpi_excluded=kpi_excluded,
        overdue_only=True,
    )
    assert all(t.status != TaskStatus.DONE.value for t in overdue_preview)


@pytest.mark.asyncio
async def test_done_like_column_title_not_counted_overdue(sqlite_session: AsyncSession) -> None:
    """Кастомная колонка «Готово» (status_key ≠ done) не считается просроченной."""
    from app.portal_collab.services.task_column import closed_task_status_keys

    user = user_portal_regular()
    admin = user_portal_admin()
    now = _now()
    overdue = now - timedelta(days=2)
    sqlite_session.add(
        PortalTaskColumn(
            title="Готово",
            status_key="col_ready_custom",
            color="#1a9000",
            position=5,
            exclude_from_kpi=False,
        )
    )
    sqlite_session.add(
        PortalTask(
            title="Кастом готово просрочка",
            creator_sub=user.sub,
            assignee_sub=user.sub,
            status="col_ready_custom",
            priority=TaskPriority.MEDIUM.value,
            due_at=overdue,
            created_at=now - timedelta(days=5),
            updated_at=now,
        )
    )
    await sqlite_session.commit()
    kpi_excluded = await kpi_excluded_status_keys(sqlite_session)
    closed = await closed_task_status_keys(sqlite_session)
    assert "col_ready_custom" in closed

    _open_n, overdue_n = await task_home_svc.count_my_tasks_home_summary(
        sqlite_session, user, kpi_excluded=kpi_excluded, closed_statuses=closed
    )
    assert overdue_n == 0

    overdue_preview = await task_home_svc.list_assignee_open_tasks_home_preview(
        sqlite_session,
        admin,
        user.sub,
        limit=8,
        kpi_excluded=kpi_excluded,
        overdue_only=True,
        closed_statuses=closed,
    )
    assert all(t.status != "col_ready_custom" for t in overdue_preview)


@pytest.mark.asyncio
async def test_my_tasks_preview_includes_done_excluded_from_kpi_count(
    sqlite_session: AsyncSession,
) -> None:
    user = user_portal_regular()
    now = _now()
    sqlite_session.add(
        PortalTaskColumn(
            title="Готово",
            status_key="done",
            color="#1a9000",
            position=2,
            exclude_from_kpi=True,
        )
    )
    sqlite_session.add(
        PortalTask(
            title="Завершённая",
            creator_sub=user.sub,
            assignee_sub=user.sub,
            status=TaskStatus.DONE.value,
            priority=TaskPriority.MEDIUM.value,
            created_at=now,
            updated_at=now,
        )
    )
    sqlite_session.add(
        PortalTask(
            title="Активная кастом",
            creator_sub=user.sub,
            assignee_sub=user.sub,
            status="col_custom01",
            priority=TaskPriority.MEDIUM.value,
            created_at=now,
            updated_at=now,
        )
    )
    await sqlite_session.commit()
    kpi_excluded = await kpi_excluded_status_keys(sqlite_session)
    assert "done" in kpi_excluded

    open_n, _ = await task_home_svc.count_my_tasks_home_summary(sqlite_session, user, kpi_excluded=kpi_excluded)
    assert open_n == 1

    preview = await task_home_svc.list_my_tasks_home_preview(sqlite_session, user, limit=8, kpi_excluded=kpi_excluded)
    titles = {t.title for t in preview}
    assert "Завершённая" in titles
    assert "Активная кастом" in titles


@pytest.mark.asyncio
async def test_admin_team_done_this_month_no_assignee_and_assignee_load(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    now = _now()
    month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
    sqlite_session.add_all(
        [
            PortalTask(
                title="Закрыта в месяце",
                creator_sub="x",
                assignee_sub="y",
                status=TaskStatus.DONE.value,
                priority=TaskPriority.MEDIUM.value,
                created_at=now - timedelta(days=5),
                updated_at=month_start + timedelta(hours=2),
            ),
            PortalTask(
                title="Без исполнителя",
                creator_sub="x",
                assignee_sub=None,
                status=TaskStatus.TODO.value,
                priority=TaskPriority.HIGH.value,
                created_at=now,
                updated_at=now,
            ),
            PortalTask(
                title="У a два открытых",
                creator_sub="x",
                assignee_sub="assignee-a",
                status=TaskStatus.TODO.value,
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
            PortalTask(
                title="У a второй",
                creator_sub="x",
                assignee_sub="assignee-a",
                status=TaskStatus.IN_PROGRESS.value,
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await sqlite_session.commit()
    kpi_excluded = await kpi_excluded_status_keys(sqlite_session)

    done_m = await task_home_svc.count_admin_team_done_this_month(sqlite_session, admin)
    assert done_m >= 1
    no_asg = await task_home_svc.count_admin_team_no_assignee(sqlite_session, admin, kpi_excluded=kpi_excluded)
    assert no_asg >= 1

    load = await task_home_svc.list_admin_team_assignee_load(sqlite_session, admin, kpi_excluded=kpi_excluded, limit=5)
    by_sub = {r["assignee_sub"]: r for r in load}
    assert "assignee-a" in by_sub
    assert by_sub["assignee-a"]["open_count"] >= 2


@pytest.mark.asyncio
async def test_get_assignee_display_info_from_profile(sqlite_session: AsyncSession) -> None:
    """Имя из profile; avatar — подписанный proxy EA (не зависит от env CI)."""
    from unittest.mock import patch

    sqlite_session.add(
        PortalUserProfile(
            sub="assignee-with-profile",
            full_name="Иван Иванов",
            email="ivan@example.com",
            username="ivan",
        )
    )
    await sqlite_session.commit()

    photo = "/api/v1/portal/users/assignee-with-profile/photo?e=1"
    with patch(
        "app.portal_collab.services._task_home_common.build_user_photo_proxy_url",
        return_value=photo,
    ) as build_photo:
        display_name, avatar_url, focal_x, focal_y = await task_home_svc.get_assignee_display_info(
            sqlite_session, "assignee-with-profile"
        )

    assert display_name == "Иван Иванов"
    assert avatar_url == photo
    assert focal_x is None
    assert focal_y is None
    build_photo.assert_called_once()
    assert build_photo.call_args.kwargs["user_sub"] == "assignee-with-profile"
    assert build_photo.call_args.kwargs["email"] == "ivan@example.com"


@pytest.mark.asyncio
async def test_get_assignee_display_info_without_profile_returns_none(sqlite_session: AsyncSession) -> None:
    """Нет профиля — все поля None (вызывающий код сам решает фолбэк, как во фронтенде на assignee_sub)."""
    display_name, avatar_url, focal_x, focal_y = await task_home_svc.get_assignee_display_info(
        sqlite_session, "unknown-sub"
    )
    assert display_name is None
    assert avatar_url is None
    assert focal_x is None
    assert focal_y is None


@pytest.mark.asyncio
async def test_non_admin_team_preview_and_counts_are_empty(sqlite_session: AsyncSession) -> None:
    user = user_portal_regular()
    kpi_excluded = frozenset()
    assert (
        await task_home_svc.list_admin_team_tasks_home_preview(sqlite_session, user, limit=5, kpi_excluded=kpi_excluded)
        == []
    )
    o, ov = await task_home_svc.count_admin_team_tasks_home_summary(sqlite_session, user, kpi_excluded=kpi_excluded)
    assert o == 0 and ov == 0
    assert await task_home_svc.count_admin_team_done_this_month(sqlite_session, user) == 0


def test_column_title_predicates_split_ready_approval_cancelled() -> None:
    from app.portal_collab.services._task_home_common import (
        is_approval_like_column_title,
        is_cancelled_like_column_title,
        is_done_like_column_title,
    )

    assert is_done_like_column_title("Готово")
    assert is_done_like_column_title("готовые")
    assert is_done_like_column_title("Завершена")
    assert not is_done_like_column_title("На согласовании")
    assert not is_done_like_column_title("Отменена")
    assert is_approval_like_column_title("На согласовании")
    assert is_approval_like_column_title("Согласовано")
    assert not is_approval_like_column_title("Готово")
    assert is_cancelled_like_column_title("Отменена")
    assert is_cancelled_like_column_title("cancelled")


@pytest.mark.asyncio
async def test_admin_team_done_this_month_and_open_treat_ready_as_closed(
    sqlite_session: AsyncSession,
) -> None:
    """KPI месяца — Готово и На согласовании; открытые без «Готово» даже без флага."""
    admin = user_portal_admin()
    now = _now()
    sqlite_session.add(
        PortalTaskColumn(
            title="На согласовании",
            status_key="done",
            color="#3b82f6",
            position=8,
            exclude_from_kpi=True,
        )
    )
    sqlite_session.add(
        PortalTaskColumn(
            title="Готово",
            status_key="col_o4kqsv03",
            color="#1a9000",
            position=9,
            exclude_from_kpi=False,
        )
    )
    sqlite_session.add_all(
        [
            PortalTask(
                title="Готово за месяц",
                creator_sub="x",
                assignee_sub="y",
                status="col_o4kqsv03",
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
            PortalTask(
                title="Согласование за месяц",
                creator_sub="x",
                assignee_sub="y",
                status=TaskStatus.DONE.value,
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
            PortalTask(
                title="Открытая",
                creator_sub="x",
                assignee_sub="y",
                status=TaskStatus.TODO.value,
                priority=TaskPriority.MEDIUM.value,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await sqlite_session.commit()

    done_m = await task_home_svc.count_admin_team_done_this_month(sqlite_session, admin)
    assert done_m == 2

    kpi_excluded = await kpi_excluded_status_keys(sqlite_session)
    assert "col_o4kqsv03" in kpi_excluded
    assert "done" in kpi_excluded
    open_n, overdue_n = await task_home_svc.count_admin_team_tasks_home_summary(
        sqlite_session, admin, kpi_excluded=kpi_excluded
    )
    assert open_n == 1
    assert overdue_n == 0
