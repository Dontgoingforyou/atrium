"""HTTP-клиент Google Sheets API v4 (httpx + JWT service account)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx
from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError
from app.integrations.google_sheets.jwt_sa import (
    GOOGLE_TOKEN_URL,
    build_service_account_jwt,
    parse_service_account_json,
)
from app.portal_bench.services._ingest import STATUS_SHEET, month_from_sheet_name

logger = logging.getLogger(__name__)

_SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


def _json_object(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except (ValueError, TypeError) as exc:
        logger.warning("Google Sheets API: невалидный JSON status=%s", response.status_code)
        raise ServiceUnavailableError("Google Sheets вернула ошибку") from exc
    if not isinstance(data, dict):
        logger.warning("Google Sheets API: JSON не объект status=%s", response.status_code)
        raise ServiceUnavailableError("Google Sheets вернула ошибку")
    return data


def quote_sheet_range(title: str) -> str:
    escaped = title.replace("'", "''")
    return f"'{escaped}'"


class GoogleSheetsClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http
        self._access_token: str | None = None

    def _require_enabled(self) -> None:
        if not self._settings.google_sheets_enabled:
            raise ServiceUnavailableError("Интеграция с Google Sheets не настроена")

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        self._require_enabled()
        token = await self._access_token_value()
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = await self._http.request(method, url, headers=headers, **kwargs)
        except httpx.RequestError as exc:
            logger.warning("Google Sheets API: сетевой сбой %s", type(exc).__name__)
            raise ServiceUnavailableError("Google Sheets временно недоступна") from exc
        if response.status_code >= 400:
            logger.warning("Google Sheets API %s → %s", method, response.status_code)
            raise ServiceUnavailableError("Google Sheets вернула ошибку")
        return _json_object(response)

    async def _access_token_value(self) -> str:
        if self._access_token:
            return self._access_token
        try:
            account = parse_service_account_json(self._settings.google_sheets_service_account_json)
            assertion = build_service_account_jwt(account)
        except ValueError as exc:
            logger.warning("Google Sheets: %s", exc)
            raise ServiceUnavailableError("Интеграция с Google Sheets не настроена") from exc
        try:
            response = await self._http.post(
                GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
            )
        except httpx.RequestError as exc:
            logger.warning("Google OAuth: сетевой сбой %s", type(exc).__name__)
            raise ServiceUnavailableError("Google Sheets временно недоступна") from exc
        if response.status_code >= 400:
            logger.warning("Google OAuth → %s", response.status_code)
            raise ServiceUnavailableError("Google Sheets вернула ошибку")
        payload = _json_object(response)
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            logger.warning("Google OAuth: нет access_token")
            raise ServiceUnavailableError("Google Sheets вернула ошибку")
        self._access_token = token
        return token

    async def list_sheet_titles(self) -> list[str]:
        spreadsheet_id = quote(self._settings.google_sheets_spreadsheet_id, safe="")
        url = f"{_SHEETS_API}/{spreadsheet_id}"
        data = await self._request("GET", url, params={"fields": "sheets.properties.title"})
        titles: list[str] = []
        for sheet in data.get("sheets") or []:
            if not isinstance(sheet, dict):
                continue
            props = sheet.get("properties") or {}
            title = props.get("title") if isinstance(props, dict) else None
            if isinstance(title, str) and title:
                titles.append(title)
        return titles

    def _select_sheet_titles(self, titles: list[str]) -> list[str]:
        selected: list[str] = []
        for title in titles:
            if title.strip().lower() == STATUS_SHEET:
                selected.append(title)
                continue
            if month_from_sheet_name(title) is not None:
                selected.append(title)
        return selected

    async def fetch_dashboard_sheets(self) -> dict[str, list[list[object]]]:
        """Все листы «* сводная» и «ОБЩИЙ СТАТУС ПО ЗАПРОСАМ»."""
        titles = self._select_sheet_titles(await self.list_sheet_titles())
        if not titles:
            logger.warning("Google Sheets: нет листов сводной или статуса")
            return {}
        spreadsheet_id = quote(self._settings.google_sheets_spreadsheet_id, safe="")
        url = f"{_SHEETS_API}/{spreadsheet_id}/values:batchGet"
        params = [("ranges", quote_sheet_range(title)) for title in titles]
        data = await self._request("GET", url, params=params)
        result: dict[str, list[list[object]]] = {}
        for title, value_range in zip(titles, data.get("valueRanges") or [], strict=False):
            if not isinstance(value_range, dict):
                continue
            values = value_range.get("values") or []
            if isinstance(values, list):
                result[title] = values
        return result
