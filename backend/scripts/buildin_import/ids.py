"""Стабильные UUID и разбор имён файлов BuildIn."""

from __future__ import annotations

import re
import uuid
from urllib.parse import unquote_plus

from app.data.portal_navigation_seed import PORTAL_NAV_NAMESPACE

BUILDIN_IMPORT_NS = uuid.uuid5(PORTAL_NAV_NAMESPACE, "buildin_outstaff_import")

_PAGE_UUID_RE = re.compile(
    r"\+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:\.md)?$",
    re.IGNORECASE,
)
_TASKS_DIR_PREFIX = "Задачи+"


def buildin_entity_id(page_uuid: str) -> uuid.UUID:
    return uuid.uuid5(BUILDIN_IMPORT_NS, page_uuid.lower())


def extract_page_uuid(name: str) -> str | None:
    m = _PAGE_UUID_RE.search(name)
    return m.group(1).lower() if m else None


def title_from_buildin_name(name: str) -> str:
    """Имя файла/папки без суффикса +uuid и с пробелами вместо '+'."""
    stem = name
    if stem.lower().endswith(".md"):
        stem = stem[:-3]
    m = _PAGE_UUID_RE.search(stem)
    if m:
        stem = stem[: m.start()]
    return unquote_plus(stem.replace("+", " ")).strip() or name


def is_tasks_path(rel_parts: tuple[str, ...]) -> bool:
    return any(p.startswith(_TASKS_DIR_PREFIX) for p in rel_parts)


def normalize_match_key(title: str) -> str:
    return " ".join(title.lower().split())
