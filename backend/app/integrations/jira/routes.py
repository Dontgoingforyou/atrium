"""Webhook Jira."""

from __future__ import annotations

import logging
from typing import Any

from app.api.deps import DbSession, HttpClient
from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError, ValidationError
from app.core.utils import hmac_secrets_equal
from app.portal_specialists.services import jira_import as jira_svc
from fastapi import APIRouter, Header, Request, Response, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/jira", tags=["Интеграции — Jira"])


def _extract_issue_key(payload: dict[str, Any]) -> str | None:
    issue = payload.get("issue")
    if isinstance(issue, dict) and issue.get("key"):
        return str(issue["key"])
    key = payload.get("issue_key") or payload.get("key")
    return str(key) if key else None


@router.post("/webhook", summary="Webhook обновления issue Jira")
async def jira_webhook(
    request: Request,
    session: DbSession,
    http: HttpClient,
    x_jira_webhook_secret: str | None = Header(default=None, alias="X-Jira-Webhook-Secret"),
) -> Response:
    settings = get_settings()
    expected = settings.jira_webhook_secret.strip()
    if not hmac_secrets_equal(x_jira_webhook_secret, expected):
        logger.warning("Jira webhook: отклонён (неверный secret) ip=%s", request.client.host if request.client else "?")
        raise ForbiddenError("Неверный секрет webhook")

    try:
        payload = await request.json()
    except Exception as exc:
        logger.warning("Jira webhook: невалидный JSON: %s", exc)
        raise BadRequestError("Невалидный JSON") from exc

    if not isinstance(payload, dict):
        logger.warning("Jira webhook: payload не является объектом (тип %s)", type(payload).__name__)
        raise BadRequestError("Тело webhook должно быть объектом")

    issue_key = _extract_issue_key(payload)
    if not issue_key:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    try:
        updated = await jira_svc.apply_jira_webhook(session, http, issue_key)
    except ValidationError:
        # Чужой проект (например TASKS) — не наша карточка, без ретраев Jira.
        logger.warning("Jira webhook: ключ не из проекта специалистов issue_key=%s", issue_key)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        logger.warning("Jira webhook: ошибка issue_key=%s: %s", issue_key, exc)
        raise

    if not updated:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return Response(status_code=status.HTTP_200_OK)
