"""Юнит-тесты search.py: merge и SQL-регрессии semantic RBAC (мок execute / pgvector)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.enums import LearningMaterialStatus
from app.core.exceptions import BadRequestError, ServiceUnavailableError
from app.core.portal_search_constants import (
    PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT,
    PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT,
    PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE,
    PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
    PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
    PORTAL_SEARCH_ENTITY_TYPE_TASK,
)
from app.portal_search.services import search as search_svc
from app.portal_search.services.search_orchestrator import run_fulltext_search

from tests.helpers.portal_test_users import (
    user_portal_admin,
    user_portal_developer,
    user_portal_manager,
    user_portal_no_idp_groups,
    user_portal_regular,
)


def test_merge_cap_bounds() -> None:
    assert search_svc.merge_cap(0, 10) == 110
    assert search_svc.merge_cap(400, 200) == 500


async def test_overlong_query_is_not_sent_to_calendar() -> None:
    remote = MagicMock()
    remote.search_events = AsyncMock()
    hits = await run_fulltext_search(
        MagicMock(),
        user_portal_regular(),
        "а" * 201,
        [PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT],
        tag_slug=None,
        status_ids=None,
        skip=0,
        limit=20,
        calendar_remote=remote,
    )
    assert hits == []
    remote.search_events.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        ServiceUnavailableError("Календарь временно недоступен"),
        BadRequestError("Проверьте поля запроса"),
    ],
)
async def test_calendar_rejection_does_not_fail_search(error: Exception) -> None:
    remote = MagicMock()
    remote.search_events = AsyncMock(side_effect=error)
    hits = await run_fulltext_search(
        MagicMock(),
        user_portal_regular(),
        "бенч",
        [PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT],
        tag_slug=None,
        status_ids=None,
        skip=0,
        limit=20,
        calendar_remote=remote,
    )
    assert hits == []


def test_merge_and_slice_orders_desc_and_paginates() -> None:
    d0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    d1 = datetime(2024, 6, 1, 12, 0, 0)
    d2 = datetime(2024, 3, 1, 12, 0, 0, tzinfo=UTC)
    out = search_svc.merge_and_slice([(d2, "c"), (d0, "a"), (d1, "b")], skip=0, limit=10)
    assert out == ["b", "c", "a"]
    page = search_svc.merge_and_slice([(d0, "a"), (d2, "c")], skip=1, limit=1)
    assert page == ["a"]


def test_merge_and_slice_preserves_aware_datetime_sort_key() -> None:
    aware = datetime(2025, 1, 1, tzinfo=UTC)
    older = datetime(2024, 1, 1, tzinfo=UTC)
    assert search_svc.merge_and_slice([(older, "old"), (aware, "new")], skip=0, limit=1) == ["new"]


def _row(
    *,
    entity_type: str = PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
    entity_id: str | None = None,
    text_content: str = "sample",
    meta: object | None = None,
    similarity_score: float = 0.85,
) -> MagicMock:
    r = MagicMock()
    r.entity_type = entity_type
    r.entity_id = entity_id or str(uuid.uuid4())
    r.text_content = text_content
    r.meta = meta if meta is not None else {}
    r.similarity_score = similarity_score
    return r


def _session_with_fetchall(rows: list[MagicMock]) -> AsyncMock:
    session = MagicMock()
    result = MagicMock()
    result.fetchall.return_value = rows
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_semantic_search_maps_rows_and_normalizes_meta() -> None:
    rows = [_row(meta={"x": 1}), _row(meta=["not", "dict"])]
    session = _session_with_fetchall(rows)
    out = await search_svc.semantic_search(
        session,
        [0.25, 0.5],
        [PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT],
        top_k=10,
        min_score=0.1,
        user=user_portal_admin(),
    )
    assert len(out) == 2
    assert out[0]["meta"] == {"x": 1}
    assert out[1]["meta"] == {}
    call_stmt = session.execute.await_args.args[0]
    sql_text = getattr(call_stmt, "text", str(call_stmt))
    assert "<=>" in sql_text
    assert "CAST(:vec AS vector)" in sql_text
    assert ":vec::vector" not in sql_text


@pytest.mark.asyncio
async def test_semantic_search_chat_message_appends_member_filter() -> None:
    session = _session_with_fetchall([])
    await search_svc.semantic_search(
        session,
        [0.1],
        [PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE],
        top_k=3,
        min_score=0.2,
        user=user_portal_regular(),
    )
    sql_text = getattr(session.execute.await_args.args[0], "text", "")
    assert "portal_chat_member" in sql_text


@pytest.mark.asyncio
async def test_semantic_search_task_filter_for_non_manager_user() -> None:
    session = _session_with_fetchall([])
    await search_svc.semantic_search(
        session,
        [0.2],
        [PORTAL_SEARCH_ENTITY_TYPE_TASK],
        top_k=4,
        min_score=0.0,
        user=user_portal_no_idp_groups(),
    )
    sql_text = getattr(session.execute.await_args.args[0], "text", "")
    assert "portal_task" in sql_text
    assert "portal_task_assignee" in sql_text


@pytest.mark.asyncio
async def test_semantic_search_task_no_visibility_sql_for_manager_user() -> None:
    """user_portal_regular — менеджер (gid outstaff); видимость задач без SQL-фильтра."""
    session = _session_with_fetchall([])
    await search_svc.semantic_search(
        session,
        [0.2],
        [PORTAL_SEARCH_ENTITY_TYPE_TASK],
        top_k=4,
        min_score=0.0,
        user=user_portal_regular(),
    )
    sql_text = getattr(session.execute.await_args.args[0], "text", "")
    assert "portal_task" not in sql_text


@pytest.mark.asyncio
async def test_semantic_search_agreement_scope_non_admin() -> None:
    session = _session_with_fetchall([])
    await search_svc.semantic_search(
        session,
        [0.3],
        [PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT],
        top_k=2,
        min_score=0.0,
        user=user_portal_no_idp_groups(),
    )
    sql_text = getattr(session.execute.await_args.args[0], "text", "")
    assert "portal_agreement" in sql_text
    assert "portal_task_assignee" in sql_text


@pytest.mark.asyncio
async def test_semantic_search_agreement_admin_skips_extra_rbac_clause() -> None:
    session = _session_with_fetchall([])
    await search_svc.semantic_search(
        session,
        [0.3],
        [PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT],
        top_k=2,
        min_score=0.0,
        user=user_portal_admin(),
    )
    sql_text = getattr(session.execute.await_args.args[0], "text", "")
    assert "portal_agreement" not in sql_text


@pytest.mark.asyncio
async def test_semantic_search_specialist_uses_any_not_in_for_asyncpg() -> None:
    """Регрессия: NOT IN :specialist_et с tuple → PostgresSyntaxError у asyncpg."""
    session = _session_with_fetchall([])
    await search_svc.semantic_search(
        session,
        [0.4],
        [PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST, PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE],
        top_k=5,
        min_score=0.0,
        user=user_portal_no_idp_groups(),
    )
    sql_text = getattr(session.execute.await_args.args[0], "text", "")
    assert "NOT (pe.entity_type = ANY(:specialist_et))" in sql_text
    assert "NOT IN :specialist_et" not in sql_text
    params = session.execute.await_args.args[1]
    assert isinstance(params["specialist_et"], list)


@pytest.mark.asyncio
async def test_semantic_search_specialist_manager_scope_sql() -> None:
    session = _session_with_fetchall([])
    await search_svc.semantic_search(
        session,
        [0.4],
        [PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST],
        top_k=5,
        min_score=0.0,
        user=user_portal_manager(),
    )
    sql_text = getattr(session.execute.await_args.args[0], "text", "")
    assert "portal_manager_specialist" in sql_text
    assert "ms.manager_sub" in sql_text


@pytest.mark.asyncio
async def test_semantic_search_specialist_no_scope_sql_for_admin() -> None:
    session = _session_with_fetchall([])
    await search_svc.semantic_search(
        session,
        [0.4],
        [PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST],
        top_k=5,
        min_score=0.0,
        user=user_portal_admin(),
    )
    sql_text = getattr(session.execute.await_args.args[0], "text", "")
    assert "specialist_et" not in sql_text
    assert "portal_manager_specialist" not in sql_text


@pytest.mark.asyncio
async def test_semantic_search_agreement_timesheet_only_uses_developer_docs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dev_id = uuid.uuid4()

    async def _fake_dev_ids(_session: object) -> list[uuid.UUID]:
        return [dev_id]

    monkeypatch.setattr(search_svc, "developer_docs_readable_ids", _fake_dev_ids)
    session = _session_with_fetchall([])
    await search_svc.semantic_search(
        session,
        [0.3],
        [PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT],
        top_k=2,
        min_score=0.0,
        user=user_portal_developer(),
    )
    params = session.execute.await_args.args[1]
    assert params["agr_dev_ids"] == [str(dev_id)]


@pytest.mark.asyncio
async def test_semantic_search_learning_rbac_for_non_admin() -> None:
    session = _session_with_fetchall([])
    await search_svc.semantic_search(
        session,
        [0.1],
        [PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL],
        top_k=3,
        min_score=0.0,
        user=user_portal_no_idp_groups(),
    )
    sql_text = getattr(session.execute.await_args.args[0], "text", "")
    assert "portal_learning_material" in sql_text
    params = session.execute.await_args.args[1]
    assert params["lm_active"] == LearningMaterialStatus.ACTIVE


@pytest.mark.asyncio
async def test_semantic_search_learning_no_filter_for_admin() -> None:
    session = _session_with_fetchall([])
    await search_svc.semantic_search(
        session,
        [0.1],
        [PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL],
        top_k=3,
        min_score=0.0,
        user=user_portal_admin(),
    )
    sql_text = getattr(session.execute.await_args.args[0], "text", "")
    assert "portal_learning_material" not in sql_text
