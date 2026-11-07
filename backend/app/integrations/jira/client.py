"""HTTP-клиент Jira REST API."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from app.core.config import Settings
from app.core.exceptions import NotFoundError, ServiceUnavailableError

logger = logging.getLogger(__name__)


def _json_payload(response: httpx.Response) -> Any:
    try:
        return response.json()
    except (ValueError, TypeError) as exc:
        logger.warning("Jira API: невалидный JSON status=%s", response.status_code)
        raise ServiceUnavailableError("Jira вернула ошибку") from exc


def _json_object(response: httpx.Response) -> dict[str, Any]:
    data = _json_payload(response)
    if not isinstance(data, dict):
        logger.warning("Jira API: JSON не объект status=%s", response.status_code)
        raise ServiceUnavailableError("Jira вернула ошибку")
    return data


def _json_list(response: httpx.Response) -> list[Any]:
    data = _json_payload(response)
    if not isinstance(data, list):
        logger.warning("Jira API: JSON не список status=%s", response.status_code)
        raise ServiceUnavailableError("Jira вернула ошибку")
    return data


class JiraClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http
        self._base = settings.jira_base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {settings.jira_personal_access_token}"}

    def _require_enabled(self) -> None:
        if not self._settings.jira_enabled:
            raise ServiceUnavailableError("Интеграция с Jira не настроена")

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        self._require_enabled()
        url = f"{self._base}{path}"
        try:
            response = await self._http.request(method, url, headers=self._headers, **kwargs)
        except httpx.RequestError as exc:
            logger.warning("Jira API: сетевой сбой %s: %s", type(exc).__name__, exc)
            raise ServiceUnavailableError("Jira временно недоступна") from exc
        if response.status_code == 404:
            raise NotFoundError("Задача Jira не найдена")
        if response.status_code >= 400:
            logger.warning("Jira API %s %s → %s", method, path, response.status_code)
            raise ServiceUnavailableError("Jira вернула ошибку")
        return _json_object(response)

    async def search_issues(
        self,
        jql: str,
        *,
        fields: list[str] | None = None,
        max_results: int = 20,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"jql": jql, "maxResults": max_results}
        if fields:
            params["fields"] = ",".join(fields)
        return await self._request("GET", "/rest/api/2/search", params=params)

    async def get_issue(self, issue_key: str, *, expand: str = "names") -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/rest/api/2/issue/{issue_key}",
            params={"expand": expand},
        )

    async def get_board_configuration(self, board_id: int | None = None) -> dict[str, Any]:
        bid = board_id if board_id is not None else self._settings.jira_board_id
        return await self._request("GET", f"/rest/agile/1.0/board/{bid}/configuration")
