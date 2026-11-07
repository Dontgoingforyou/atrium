"""Модульные тесты HTTP-клиента Jira (`app.integrations.jira.client`)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.core.config import Settings
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.integrations.jira.client import JiraClient
from tests.conftest import make_oidc_settings


def _jira_settings(**kwargs: Any) -> Settings:
    data: dict[str, Any] = {
        "jira_base_url": "https://jira.example/",
        "jira_personal_access_token": "test-pat",
        "jira_board_id": 68,
    }
    data.update(kwargs)
    return make_oidc_settings(**data)


def _mock_response(*, status_code: int = 200, json_body: Any = None, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = json_body if json_body is not None else {"ok": True}
    return response


@pytest.fixture
def http() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def client(http: AsyncMock) -> JiraClient:
    return JiraClient(_jira_settings(), http)


@pytest.mark.anyio
async def test_request_raises_when_jira_disabled(http: AsyncMock) -> None:
    disabled = JiraClient(
        _jira_settings(jira_base_url="", jira_personal_access_token=""),
        http,
    )
    with pytest.raises(ServiceUnavailableError, match="не настроена"):
        await disabled.search_issues('summary ~ "test"')


@pytest.mark.anyio
async def test_request_network_error_maps_to_service_unavailable(
    client: JiraClient,
    http: AsyncMock,
) -> None:
    http.request.side_effect = httpx.ConnectError("connection refused")
    with pytest.raises(ServiceUnavailableError, match="временно недоступна"):
        await client.get_issue("BASE-1")
    http.request.assert_awaited_once()


@pytest.mark.anyio
async def test_request_404_raises_not_found(
    client: JiraClient,
    http: AsyncMock,
) -> None:
    http.request.return_value = _mock_response(status_code=404)
    with pytest.raises(NotFoundError, match="не найдена"):
        await client.get_issue("BASE-404")


@pytest.mark.anyio
async def test_request_json_not_object_raises_unavailable(
    client: JiraClient,
    http: AsyncMock,
) -> None:
    http.request.return_value = _mock_response(json_body=[{"key": "BASE-1"}])
    with pytest.raises(ServiceUnavailableError, match="ошибку"):
        await client.get_issue("BASE-1")


@pytest.mark.parametrize("status_code", [400, 401, 500])
@pytest.mark.anyio
async def test_request_http_error_maps_to_service_unavailable(
    client: JiraClient,
    http: AsyncMock,
    status_code: int,
) -> None:
    http.request.return_value = _mock_response(status_code=status_code, text="Jira error body")
    with pytest.raises(ServiceUnavailableError, match="вернула ошибку"):
        await client.get_issue("BASE-1")


@pytest.mark.anyio
async def test_request_invalid_json_maps_to_service_unavailable(
    client: JiraClient,
    http: AsyncMock,
) -> None:
    response = _mock_response()
    response.json.side_effect = ValueError("html")
    http.request.return_value = response
    with pytest.raises(ServiceUnavailableError, match="ошибку"):
        await client.get_issue("BASE-1")


@pytest.mark.anyio
async def test_request_success_returns_json(client: JiraClient, http: AsyncMock) -> None:
    payload = {"issues": [{"key": "BASE-1"}]}
    http.request.return_value = _mock_response(json_body=payload)
    result = await client.search_issues('project = "BASE"')
    assert result == payload


@pytest.mark.anyio
async def test_search_issues_builds_params_without_fields(client: JiraClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(json_body={"issues": []})
    await client.search_issues('summary ~ "Иван"', max_results=10)
    http.request.assert_awaited_once_with(
        "GET",
        "https://jira.example/rest/api/2/search",
        headers={"Authorization": "Bearer test-pat"},
        params={"jql": 'summary ~ "Иван"', "maxResults": 10},
    )


@pytest.mark.anyio
async def test_search_issues_includes_fields_param(client: JiraClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(json_body={"issues": []})
    await client.search_issues("project = BASE", fields=["summary", "status"], max_results=5)
    http.request.assert_awaited_once_with(
        "GET",
        "https://jira.example/rest/api/2/search",
        headers={"Authorization": "Bearer test-pat"},
        params={
            "jql": "project = BASE",
            "maxResults": 5,
            "fields": "summary,status",
        },
    )


@pytest.mark.anyio
async def test_get_issue_passes_expand(client: JiraClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(json_body={"key": "BASE-4"})
    result = await client.get_issue("BASE-4", expand="names")
    assert result == {"key": "BASE-4"}
    http.request.assert_awaited_once_with(
        "GET",
        "https://jira.example/rest/api/2/issue/BASE-4",
        headers={"Authorization": "Bearer test-pat"},
        params={"expand": "names"},
    )


@pytest.mark.anyio
async def test_get_board_configuration_uses_settings_board_id(
    client: JiraClient,
    http: AsyncMock,
) -> None:
    http.request.return_value = _mock_response(json_body={"columnConfig": {}})
    await client.get_board_configuration()
    http.request.assert_awaited_once_with(
        "GET",
        "https://jira.example/rest/agile/1.0/board/68/configuration",
        headers={"Authorization": "Bearer test-pat"},
    )


@pytest.mark.anyio
async def test_get_board_configuration_explicit_board_id(
    client: JiraClient,
    http: AsyncMock,
) -> None:
    http.request.return_value = _mock_response(json_body={"columnConfig": {}})
    await client.get_board_configuration(board_id=99)
    http.request.assert_awaited_once_with(
        "GET",
        "https://jira.example/rest/agile/1.0/board/99/configuration",
        headers={"Authorization": "Bearer test-pat"},
    )
