"""Клиент Google Sheets: JWT, RBAC enabled, сетевые сбои (мок httpx)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError
from app.integrations.google_sheets.client import GoogleSheetsClient
from app.integrations.google_sheets.jwt_sa import build_service_account_jwt, parse_service_account_json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _sa_json() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return json.dumps({"client_email": "bench@example.iam.gserviceaccount.com", "private_key": pem})


def _settings(**kwargs: object) -> Settings:
    data: dict[str, object] = {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "google_sheets_sync_enabled": True,
        "google_sheets_spreadsheet_id": "sheet-id-1",
        "google_sheets_service_account_json": _sa_json(),
    }
    data.update(kwargs)
    return Settings(**data)  # type: ignore[arg-type]


def test_parse_service_account_rejects_invalid_json() -> None:
    with pytest.raises(ValueError, match="невалидный JSON"):
        parse_service_account_json("{not-json")


def test_build_jwt_has_three_segments() -> None:
    account = parse_service_account_json(_sa_json())
    token = build_service_account_jwt(account)
    assert token.count(".") == 2
    assert account["client_email"] not in token.split(".")[2]


@pytest.mark.asyncio
async def test_client_disabled_raises() -> None:
    settings = _settings(google_sheets_sync_enabled=False, google_sheets_service_account_json="")
    client = GoogleSheetsClient(settings, AsyncMock())
    with pytest.raises(ServiceUnavailableError):
        await client.fetch_dashboard_sheets()


@pytest.mark.asyncio
async def test_client_network_error_on_token() -> None:
    http = AsyncMock()
    http.post = AsyncMock(side_effect=httpx.ConnectError("boom"))
    client = GoogleSheetsClient(_settings(), http)
    with pytest.raises(ServiceUnavailableError, match="недоступна"):
        await client.list_sheet_titles()


@pytest.mark.asyncio
async def test_fetch_dashboard_sheets_batch_get() -> None:
    http = MagicMock()
    token_resp = MagicMock()
    token_resp.status_code = 200
    token_resp.json.return_value = {"access_token": "ya29.test"}
    meta_resp = MagicMock()
    meta_resp.status_code = 200
    meta_resp.json.return_value = {
        "sheets": [
            {"properties": {"title": "справочник"}},
            {"properties": {"title": "ОБЩИЙ СТАТУС ПО ЗАПРОСАМ"}},
            {"properties": {"title": "Январь сводная"}},
            {"properties": {"title": "МАЙ"}},
        ]
    }
    values_resp = MagicMock()
    values_resp.status_code = 200
    values_resp.json.return_value = {
        "valueRanges": [
            {"values": [["2026"], ["Разработчик", "Ставка"]]},
            {"values": [["Разработчик"], ["Иванов iOS", 1, 0, 0, 0, 0, 0, 0, 0, 0, "выход 10.01"]]},
        ]
    }

    async def request(method: str, url: str, **_kwargs: object) -> MagicMock:
        if "values:batchGet" in url:
            return values_resp
        return meta_resp

    http.post = AsyncMock(return_value=token_resp)
    http.request = AsyncMock(side_effect=request)
    client = GoogleSheetsClient(_settings(), http)
    sheets = await client.fetch_dashboard_sheets()
    assert "ОБЩИЙ СТАТУС ПО ЗАПРОСАМ" in sheets
    assert "Январь сводная" in sheets
    assert "справочник" not in sheets
    assert "МАЙ" not in sheets
