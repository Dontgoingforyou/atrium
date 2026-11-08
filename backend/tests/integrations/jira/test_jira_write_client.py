"""Модульные тесты JiraWriteClient."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.integrations.jira.write_client import JiraWriteClient
from tests.conftest import make_oidc_settings


def _settings(**kwargs: Any) -> Any:
    data: dict[str, Any] = {
        "jira_base_url": "https://jira.example/",
        "jira_personal_access_token": "test-pat",
    }
    data.update(kwargs)
    return make_oidc_settings(**data)


def _mock_response(*, status_code: int = 200, json_body: Any = None, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = json_body if json_body is not None else {}
    return response


@pytest.fixture
def http() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(http: AsyncMock) -> JiraWriteClient:
    return JiraWriteClient(_settings(), http)


@pytest.mark.anyio
async def test_add_watcher_sends_json_encoded_username(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=204)
    await client.add_watcher("TASKS-1", 'user"name')
    http.request.assert_awaited_once()
    kwargs = http.request.await_args.kwargs
    assert kwargs["content"] == json.dumps('user"name')


@pytest.mark.anyio
async def test_add_watcher_http_error_does_not_raise(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=403)
    await client.add_watcher("TASKS-1", "bob")


@pytest.mark.anyio
async def test_find_user_by_email_requires_exact_match(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(
        json_body=[{"name": "other", "emailAddress": "other@ex.com"}],
    )
    assert await client.find_user_by_email("wanted@ex.com") is None


@pytest.mark.anyio
async def test_find_user_by_email_returns_match(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(
        json_body=[
            {"name": "other", "emailAddress": "other@ex.com"},
            {"name": "wanted", "emailAddress": "Wanted@ex.com"},
        ],
    )
    user = await client.find_user_by_email("wanted@ex.com")
    assert user is not None
    assert user["name"] == "wanted"


@pytest.mark.anyio
async def test_find_user_by_email_http_error_returns_none(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=500, json_body=[])
    assert await client.find_user_by_email("a@b.com") is None


@pytest.mark.anyio
async def test_find_user_by_email_non_list_json_returns_none(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(json_body={"users": []})
    assert await client.find_user_by_email("a@b.com") is None


@pytest.mark.anyio
async def test_create_issue_invalid_json_maps_to_unavailable(client: JiraWriteClient, http: AsyncMock) -> None:
    response = _mock_response(status_code=201)
    response.json.side_effect = ValueError("not json")
    http.request.return_value = response
    with pytest.raises(ServiceUnavailableError, match="ошибку"):
        await client.create_issue({"summary": "x"})


@pytest.mark.anyio
async def test_create_issue_http_400_raises_unavailable(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=400)
    with pytest.raises(ServiceUnavailableError, match="не приняла создание"):
        await client.create_issue({"summary": "x"})


@pytest.mark.anyio
async def test_update_issue_404_raises_not_found(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=404)
    with pytest.raises(NotFoundError, match="не найдена"):
        await client.update_issue("TASKS-1", {"summary": "x"})


@pytest.mark.anyio
async def test_update_issue_http_400_raises_unavailable(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=400)
    with pytest.raises(ServiceUnavailableError, match="не приняла обновление"):
        await client.update_issue("TASKS-1", {"summary": "x"})


@pytest.mark.anyio
async def test_get_transitions_missing_key_returns_empty(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(json_body={"expand": "transitions"})
    assert await client.get_transitions("TASKS-1") == []


@pytest.mark.anyio
async def test_transition_issue_http_400_raises_unavailable(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=400)
    with pytest.raises(ServiceUnavailableError, match="не приняла смену статуса"):
        await client.transition_issue("TASKS-1", "21")


@pytest.mark.anyio
async def test_add_comment_success_returns_body(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=201, json_body={"id": "100", "body": "hi"})
    assert await client.add_comment("TASKS-1", "hi") == {"id": "100", "body": "hi"}


@pytest.mark.anyio
async def test_add_comment_http_400_raises_unavailable(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=400)
    with pytest.raises(ServiceUnavailableError, match="не приняла комментарий"):
        await client.add_comment("TASKS-1", "hi")


@pytest.mark.anyio
async def test_add_attachment_returns_list(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=200, json_body=[{"filename": "a.bin"}])
    assert await client.add_attachment(
        "TASKS-1",
        filename="a.bin",
        content=b"x",
        content_type="application/octet-stream",
    ) == [{"filename": "a.bin"}]


@pytest.mark.anyio
async def test_add_attachment_http_400_raises_unavailable(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=400, json_body=[])
    with pytest.raises(ServiceUnavailableError, match="не приняла вложение"):
        await client.add_attachment(
            "TASKS-1",
            filename="a.bin",
            content=b"x",
            content_type="application/octet-stream",
        )


@pytest.mark.anyio
async def test_delete_issue_204_sends_delete(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=204)
    await client.delete_issue("TASKS-1")
    http.request.assert_awaited_once()
    args = http.request.await_args.args
    assert args[0] == "DELETE"
    assert args[1].endswith("/rest/api/2/issue/TASKS-1")
    assert "params" not in http.request.await_args.kwargs


@pytest.mark.anyio
async def test_delete_issue_404_is_success(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=404)
    await client.delete_issue("TASKS-1")
    assert http.request.await_args.args[0] == "DELETE"


@pytest.mark.anyio
async def test_delete_issue_403_raises_and_does_not_transition(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=403)
    with pytest.raises(ServiceUnavailableError, match="не приняла удаление"):
        await client.delete_issue("TASKS-1")
    http.request.assert_awaited_once()
    assert http.request.await_args.args[0] == "DELETE"


@pytest.mark.anyio
async def test_delete_issue_with_subtasks_sends_query(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=204)
    await client.delete_issue("TASKS-1", delete_subtasks=True)
    assert http.request.await_args.kwargs["params"] == {"deleteSubtasks": "true"}


@pytest.mark.anyio
async def test_add_attachment_non_list_json_raises_unavailable(client: JiraWriteClient, http: AsyncMock) -> None:
    http.request.return_value = _mock_response(status_code=200, json_body={"id": "1"})
    with pytest.raises(ServiceUnavailableError, match="ошибку"):
        await client.add_attachment(
            "TASKS-1",
            filename="a.bin",
            content=b"x",
            content_type="application/octet-stream",
        )
