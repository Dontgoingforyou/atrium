"""Тесты маппинга колонок канбана → статусы доски AUTASKS."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.exceptions import ForbiddenError, ServiceUnavailableError
from app.portal_collab.services import task_jira_column_sync as sync_mod
from sqlalchemy import select


def test_normalize_and_aliases() -> None:
    assert sync_mod.normalize_column_title("  В  Работе ") == "в работе"
    assert sync_mod.resolve_jira_lookup_key("Бэклог") == "список задач"
    assert sync_mod.resolve_jira_lookup_key("Готово") == "выполнено"
    assert sync_mod.resolve_jira_lookup_key("В работе") == "в работе"


def test_build_index_and_status_lookup() -> None:
    config = {
        "columnConfig": {
            "columns": [
                {"name": "Список задач", "statuses": [{"id": "1"}]},
                {"name": "В работе", "statuses": [{"id": "2"}, {"id": "22"}]},
                {"name": "Выполнено", "statuses": [{"id": "3"}]},
                {"name": "Пустая", "statuses": []},
            ],
        },
    }
    index = sync_mod.build_jira_status_index(config)
    assert index == {
        "список задач": "1",
        "в работе": "2",
        "выполнено": "3",
    }
    assert sync_mod.status_id_for_cosmolet_title("Бэклог", index) == "1"
    assert sync_mod.status_id_for_cosmolet_title("Готово", index) == "3"
    assert sync_mod.status_id_for_cosmolet_title("В работе", index) == "2"
    assert sync_mod.status_id_for_cosmolet_title("Неизвестная", index) is None


@pytest.mark.asyncio
async def test_bind_column_sets_status_id() -> None:
    col = SimpleNamespace(title="Бэклог", jira_status_id=None)
    http = MagicMock()
    with patch.object(
        sync_mod,
        "fetch_tasks_board_status_index",
        new=AsyncMock(return_value={"список задач": "100"}),
    ):
        ok = await sync_mod.bind_column_jira_status_by_title(col, http)  # type: ignore[arg-type]
    assert ok is True
    assert col.jira_status_id == "100"


@pytest.mark.asyncio
async def test_bind_column_skips_when_jira_down() -> None:
    col = SimpleNamespace(title="Бэклог", jira_status_id=None)
    http = MagicMock()
    with patch.object(
        sync_mod,
        "fetch_tasks_board_status_index",
        new=AsyncMock(side_effect=ServiceUnavailableError("Jira")),
    ):
        ok = await sync_mod.bind_column_jira_status_by_title(col, http)  # type: ignore[arg-type]
    assert ok is False
    assert col.jira_status_id is None


@pytest.mark.asyncio
async def test_fetch_index_gate_when_jira_disabled() -> None:
    http = MagicMock()
    settings = SimpleNamespace(jira_enabled=False, jira_tasks_board_id=86)
    with patch.object(sync_mod, "get_settings", return_value=settings):
        with pytest.raises(ServiceUnavailableError, match="не настроена"):
            await sync_mod.fetch_tasks_board_status_index(http)


@pytest.mark.asyncio
async def test_sync_preserves_manual_id_when_unbound(sqlite_session) -> None:
    from app.infrastructure.db.models.portal_task import PortalTaskColumn

    from tests.helpers.portal_test_users import user_portal_admin

    admin = user_portal_admin()
    col = PortalTaskColumn(
        title="Кастомная",
        color="#444",
        status_key="custom",
        position=0,
        jira_status_id="manual-99",
    )
    sqlite_session.add(col)
    await sqlite_session.commit()

    http = MagicMock()
    with patch.object(
        sync_mod,
        "fetch_tasks_board_status_index",
        new=AsyncMock(return_value={"в работе": "20"}),
    ):
        report = await sync_mod.sync_task_column_jira_status_ids(sqlite_session, admin, http)

    assert report["bound"] == 0
    assert "Кастомная" in report["unbound_titles"]
    await sqlite_session.refresh(col)
    assert col.jira_status_id == "manual-99"


@pytest.mark.asyncio
async def test_sync_all_columns_report(sqlite_session) -> None:
    from app.infrastructure.db.models.portal_task import PortalTaskColumn

    from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular

    admin = user_portal_admin()
    sqlite_session.add(
        PortalTaskColumn(title="Бэклог", color="#111", status_key="todo", position=0),
    )
    sqlite_session.add(
        PortalTaskColumn(title="В работе", color="#222", status_key="in_progress", position=1),
    )
    sqlite_session.add(
        PortalTaskColumn(title="Сирота", color="#333", status_key="orphan", position=2),
    )
    await sqlite_session.commit()

    http = MagicMock()
    index = {"список задач": "10", "в работе": "20", "выполнено": "30"}
    with patch.object(sync_mod, "fetch_tasks_board_status_index", new=AsyncMock(return_value=index)):
        report = await sync_mod.sync_task_column_jira_status_ids(sqlite_session, admin, http)

    assert report["bound"] == 2
    assert "Сирота" in report["unbound_titles"]
    assert "выполнено" in report["jira_only_titles"]

    cols = (await sqlite_session.execute(select(PortalTaskColumn))).scalars().all()
    by_title = {c.title: c.jira_status_id for c in cols}
    assert by_title["Бэклог"] == "10"
    assert by_title["В работе"] == "20"
    assert by_title["Сирота"] is None

    with pytest.raises(ForbiddenError):
        await sync_mod.sync_task_column_jira_status_ids(sqlite_session, user_portal_regular(), http)
