"""Маппинг всех статусов Jira → колонки воронки специалистов."""

from __future__ import annotations

import uuid

import pytest
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.portal_specialists.services.jira_board_sync import upsert_columns_from_board_config
from app.portal_specialists.services.specialist_jira_status_map import (
    iter_jira_column_status_pairs,
    replace_status_maps_from_board_config,
    resolve_column_key_by_jira_status_id,
)
from sqlalchemy.ext.asyncio import AsyncSession


def test_iter_jira_column_status_pairs_includes_secondary_statuses() -> None:
    config = {
        "columnConfig": {
            "columns": [
                {
                    "name": "Передать во вне",
                    "statuses": [{"id": "10010"}, {"id": "10011"}],
                },
                {"name": "  ", "statuses": [{"id": "1"}]},
                {"name": "Без id", "statuses": [{"id": ""}]},
            ],
        },
    }
    pairs = iter_jira_column_status_pairs(config)
    assert pairs == [("10010", "Передать во вне"), ("10011", "Передать во вне")]


@pytest.mark.anyio
async def test_resolve_column_key_by_secondary_status_id(session_with_board: AsyncSession) -> None:
    col = PortalSpecialistColumn(
        id=uuid.uuid4(),
        key="peredat-vo-vne",
        title="Передать во вне",
        color="#6366f1",
        position=5,
        jira_status_id="10010",
    )
    session_with_board.add(col)
    await session_with_board.flush()

    n = await replace_status_maps_from_board_config(
        session_with_board,
        {
            "columnConfig": {
                "columns": [
                    {"name": "Передать во вне", "statuses": [{"id": "10010"}, {"id": "10011"}]},
                ],
            },
        },
        columns_by_title={"передать во вне": col},
    )
    await session_with_board.flush()

    assert n == 2
    assert await resolve_column_key_by_jira_status_id(session_with_board, "10011") == "peredat-vo-vne"
    assert await resolve_column_key_by_jira_status_id(session_with_board, "10010") == "peredat-vo-vne"
    assert await resolve_column_key_by_jira_status_id(session_with_board, "99999") is None


@pytest.mark.anyio
async def test_replace_status_maps_rebuilds_table(session_with_board: AsyncSession) -> None:
    col = PortalSpecialistColumn(
        id=uuid.uuid4(),
        key="col-a",
        title="Передать во вне",
        color="#6366f1",
        position=0,
    )
    session_with_board.add(col)
    await session_with_board.flush()

    await replace_status_maps_from_board_config(
        session_with_board,
        {"columnConfig": {"columns": [{"name": "Передать во вне", "statuses": [{"id": "1"}]}]}},
        columns_by_title={"передать во вне": col},
    )
    await session_with_board.flush()
    assert await resolve_column_key_by_jira_status_id(session_with_board, "1") == "col-a"

    n = await replace_status_maps_from_board_config(
        session_with_board,
        {"columnConfig": {"columns": [{"name": "Передать во вне", "statuses": [{"id": "2"}]}]}},
        columns_by_title={"передать во вне": col},
    )
    await session_with_board.flush()
    assert n == 1
    assert await resolve_column_key_by_jira_status_id(session_with_board, "1") is None
    assert await resolve_column_key_by_jira_status_id(session_with_board, "2") == "col-a"


@pytest.mark.anyio
async def test_upsert_columns_from_board_config_creates_peredat_vo_vne(
    session_with_board: AsyncSession,
) -> None:
    cols = await upsert_columns_from_board_config(
        session_with_board,
        {
            "columnConfig": {
                "columns": [
                    {"name": "Новичок", "statuses": [{"id": "1"}]},
                    {"name": "Передать во вне", "statuses": [{"id": "10010"}, {"id": "10011"}]},
                ],
            },
        },
    )
    await session_with_board.flush()
    keys = {c.key for c in cols}
    assert "peredat-vo-vne" in keys
    assert await resolve_column_key_by_jira_status_id(session_with_board, "10011") == "peredat-vo-vne"
