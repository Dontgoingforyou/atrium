"""HTTP-клиент сверки почт с сервисом профилей."""

from __future__ import annotations

import logging
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any

import httpx
from app.core.config import Settings

logger = logging.getLogger(__name__)

EMAILS_CHECK_PATH = "/api/v1/emails/check"
EMAILS_CHECK_MAX = 500


@dataclass(frozen=True)
class EmailsCheckResult:
    found: frozenset[str]
    not_found: frozenset[str]


def normalize_email(email: str) -> str:
    return email.strip().lower()


class ProfileDirectoryEmailsClient:
    """Клиент ``POST /api/v1/emails/check``: found = активная запись каталога."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http
        self._base = settings.profile_directory_base_url.rstrip("/")

    def _enabled(self) -> bool:
        return self._settings.profile_directory_emails_check_enabled

    def _timeout(self) -> float:
        return self._settings.profile_directory_timeout_seconds

    async def check_emails(self, emails: Collection[str]) -> EmailsCheckResult | None:
        """Сверить почты. ``None`` — сверка недоступна (не настроена или сбой)."""
        if not self._enabled():
            return None
        unique: list[str] = []
        seen: set[str] = set()
        for raw in emails:
            normalized = normalize_email(raw)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)
        if not unique:
            return EmailsCheckResult(found=frozenset(), not_found=frozenset())

        found: set[str] = set()
        not_found: set[str] = set()
        for start in range(0, len(unique), EMAILS_CHECK_MAX):
            batch = unique[start : start + EMAILS_CHECK_MAX]
            part = await self._post_batch(batch)
            if part is None:
                return None
            found.update(part.found)
            not_found.update(part.not_found)
        return EmailsCheckResult(found=frozenset(found), not_found=frozenset(not_found))

    async def _post_batch(self, emails: list[str]) -> EmailsCheckResult | None:
        url = f"{self._base}{EMAILS_CHECK_PATH}"
        token = self._settings.profile_directory_service_token.strip()
        try:
            response = await self._http.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"emails": emails},
                timeout=self._timeout(),
            )
        except httpx.RequestError as exc:
            logger.warning("EA emails/check: сетевой сбой %s", type(exc).__name__)
            return None
        if response.status_code >= 400:
            logger.warning("EA emails/check → %s", response.status_code)
            return None
        try:
            data: Any = response.json()
        except (ValueError, TypeError):
            logger.warning("EA emails/check: тело не JSON")
            return None
        if not isinstance(data, dict):
            logger.warning("EA emails/check: неожиданный JSON")
            return None
        return EmailsCheckResult(
            found=_email_set(data.get("found")),
            not_found=_email_set(data.get("not_found")),
        )


def _email_set(raw: object) -> frozenset[str]:
    if not isinstance(raw, list):
        return frozenset()
    out: set[str] = set()
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.add(normalize_email(item))
    return frozenset(out)
