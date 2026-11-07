"""HTTP-контракт главной: RBAC, изоляция превью, точные счётчики."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta

import pytest
from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.models.portal_task import PortalTaskColumn
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.services._task_due_calendar import today_portal
from app.schemas.auth import UserPublic
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_portal_admin,
    user_portal_manager,
    user_portal_no_idp_groups,
    user_portal_user_b,
)
from tests.portal_home.conftest import (
    HOME_API,
    add_favorite_doc,
    add_task,
    as_user,
    assert_api_error,
    assert_pydantic_422,
    user_admin_and_manager,
)


@pytest.mark.parametrize("params", [{}, {"assignee_sub": "x"}])
async def test_home_requires_auth(
    client_sqlite_only: AsyncClient,
    params: dict[str, str],
) -> None:
    r = await client_sqlite_only.get(HOME_API, params=params)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize("params", [{}, {"assignee_sub": "x"}])
async def test_home_timesheet_forbidden(
    client_developer: AsyncClient,
    params: dict[str, str],
) -> None:
    r = await client_developer.get(HOME_API, params=params)
    assert_api_error(r, 403, "forbidden")


@pytest.mark.parametrize("assignee_sub", ["someone-else-sub", "user-no-idp"])
async def test_home_drilldown_forbidden_for_regular(
    client_no_idp: AsyncClient,
    assignee_sub: str,
) -> None:
    r = await client_no_idp.get(HOME_API, params={"assignee_sub": assignee_sub})
    assert_api_error(r, 403, "forbidden")


async def test_home_drilldown_forbidden_for_outstaff_not_manager(
    client_outstaff_not_manager: AsyncClient,
) -> None:
    r = await client_outstaff_not_manager.get(HOME_API, params={"assignee_sub": "someone-else-sub"})
    assert_api_error(r, 403, "forbidden")


async def test_home_assignee_sub_too_long_is_422(client_admin: AsyncClient) -> None:
    r = await client_admin.get(HOME_API, params={"assignee_sub": "x" * 256})
    assert_pydantic_422(r)


@pytest.mark.parametrize(
    ("user_factory", "expect_admin"),
    [
        (user_portal_no_idp_groups, False),
        (user_portal_manager, False),
        (user_admin_and_manager, True),
    ],
)
async def test_home_manager_always_null_admin_only_for_portal_admin(
    client_admin: AsyncClient,
    user_factory: Callable[[], UserPublic],
    expect_admin: bool,
) -> None:
    with as_user(user_factory):
        r = await client_admin.get(HOME_API)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["manager"] is None
    assert (data["admin"] is not None) is expect_admin
    assert data["search"]["get_path"] == "/api/v1/portal/search"
    assert data["assignee_drilldown"] is None


async def test_home_my_tasks_isolated_exact_counts(
    client_no_idp: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    viewer = user_portal_no_idp_groups()
    now = datetime.now(UTC)
    sqlite_session.add(
        PortalTaskColumn(
            title="Готово",
            status_key=TaskStatus.DONE.value,
            color="#1a9000",
            position=2,
            exclude_from_kpi=True,
        )
    )
    await add_task(
        sqlite_session,
        title="Своя в срок",
        creator_sub=viewer.sub,
        assignee_sub=viewer.sub,
        due_at=now + timedelta(days=3),
    )
    await add_task(
        sqlite_session,
        title="Своя просрочена",
        creator_sub=viewer.sub,
        assignee_sub=viewer.sub,
        due_at=datetime.combine(today_portal(now) - timedelta(days=1), time.min, tzinfo=UTC),
    )
    await add_task(
        sqlite_session,
        title="Своя готово",
        creator_sub=viewer.sub,
        assignee_sub=viewer.sub,
        status=TaskStatus.DONE.value,
        due_at=now - timedelta(days=2),
    )
    await add_task(
        sqlite_session,
        title="Чужая",
        creator_sub=user_portal_user_b().sub,
        assignee_sub=user_portal_user_b().sub,
    )
    await sqlite_session.commit()

    r = await client_no_idp.get(HOME_API)
    assert r.status_code == 200, r.text
    data = r.json()
    titles = {t["title"] for t in data["my_tasks_preview"]}
    assert titles == {"Своя в срок", "Своя просрочена", "Своя готово"}
    assert data["my_tasks_open_count"] == 2
    assert data["my_tasks_overdue_count"] == 1
    assert data["admin"] is None
    assert data["manager"] is None


async def test_home_my_tasks_preview_includes_junction_assignee_subs(
    client_no_idp: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    viewer = user_portal_no_idp_groups()
    peer_sub = "second-assignee-sub"
    await add_task(
        sqlite_session,
        title="Задача с несколькими исполнителями",
        creator_sub="creator-sub",
        assignee_sub=None,
        assignee_subs=[viewer.sub, peer_sub],
    )
    await sqlite_session.commit()

    r = await client_no_idp.get(HOME_API)
    assert r.status_code == 200, r.text
    preview = r.json()["my_tasks_preview"]
    assert len(preview) == 1
    hit = preview[0]
    assert hit["title"] == "Задача с несколькими исполнителями"
    assert set(hit["assignee_subs"]) == {viewer.sub, peer_sub}
    assert hit["assignee_sub"] == hit["assignee_subs"][0]


async def test_home_my_tasks_preview_limit_eight(
    client_no_idp: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    viewer = user_portal_no_idp_groups()
    for i in range(9):
        await add_task(
            sqlite_session,
            title=f"Задача {i}",
            creator_sub=viewer.sub,
            assignee_sub=viewer.sub,
        )
    await sqlite_session.commit()

    r = await client_no_idp.get(HOME_API)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["my_tasks_preview"]) == 8
    assert data["my_tasks_open_count"] == 9


async def test_home_favorites_preview_own_live_only_and_limit(
    client_no_idp: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    viewer = user_portal_no_idp_groups()
    now = datetime.now(UTC)
    live, _ = await add_favorite_doc(
        sqlite_session,
        title="Своя живая",
        user_sub=viewer.sub,
        fav_created_at=now - timedelta(hours=1),
    )
    await add_favorite_doc(
        sqlite_session,
        title="Своя в корзине",
        user_sub=viewer.sub,
        deleted_at=now,
        fav_created_at=now,
    )
    await add_favorite_doc(
        sqlite_session,
        title="Чужая звезда",
        user_sub=user_portal_user_b().sub,
        fav_created_at=now,
    )
    await sqlite_session.commit()

    r = await client_no_idp.get(HOME_API)
    assert r.status_code == 200, r.text
    preview = r.json()["favorites_preview"]
    assert len(preview) == 1
    assert preview[0]["title"] == "Своя живая"
    assert preview[0]["target_id"] == str(live.id)

    for i in range(9):
        await add_favorite_doc(
            sqlite_session,
            title=f"Ещё живая {i}",
            user_sub=viewer.sub,
            fav_created_at=now - timedelta(minutes=i),
        )
    await sqlite_session.commit()

    r = await client_no_idp.get(HOME_API)
    assert r.status_code == 200, r.text
    assert len(r.json()["favorites_preview"]) == 8


async def test_home_admin_block_exact_team_metrics(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    assignee_sub = "assignee-with-profile"
    sqlite_session.add(
        PortalUserProfile(
            sub=assignee_sub,
            full_name="Иван Иванов",
            email="ivan@example.com",
            username="ivan",
        )
    )
    await add_task(
        sqlite_session,
        title="Задача команды",
        creator_sub=user_portal_admin().sub,
        assignee_sub=assignee_sub,
        priority=TaskPriority.MEDIUM.value,
    )
    await sqlite_session.commit()

    r = await client_admin.get(HOME_API)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["manager"] is None
    adm = data["admin"]
    assert adm is not None
    assert adm["team_open_count"] == 1
    assert adm["team_open_by_priority"] == {"low": 0, "medium": 1, "high": 0}
    titles = {t["title"] for t in adm["team_tasks_preview"]}
    assert titles == {"Задача команды"}
    entry = next(e for e in adm["team_assignee_load"] if e["assignee_sub"] == assignee_sub)
    assert entry["display_name"] == "Иван Иванов"
    assert entry["open_count"] == 1


async def test_home_admin_no_assignee_ignores_junction_only(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Задача с исполнителями только в junction — не «без исполнителя»."""
    await add_task(
        sqlite_session,
        title="По-настоящему без исполнителя",
        creator_sub=user_portal_admin().sub,
        assignee_sub=None,
    )
    await add_task(
        sqlite_session,
        title="Только junction",
        creator_sub=user_portal_admin().sub,
        assignee_sub=None,
        assignee_subs=["junction-only-sub"],
    )
    await sqlite_session.commit()

    r = await client_admin.get(HOME_API)
    assert r.status_code == 200, r.text
    assert r.json()["admin"]["team_no_assignee_count"] == 1


