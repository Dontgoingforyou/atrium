"""Расширение JiraClient: write API для outbound задач портала."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

import httpx
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.integrations.jira.client import JiraClient, _json_list, _json_object

logger = logging.getLogger(__name__)


class JiraWriteClient(JiraClient):
    """Create/update/delete/transition/comment/attachment поверх read-only клиента."""

    async def _request_raw(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        self._require_enabled()
        url = f"{self._base}{path}"
        headers = {**self._headers, **(kwargs.pop("headers", {}) or {})}
        try:
            response = await self._http.request(method, url, headers=headers, **kwargs)
        except httpx.RequestError as exc:
            logger.warning("Jira API: сетевой сбой %s: %s", type(exc).__name__, exc)
            raise ServiceUnavailableError("Jira временно недоступна") from exc
        return response

    async def create_issue(self, fields: dict[str, Any]) -> dict[str, Any]:
        response = await self._request_raw("POST", "/rest/api/2/issue", json={"fields": fields})
        if response.status_code >= 400:
            logger.warning("Jira create issue → %s", response.status_code)
            raise ServiceUnavailableError("Jira не приняла создание задачи")
        return _json_object(response)

    async def update_issue(self, issue_key: str, fields: dict[str, Any]) -> None:
        response = await self._request_raw("PUT", f"/rest/api/2/issue/{issue_key}", json={"fields": fields})
        if response.status_code == 404:
            raise NotFoundError("Задача Jira не найдена")
        if response.status_code >= 400:
            logger.warning("Jira update %s → %s", issue_key, response.status_code)
            raise ServiceUnavailableError("Jira не приняла обновление задачи")

    async def get_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/rest/api/2/issue/{issue_key}/transitions")
        return cast(list[dict[str, Any]], data.get("transitions") or [])

    async def transition_issue(self, issue_key: str, transition_id: str) -> None:
        response = await self._request_raw(
            "POST",
            f"/rest/api/2/issue/{issue_key}/transitions",
            json={"transition": {"id": transition_id}},
        )
        if response.status_code >= 400:
            logger.warning("Jira transition %s → %s", issue_key, response.status_code)
            raise ServiceUnavailableError("Jira не приняла смену статуса")

    async def add_comment(self, issue_key: str, body: str) -> dict[str, Any]:
        response = await self._request_raw(
            "POST",
            f"/rest/api/2/issue/{issue_key}/comment",
            json={"body": body},
        )
        if response.status_code >= 400:
            logger.warning("Jira comment %s → %s", issue_key, response.status_code)
            raise ServiceUnavailableError("Jira не приняла комментарий")
        return _json_object(response)

    async def add_attachment(
        self,
        issue_key: str,
        *,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> list[dict[str, Any]]:
        headers = {**self._headers, "X-Atlassian-Token": "no-check"}
        response = await self._request_raw(
            "POST",
            f"/rest/api/2/issue/{issue_key}/attachments",
            headers=headers,
            files={"file": (filename, content, content_type)},
        )
        if response.status_code >= 400:
            logger.warning("Jira attachment %s → %s", issue_key, response.status_code)
            raise ServiceUnavailableError("Jira не приняла вложение")
        return cast(list[dict[str, Any]], _json_list(response))

    async def delete_issue(self, issue_key: str, *, delete_subtasks: bool = False) -> None:
        """Удалить issue. 404 — успех: карточки уже нет, повтор не должен падать."""
        request_kwargs: dict[str, Any] = {}
        if delete_subtasks:
            request_kwargs["params"] = {"deleteSubtasks": "true"}
        response = await self._request_raw(
            "DELETE",
            f"/rest/api/2/issue/{issue_key}",
            **request_kwargs,
        )
        if response.status_code in (204, 404):
            return
        logger.warning("Jira delete %s → %s", issue_key, response.status_code)
        raise ServiceUnavailableError("Jira не приняла удаление задачи")

    async def add_watcher(self, issue_key: str, username: str) -> None:
        response = await self._request_raw(
            "POST",
            f"/rest/api/2/issue/{issue_key}/watchers",
            content=json.dumps(username),
            headers={"Content-Type": "application/json"},
        )
        if response.status_code >= 400:
            # Уже watcher / нет прав — не валим весь sync
            logger.warning("Jira add watcher %s → %s", issue_key, response.status_code)

    async def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Server/DC: user search; только точное совпадение email, иначе None."""
        response = await self._request_raw(
            "GET",
            "/rest/api/2/user/search",
            params={"username": email, "maxResults": 5},
        )
        if response.status_code >= 400:
            logger.warning("Jira user search → %s", response.status_code)
            return None
        try:
            users = _json_list(response)
        except ServiceUnavailableError:
            return None
        wanted = email.lower()
        for item in users:
            if isinstance(item, dict) and str(item.get("emailAddress") or "").lower() == wanted:
                return cast(dict[str, Any], item)
        return None
