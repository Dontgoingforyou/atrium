"""Тесты webhook Jira (`app.integrations.jira.routes`)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from app.core.exceptions import ValidationError
from app.integrations.jira.routes import _extract_issue_key
from httpx import AsyncClient
from tests.conftest import make_oidc_settings


@pytest.fixture
def patch_jira_webhook_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    s = make_oidc_settings(
        jira_base_url="https://jira.example",
        jira_personal_access_token="test-pat",
        jira_webhook_secret="wh-secret",
    )
    monkeypatch.setattr("app.integrations.jira.routes.get_settings", lambda: s)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"issue": {"key": "BASE-1"}}, "BASE-1"),
        ({"issue_key": "BASE-2"}, "BASE-2"),
        ({"key": "BASE-3"}, "BASE-3"),
        ({}, None),
        ({"issue": "not-a-dict"}, None),
    ],
)
def test_extract_issue_key(payload: dict[str, Any], expected: str | None) -> None:
    assert _extract_issue_key(payload) == expected


@pytest.mark.anyio
async def test_jira_webhook_rejects_when_secret_not_configured(
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = make_oidc_settings(jira_webhook_secret="")
    monkeypatch.setattr("app.integrations.jira.routes.get_settings", lambda: s)
    res = await client_sqlite_only.post(
        "/api/v1/integrations/jira/webhook",
        json={"issue": {"key": "BASE-1"}},
        headers={"X-Jira-Webhook-Secret": ""},
    )
    assert res.status_code == 403
    assert res.json()["code"] == "forbidden"


@pytest.mark.anyio
async def test_jira_webhook_missing_secret_header_403(
    client_sqlite_only: AsyncClient,
    patch_jira_webhook_settings: None,
) -> None:
    res = await client_sqlite_only.post(
        "/api/v1/integrations/jira/webhook",
        json={"issue": {"key": "BASE-1"}},
    )
    assert res.status_code == 403
    assert res.json()["code"] == "forbidden"


@pytest.mark.anyio
async def test_jira_webhook_wrong_secret_same_length_403(
    client_sqlite_only: AsyncClient,
    patch_jira_webhook_settings: None,
) -> None:
    res = await client_sqlite_only.post(
        "/api/v1/integrations/jira/webhook",
        json={"key": "BASE-1"},
        headers={"X-Jira-Webhook-Secret": "wh-secreX"},
    )
    assert res.status_code == 403
    assert res.json()["code"] == "forbidden"


@pytest.mark.anyio
async def test_jira_webhook_invalid_json_returns_400(
    client_sqlite_only: AsyncClient,
    patch_jira_webhook_settings: None,
) -> None:
    res = await client_sqlite_only.post(
        "/api/v1/integrations/jira/webhook",
        content=b"not-json",
        headers={
            "Content-Type": "application/json",
            "X-Jira-Webhook-Secret": "wh-secret",
        },
    )
    assert res.status_code == 400
    assert res.json()["code"] == "bad_request"


@pytest.mark.anyio
async def test_jira_webhook_non_dict_payload_returns_400(
    client_sqlite_only: AsyncClient,
    patch_jira_webhook_settings: None,
) -> None:
    res = await client_sqlite_only.post(
        "/api/v1/integrations/jira/webhook",
        json=["not", "a", "dict"],
        headers={"X-Jira-Webhook-Secret": "wh-secret"},
    )
    assert res.status_code == 400
    assert res.json()["code"] == "bad_request"


@pytest.mark.anyio
async def test_jira_webhook_204_without_issue_key(
    client_sqlite_only: AsyncClient,
    patch_jira_webhook_settings: None,
) -> None:
    res = await client_sqlite_only.post(
        "/api/v1/integrations/jira/webhook",
        json={"comment": "only metadata"},
        headers={"X-Jira-Webhook-Secret": "wh-secret"},
    )
    assert res.status_code == 204


@pytest.mark.anyio
async def test_jira_webhook_issue_key_from_top_level_field(
    client_sqlite_only: AsyncClient,
    patch_jira_webhook_settings: None,
) -> None:
    with patch("app.integrations.jira.routes.jira_svc.apply_jira_webhook", new_callable=AsyncMock) as wh:
        wh.return_value = False
        res = await client_sqlite_only.post(
            "/api/v1/integrations/jira/webhook",
            json={"issue_key": "BASE-7"},
            headers={"X-Jira-Webhook-Secret": "wh-secret"},
        )
    assert res.status_code == 204
    wh.assert_awaited_once()
    assert wh.await_args.args[2] == "BASE-7"


@pytest.mark.anyio
async def test_jira_webhook_200_when_updated(
    client_sqlite_only: AsyncClient,
    patch_jira_webhook_settings: None,
) -> None:
    with patch("app.integrations.jira.routes.jira_svc.apply_jira_webhook", new_callable=AsyncMock) as wh:
        wh.return_value = True
        res = await client_sqlite_only.post(
            "/api/v1/integrations/jira/webhook",
            json={"key": "BASE-9"},
            headers={"X-Jira-Webhook-Secret": "wh-secret"},
        )
    assert res.status_code == 200
    wh.assert_awaited_once()
    assert wh.await_args.args[2] == "BASE-9"


@pytest.mark.anyio
async def test_jira_webhook_rejects_secret_of_different_length(
    client_sqlite_only: AsyncClient,
    patch_jira_webhook_settings: None,
) -> None:
    res = await client_sqlite_only.post(
        "/api/v1/integrations/jira/webhook",
        json={"key": "BASE-1"},
        headers={"X-Jira-Webhook-Secret": "x"},
    )
    assert res.status_code == 403
    assert res.json()["code"] == "forbidden"


@pytest.mark.anyio
async def test_jira_webhook_unknown_issue_key_returns_204(
    client_sqlite_only: AsyncClient,
    patch_jira_webhook_settings: None,
) -> None:
    with patch("app.integrations.jira.routes.jira_svc.apply_jira_webhook", new_callable=AsyncMock) as wh:
        wh.side_effect = ValidationError("Некорректный ключ задачи Jira (ожидается BASE-123)")
        res = await client_sqlite_only.post(
            "/api/v1/integrations/jira/webhook",
            json={"key": "AUTASKS-1"},
            headers={"X-Jira-Webhook-Secret": "wh-secret"},
        )
    assert res.status_code == 204


@pytest.mark.anyio
async def test_jira_webhook_propagates_apply_error(
    client_sqlite_only: AsyncClient,
    patch_jira_webhook_settings: None,
) -> None:
    with patch("app.integrations.jira.routes.jira_svc.apply_jira_webhook", new_callable=AsyncMock) as wh:
        wh.side_effect = RuntimeError("jira down")
        with pytest.raises(RuntimeError, match="jira down"):
            await client_sqlite_only.post(
                "/api/v1/integrations/jira/webhook",
                json={"key": "BASE-8"},
                headers={"X-Jira-Webhook-Secret": "wh-secret"},
            )