async def test_home_admin_assignee_load_counts_task_once_per_assignee(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Одна задача с двумя junction-исполнителями — open_count=1 у каждого, не декартово."""
    await add_task(
        sqlite_session,
        title="Два исполнителя",
        creator_sub=user_portal_admin().sub,
        assignee_sub=None,
        assignee_subs=["load-a", "load-b"],
    )
    await sqlite_session.commit()

    r = await client_admin.get(HOME_API)
    assert r.status_code == 200, r.text
    by_sub = {e["assignee_sub"]: e["open_count"] for e in r.json()["admin"]["team_assignee_load"]}
    assert by_sub["load-a"] == 1
    assert by_sub["load-b"] == 1


async def test_home_assignee_drilldown_manager_exact(
    client_manager: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    assignee_sub = "peer-assignee-sub"
    sqlite_session.add(
        PortalUserProfile(
            sub=assignee_sub,
            email="peer@example.com",
            full_name="Peer Assignee",
            username="peer",
        )
    )
    await add_task(
        sqlite_session,
        title="Задача коллеги",
        creator_sub=user_portal_manager().sub,
        assignee_sub=assignee_sub,
    )
    await sqlite_session.commit()

    r = await client_manager.get(HOME_API, params={"assignee_sub": assignee_sub})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["admin"] is None
    assert data["manager"] is None
    drill = data["assignee_drilldown"]
    assert drill is not None
    assert drill["assignee_sub"] == assignee_sub
    assert drill["open_count"] == 1
    assert drill["overdue_count"] == 0
    assert drill["display_name"] == "Peer Assignee"
    assert {t["title"] for t in drill["open_tasks_preview"]} == {"Задача коллеги"}


async def test_home_assignee_drilldown_unknown_is_empty_not_404(
    client_manager: AsyncClient,
) -> None:
    r = await client_manager.get(HOME_API, params={"assignee_sub": "unknown-nobody-sub"})
    assert r.status_code == 200, r.text
    drill = r.json()["assignee_drilldown"]
    assert drill is not None
    assert drill["assignee_sub"] == "unknown-nobody-sub"
    assert drill["open_count"] == 0
    assert drill["overdue_count"] == 0
    assert drill["display_name"] is None
    assert drill["open_tasks_preview"] == []


async def test_home_assignee_drilldown_admin_ok(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    assignee_sub = "admin-peer-sub"
    await add_task(
        sqlite_session,
        title="Задача для админ-drill-down",
        creator_sub=user_portal_admin().sub,
        assignee_sub=assignee_sub,
    )
    await sqlite_session.commit()

    r = await client_admin.get(HOME_API, params={"assignee_sub": assignee_sub})
    assert r.status_code == 200, r.text
    drill = r.json()["assignee_drilldown"]
    assert drill is not None
    assert drill["assignee_sub"] == assignee_sub
    assert drill["open_count"] == 1
    assert r.json()["admin"] is not None
