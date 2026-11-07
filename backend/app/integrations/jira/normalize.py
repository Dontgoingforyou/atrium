"""Нормализация полей Jira issue для UI и импорта."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse

from app.integrations.jira.fields import (
    GROUP_LABELS,
    JIRA_FIELD_LABEL_BY_ID,
    JIRA_FIELD_SPECS,
    JIRA_LINK_FIELDS,
    JIRA_NATIVE_UI_FIELD_IDS,
)

_URL_RE = re.compile(r"^https?://", re.I)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list | dict):
        return len(value) == 0
    return False


def _format_user(user: dict[str, Any] | None) -> str | None:
    if not user:
        return None
    name = user.get("displayName") or user.get("name")
    email = user.get("emailAddress")
    if name and email:
        return f"{name} ({email})"
    return str(name or email or "")


def _format_users(users: list[Any] | None) -> str | None:
    if not users:
        return None
    parts: list[str] = []
    for item in users:
        if isinstance(item, dict):
            formatted = _format_user(item)
            if formatted:
                parts.append(formatted)
        elif isinstance(item, str) and item.strip():
            parts.append(item.strip())
    return "; ".join(parts) if parts else None


def _format_option(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        v = value.get("value") or value.get("name")
        return str(v) if v else None
    if isinstance(value, list):
        opts_raw = [_format_option(v) for v in value]
        opts: list[str] = [o for o in opts_raw if o is not None]
        return ", ".join(opts) if opts else None
    return str(value).strip() or None


def _format_raw(field_id: str, value: Any) -> str | None:
    if _is_empty(value):
        return None
    if field_id in ("assignee", "reporter", "creator"):
        return _format_user(value) if isinstance(value, dict) else None
    if field_id in ("status", "issuetype", "priority"):
        return _format_option(value)
    if field_id in ("labels", "fixVersions"):
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict):
                    parts.append(str(item.get("name") or item.get("value") or ""))
                else:
                    parts.append(str(item))
            parts = [p for p in parts if p]
            return ", ".join(parts) if parts else None
    if field_id.startswith("customfield_"):
        if isinstance(value, list):
            if value and isinstance(value[0], dict) and "displayName" in value[0]:
                return _format_users(value)
            if value and isinstance(value[0], dict) and "value" in value[0]:
                return _format_option(value)
            return ", ".join(str(v) for v in value if v) or None
        if isinstance(value, dict):
            if "displayName" in value:
                return _format_user(value)
            return _format_option(value)
    if isinstance(value, str):
        return value.strip() or None
    return str(value)


def _field_kind(field_id: str, value: Any, display: str | None) -> str:
    if display and _URL_RE.match(display):
        return "url"
    if field_id in ("assignee", "reporter", "creator") or (isinstance(value, dict) and "displayName" in value):
        return "user"
    return "text"


def extract_jira_field_text(field_id: str, value: Any) -> str | None:
    """Текстовое значение поля Jira для импорта в профиль/статус."""
    return _format_raw(field_id, value)


def normalize_issue_fields(issue: dict[str, Any]) -> dict[str, Any]:
    """Снимок полей issue для хранения в jira_fields и отдачи в API."""
    fields_raw: dict[str, Any] = issue.get("fields") or {}
    names: dict[str, str] = issue.get("names") or {}
    normalized: list[dict[str, Any]] = []

    for spec in JIRA_FIELD_SPECS:
        if spec.field_id in JIRA_NATIVE_UI_FIELD_IDS:
            continue
        raw = fields_raw.get(spec.field_id)
        # Портальные подписи важнее локализованных имён Jira (summary → «Тема» в ru).
        label = JIRA_FIELD_LABEL_BY_ID.get(spec.field_id) or names.get(spec.field_id) or spec.label
        display = _format_raw(spec.field_id, raw)
        normalized.append(
            {
                "id": spec.field_id,
                "label": label,
                "group": spec.group,
                "value": display,
                "kind": _field_kind(spec.field_id, raw, display),
            },
        )

    groups: list[dict[str, Any]] = []
    for group_key, group_label in GROUP_LABELS.items():
        group_fields = [f for f in normalized if f["group"] == group_key]
        if not group_fields:
            continue
        groups.append({"key": group_key, "label": group_label, "fields": group_fields})

    return {
        "issue_key": issue.get("key"),
        "groups": groups,
    }


def _apply_portal_field_labels(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Подставить портальные подписи (в т.ч. для снимков с «Тема» из Jira names)."""
    relabeled: list[dict[str, Any]] = []
    for group in groups:
        fields = []
        for field in group.get("fields") or []:
            field_id = field.get("id")
            portal_label = JIRA_FIELD_LABEL_BY_ID.get(field_id) if field_id else None
            if portal_label:
                fields.append({**field, "label": portal_label})
            else:
                fields.append(field)
        relabeled.append({**group, "fields": fields})
    return relabeled


def filter_jira_groups_for_display(groups: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Отфильтровать группы/поля для UI (в т.ч. устаревшие снимки до sync)."""
    if not groups:
        return []
    hidden = JIRA_NATIVE_UI_FIELD_IDS
    filtered: list[dict[str, Any]] = []
    for group in groups:
        fields = [f for f in group.get("fields") or [] if f.get("id") not in hidden]
        if not fields:
            continue
        filtered.append({**group, "fields": fields})
    return _apply_portal_field_labels(filtered)


def parse_jira_date(raw: str | None) -> date | None:
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10] if fmt == "%Y-%m-%d" else text, fmt).date()
        except ValueError:
            continue
    return None


def is_http_url(text: str) -> bool:
    """Только http/https с host — отсекает javascript:/data:/ftp: (XSS в <a href>)."""
    parsed = urlparse(text.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def extract_link_urls(fields_raw: dict[str, Any]) -> list[tuple[str, str]]:
    """(title, url) для upsert ссылок."""
    out: list[tuple[str, str]] = []
    for field_id, title in JIRA_LINK_FIELDS.items():
        raw = fields_raw.get(field_id)
        if not raw or not isinstance(raw, str):
            continue
        text = raw.strip()
        if not text:
            continue
        if is_http_url(text):
            out.append((title, text))
    return out


def get_field_value(fields_raw: dict[str, Any], field_id: str) -> Any:
    return fields_raw.get(field_id)
