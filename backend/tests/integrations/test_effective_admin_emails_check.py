"""HTTP-ветки EffectiveAdminEmailsClient."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.integrations.effective_admin.emails_check import EMAILS_CHECK_MAX, EffectiveAdminEmailsClient
from tests.conftest import make_oidc_settings


def _settings(**kwargs: Any) -> Any:
    data: dict[str, Any] = {
        "effective_admin_base_url": "https://ea.example",
        "effective_admin_service_token": "svc-token",
    }
    data.update(kwargs)
    return make_oidc_settings(**data)


def _json_response(*, status_code: int = 200, payload: dict[str, Any] | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json = MagicMock(return_value=payload if payload is not None else {})
    return response


@pytest.fixture
def http() -> MagicMock:
    mock = MagicMock(spec=httpx.AsyncClient)
    mock.post = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_check_emails_disabled_without_token(http: MagicMock) -> None:
    client = EffectiveAdminEmailsClient(_settings(effective_admin_service_token=""), http)
    assert await client.check_emails(["a@x.test"]) is None
    http.post.assert_not_called()


@pytest.mark.asyncio
async def test_check_emails_splits_found_and_not_found(http: MagicMock) -> None:
    http.post = AsyncMock(
        return_value=_json_response(
            payload={
                "found": ["User.Two@example.com"],
                "not_found": [" nobody@example.com "],
            }
        )
    )
    client = EffectiveAdminEmailsClient(_settings(), http)
    result = await client.check_emails(["  USER.TWO@example.com ", "nobody@example.com"])
    assert result is not None
    assert result.found == frozenset({"user.two@example.com"})
    assert result.not_found == frozenset({"nobody@example.com"})
    http.post.assert_awaited_once()
    kwargs = http.post.await_args
    assert kwargs.args[0] == "https://ea.example/api/v1/emails/check"
    assert kwargs.kwargs["headers"]["Authorization"] == "Bearer svc-token"
    assert kwargs.kwargs["json"]["emails"] == [
        "user.two@example.com",
        "nobody@example.com",
    ]


@pytest.mark.asyncio
async def test_check_emails_401_returns_none(http: MagicMock) -> None:
    http.post = AsyncMock(return_value=_json_response(status_code=401, payload={"detail": "no"}))
    client = EffectiveAdminEmailsClient(_settings(), http)
    assert await client.check_emails(["a@x.test"]) is None


@pytest.mark.asyncio
async def test_check_emails_network_error_returns_none(http: MagicMock) -> None:
    http.post = AsyncMock(side_effect=httpx.ConnectError("down"))
    client = EffectiveAdminEmailsClient(_settings(), http)
    assert await client.check_emails(["a@x.test"]) is None


@pytest.mark.asyncio
async def test_check_emails_batches_over_limit(http: MagicMock) -> None:
    http.post = AsyncMock(return_value=_json_response(payload={"found": [], "not_found": []}))
    client = EffectiveAdminEmailsClient(_settings(), http)
    emails = [f"u{i}@x.test" for i in range(EMAILS_CHECK_MAX + 1)]
    result = await client.check_emails(emails)
    assert result is not None
    assert http.post.await_count == 2
