"""Тесты интеграции Jira для специалистов."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.integrations.jira.fields import CF_CITY, CF_CV, CF_DIRECTION, CF_TELEGRAM
from app.integrations.jira.jql import escape_jql_text
from app.integrations.jira.normalize import normalize_issue_fields
from app.portal_specialists.services.jira_import import JIRA_SYNCED_STATUS_ID_KEY
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_oidc_settings
from tests.portal_specialists.conftest import assert_api_error

# ---------------------------------------------------------------------------
# Unit: jql + normalize
# ---------------------------------------------------------------------------


def test_escape_jql_text_quotes_and_backslash() -> None:
    assert escape_jql_text('Иванов "test"') == r"Иванов \"test\""
    assert escape_jql_text(r"path\file") == r"path\\file"


def test_escape_jql_text_empty() -> None:
    assert escape_jql_text("   ") == ""


def test_escape_jql_text_strips_control_chars() -> None:
    assert escape_jql_text("ab\nOR project = X") == "abOR project = X"


def test_normalize_issue_fields_groups_and_empty() -> None:
    issue = {
        "key": "BASE-4",
        "fields": {
            "summary": "Иванов Иван",
            CF_CITY: "Москва",
            CF_TELEGRAM: "@ivan",
            CF_DIRECTION: {"value": "Python"},
            CF_CV: "https://example.com/cv.pdf",
            "status": {"name": "Новичок", "id": "10001"},
        },
        "names": {CF_CITY: "Город", "summary": "Тема"},
    }
    data = normalize_issue_fields(issue)
    assert data["issue_key"] == "BASE-4"
    all_ids = {f["id"] for g in data["groups"] for f in g["fields"]}
    assert CF_CITY not in all_ids
    assert CF_TELEGRAM not in all_ids
    assert CF_DIRECTION not in all_ids
    assert CF_CV not in all_ids
    assert "summary" in all_ids
    summary_field = next(f for g in data["groups"] for f in g["fields"] if f["id"] == "summary")
    assert summary_field["label"] == "ФИО"
    assert summary_field["value"] == "Иванов Иван"
    assert "status" in all_ids
    status_field = next(f for g in data["groups"] for f in g["fields"] if f["id"] == "status")
    assert status_field["value"] == "Новичок"


def test_extract_jira_field_text_option_and_string() -> None:
    from app.integrations.jira.normalize import extract_jira_field_text

    assert extract_jira_field_text(CF_DIRECTION, {"value": "Python"}) == "Python"
    assert extract_jira_field_text(CF_CITY, "Донецк") == "Донецк"


def test_filter_jira_groups_relabels_summary_from_snapshot() -> None:
    from app.integrations.jira.normalize import filter_jira_groups_for_display

    groups = [
        {
            "key": "profile",
            "label": "Профиль",
            "fields": [{"id": "summary", "label": "Тема", "value": "Иванов Иван", "kind": "text"}],
        },
    ]
    out = filter_jira_groups_for_display(groups)
    summary = out[0]["fields"][0]
    assert summary["label"] == "ФИО"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sample_issue(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "key": "BASE-4",
        "fields": {
            "project": {"key": "BASE"},
            "summary": "Иванов Иван",
            "status": {"id": "10001", "name": "Новичок"},
            CF_CITY: "Москва",
            CF_TELEGRAM: "v1sh3nk4",
            CF_DIRECTION: {"value": "Python"},
            CF_CV: "https://example.com/cv.pdf",
        },
        "names": {},
    }
    if overrides:
        if "fields" in overrides:
            base["fields"].update(overrides.pop("fields"))
        base.update(overrides)
    return base


@pytest.fixture
def patch_jira_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    s = make_oidc_settings(
        jira_base_url="https://jira.example",
        jira_personal_access_token="test-pat",
        jira_project_key="BASE",
        jira_board_id=68,
        jira_webhook_secret="wh-secret",
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)
    monkeypatch.setattr("app.portal_specialists.services.jira_import.get_settings", lambda: s)
    monkeypatch.setattr("app.portal_specialists.services.jira_board_sync.get_settings", lambda: s)
    monkeypatch.setattr("app.portal_specialists.routes.jira.get_settings", lambda: s)
    monkeypatch.setattr("app.integrations.jira.routes.get_settings", lambda: s)


@pytest.fixture
def mock_jira_client() -> Any:
    with patch("app.portal_specialists.services.jira_import.JiraClient") as cls:
        instance = cls.return_value
        instance.search_issues = AsyncMock(
            return_value={
                "issues": [
                    {
                        "key": "BASE-4",
                        "fields": {
                            "summary": "Иванов Иван",
                            "status": {"name": "Новичок"},
                        },
                    },
                ],
            },
        )
        instance.get_issue = AsyncMock(return_value=_sample_issue())
        yield instance


# ---------------------------------------------------------------------------
# API: RBAC + link/sync
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_jira_search_forbidden_for_student(
    client_specialist_user: AsyncClient,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    res = await client_specialist_user.get("/api/v1/portal/specialists/jira/search?q=Иван")
    assert_api_error(res, 403, "forbidden")


@pytest.mark.anyio
async def test_jira_search_query_too_short_422(
    client_manager: AsyncClient,
    patch_jira_settings: None,
) -> None:
    res = await client_manager.get("/api/v1/portal/specialists/jira/search?q=a")
    assert res.status_code == 422
    assert "detail" in res.json()


@pytest.mark.anyio
async def test_jira_search_disabled_service_unavailable(
    client_manager: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = make_oidc_settings(jira_base_url="", jira_personal_access_token="")
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)
    monkeypatch.setattr("app.portal_specialists.services.jira_import.get_settings", lambda: s)
    res = await client_manager.get("/api/v1/portal/specialists/jira/search?q=ab")
    assert_api_error(res, 503, "service_unavailable")


@pytest.mark.anyio
async def test_jira_search_success(
    client_manager: AsyncClient,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    res = await client_manager.get("/api/v1/portal/specialists/jira/search?q=Иван")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["issue_key"] == "BASE-4"


@pytest.mark.anyio
async def test_jira_link_idor_manager_b(
    client_manager_b: AsyncClient,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    res = await client_manager_b.post(
        "/api/v1/portal/specialists/specialist-sub/jira/link",
        json={"issue_key": "BASE-4"},
    )
    assert_api_error(res, 403, "forbidden")


@pytest.mark.anyio
async def test_jira_sync_idor_manager_b(
    client_manager_b: AsyncClient,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    res = await client_manager_b.post("/api/v1/portal/specialists/specialist-sub/jira/sync")
    assert_api_error(res, 403, "forbidden")


@pytest.mark.anyio
async def test_jira_unlink_idor_manager_b(
    client_manager_b: AsyncClient,
    patch_jira_settings: None,
) -> None:
    res = await client_manager_b.delete("/api/v1/portal/specialists/specialist-sub/jira/link")
    assert_api_error(res, 403, "forbidden")


@pytest.mark.anyio
async def test_jira_link_invalid_issue_key(
    client_manager: AsyncClient,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    res = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/jira/link",
        json={"issue_key": "INVALID"},
    )
    assert res.status_code == 422


@pytest.mark.anyio
async def test_jira_link_success_updates_profile_and_column(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    res = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/jira/link",
        json={"issue_key": "BASE-4"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["jira_issue_key"] == "BASE-4"
    assert body["jira_browse_url"] == "https://jira.example/browse/BASE-4"
    assert body["groups"]

    profile = await session_with_board.get(PortalSpecialistProfile, "specialist-sub")
    assert profile is not None
    assert profile.jira_issue_key == "BASE-4"
    assert profile.location == "Москва"
    assert profile.telegram is not None
    assert profile.jira_synced_at is not None

    assert profile.direction == "Python"

    entry = await _board_entry(session_with_board)
    assert entry.column_key == "new"
    profile = await session_with_board.get(PortalSpecialistProfile, "specialist-sub")
    assert profile is not None
    assert (profile.jira_fields or {}).get(JIRA_SYNCED_STATUS_ID_KEY) == "10001"


async def _board_entry(session: AsyncSession) -> PortalManagerSpecialist:
    session.expire_all()
    return (
        await session.execute(
            select(PortalManagerSpecialist).where(
                PortalManagerSpecialist.specialist_sub == "specialist-sub",
            ),
        )
    ).scalar_one()


@pytest.mark.anyio
async def test_jira_sync_same_status_keeps_manual_column(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    """Повторный sync с тем же статусом не сбрасывает колонку, куда карточку поставил менеджер."""
    linked = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/jira/link",
        json={"issue_key": "BASE-4"},
    )
    assert linked.status_code == 200

    moved = await client_manager.patch(
        "/api/v1/portal/specialists/board/specialist-sub",
        json={"expected_version": 1, "column_key": "hired"},
    )
    assert moved.status_code == 200

    synced = await client_manager.post("/api/v1/portal/specialists/specialist-sub/jira/sync")
    assert synced.status_code == 200

    entry = await _board_entry(session_with_board)
    assert entry.column_key == "hired"
    profile = await session_with_board.get(PortalSpecialistProfile, "specialist-sub")
    assert profile is not None
    assert (profile.jira_fields or {}).get(JIRA_SYNCED_STATUS_ID_KEY) == "10001"
    assert mock_jira_client.get_issue.await_count >= 1


@pytest.mark.anyio
async def test_jira_sync_changed_status_moves_column(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    """Смена статуса задачи переносит карточку в колонку по названию статуса."""
    linked = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/jira/link",
        json={"issue_key": "BASE-4"},
    )
    assert linked.status_code == 200

    moved = await client_manager.patch(
        "/api/v1/portal/specialists/board/specialist-sub",
        json={"expected_version": 1, "column_key": "cv_sent"},
    )
    assert moved.status_code == 200

    hired = (
        await session_with_board.execute(
            select(PortalSpecialistColumn).where(PortalSpecialistColumn.key == "hired"),
        )
    ).scalar_one()
    hired.jira_status_id = "10099"
    await session_with_board.commit()

    mock_jira_client.get_issue.return_value = _sample_issue(
        fields={"status": {"id": "10099", "name": "Принят"}},
    )
    synced = await client_manager.post("/api/v1/portal/specialists/specialist-sub/jira/sync")
    assert synced.status_code == 200

    entry = await _board_entry(session_with_board)
    assert entry.column_key == "hired"
    profile = await session_with_board.get(PortalSpecialistProfile, "specialist-sub")
    assert profile is not None
    assert (profile.jira_fields or {}).get(JIRA_SYNCED_STATUS_ID_KEY) == "10099"


@pytest.mark.anyio
async def test_jira_sync_without_stored_status_id_does_not_move(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    """Уже привязанный профиль без сохранённого id: sync запоминает статус и не двигает колонку."""
    session_with_board.add(
        PortalSpecialistProfile(
            specialist_sub="specialist-sub",
            jira_issue_key="BASE-4",
            jira_fields={},
        ),
    )
    await session_with_board.commit()
    entry = await _board_entry(session_with_board)
    entry.column_key = "hired"
    await session_with_board.commit()

    synced = await client_manager.post("/api/v1/portal/specialists/specialist-sub/jira/sync")
    assert synced.status_code == 200

    entry = await _board_entry(session_with_board)
    assert entry.column_key == "hired"
    profile = await session_with_board.get(PortalSpecialistProfile, "specialist-sub")
    assert profile is not None
    assert (profile.jira_fields or {}).get(JIRA_SYNCED_STATUS_ID_KEY) == "10001"
    assert mock_jira_client.get_issue.await_count == 1


@pytest.mark.anyio
async def test_jira_link_duplicate_issue_key_conflict(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    session_with_board.add(
        PortalUserProfile(
            sub="other-sub",
            email="other@example.com",
            full_name="Other Specialist",
            username="other",
        ),
    )
    await session_with_board.flush()
    session_with_board.add(
        PortalSpecialistProfile(
            specialist_sub="other-sub",
            jira_issue_key="BASE-4",
        ),
    )
    await session_with_board.commit()

    res = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/jira/link",
        json={"issue_key": "BASE-4"},
    )
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# Webhook (Phase 2)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_jira_webhook_204_unlinked_issue(
    client_sqlite_only: AsyncClient,
    patch_jira_settings: None,
) -> None:
    res = await client_sqlite_only.post(
        "/api/v1/integrations/jira/webhook",
        json={"issue": {"key": "BASE-999"}},
        headers={"X-Jira-Webhook-Secret": "wh-secret"},
    )
    assert res.status_code == 204


@pytest.mark.anyio
async def test_jira_webhook_debounce_skips_second_call(
    sqlite_session: AsyncSession,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    from app.portal_specialists.services import jira_import as jira_svc

    sqlite_session.add(
        PortalSpecialistProfile(
            specialist_sub="user-sub",
            jira_issue_key="BASE-4",
        ),
    )
    await sqlite_session.commit()

    redis_mock = AsyncMock()
    redis_mock.set = AsyncMock(side_effect=[True, False])

    with patch("app.portal_specialists.services.jira_import.get_redis_client", return_value=redis_mock):
        first = await jira_svc.apply_jira_webhook(sqlite_session, AsyncMock(), "BASE-4")
        second = await jira_svc.apply_jira_webhook(sqlite_session, AsyncMock(), "BASE-4")

    assert first is True
    assert second is False
    assert mock_jira_client.get_issue.await_count == 1


@pytest.mark.anyio
async def test_jira_get_state_does_not_insert_and_hides_non_student(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
    patch_jira_settings: None,
) -> None:
    res = await client_manager.get("/api/v1/portal/specialists/specialist-sub/jira")
    assert res.status_code == 200
    assert res.json()["jira_issue_key"] is None
    assert await session_with_board.get(PortalSpecialistProfile, "specialist-sub") is None

    hidden = await client_manager.get("/api/v1/portal/specialists/manager-b-sub/jira")
    assert hidden.status_code == 404


@pytest.mark.anyio
async def test_jira_sync_and_unlink(
    client_manager: AsyncClient,
    session_with_board: AsyncSession,
    patch_jira_settings: None,
    mock_jira_client: Any,
) -> None:
    missing = await client_manager.post("/api/v1/portal/specialists/specialist-sub/jira/sync")
    assert missing.status_code == 404

    linked = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/jira/link",
        json={"issue_key": "BASE-4"},
    )
    assert linked.status_code == 200

    synced = await client_manager.post("/api/v1/portal/specialists/specialist-sub/jira/sync")
    assert synced.status_code == 200
    assert synced.json()["jira_issue_key"] == "BASE-4"

    manual = await client_manager.post(
        "/api/v1/portal/specialists/specialist-sub/links",
        json={"title": "Ручная", "url": "https://example.com/manual"},
    )
    assert manual.status_code == 201

    before = await client_manager.get("/api/v1/portal/specialists/specialist-sub/links")
    titles = {item["title"] for item in before.json()}
    assert "CV" in titles
    assert "Ручная" in titles

    unlinked = await client_manager.delete("/api/v1/portal/specialists/specialist-sub/jira/link")
    assert unlinked.status_code == 204
    profile = await session_with_board.get(PortalSpecialistProfile, "specialist-sub")
    assert profile is not None
    assert profile.jira_issue_key is None

    after = await client_manager.get("/api/v1/portal/specialists/specialist-sub/links")
    leftover = {item["title"] for item in after.json()}
    assert leftover == {"Ручная"}


@pytest.mark.anyio
async def test_jira_sync_columns_forbidden_for_manager(
    client_manager: AsyncClient,
    patch_jira_settings: None,
) -> None:
    denied = await client_manager.post("/api/v1/portal/specialists/columns/sync-from-jira")
    assert denied.status_code == 403


@pytest.mark.anyio
async def test_jira_sync_columns_admin(
    client_admin_board: AsyncClient,
    patch_jira_settings: None,
) -> None:
    with patch("app.portal_specialists.services.jira_board_sync.JiraClient") as cls:
        cls.return_value.get_board_configuration = AsyncMock(
            return_value={
                "columnConfig": {
                    "columns": [
                        {"name": "Собеседование", "statuses": [{"id": "20002"}]},
                    ],
                },
            },
        )
        ok = await client_admin_board.post("/api/v1/portal/specialists/columns/sync-from-jira")
    assert ok.status_code == 200
    assert ok.json()["synced"] >= 1
