"""Стабильные UUID и разбор имён BuildIn."""

from __future__ import annotations

import uuid

from buildin_import.ids import (
    buildin_entity_id,
    extract_page_uuid,
    is_tasks_path,
    normalize_match_key,
    title_from_buildin_name,
)

_PAGE = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_buildin_entity_id_stable() -> None:
    a = buildin_entity_id(_PAGE)
    b = buildin_entity_id(_PAGE.upper())
    assert a == b
    assert isinstance(a, uuid.UUID)


def test_extract_page_uuid_from_md_name() -> None:
    assert extract_page_uuid(f"Page+{_PAGE}.md") == _PAGE


def test_title_from_buildin_name() -> None:
    assert title_from_buildin_name(f"My+Title+{_PAGE}.md") == "My Title"
    assert title_from_buildin_name(f"Plain+{_PAGE}") == "Plain"


def test_is_tasks_path() -> None:
    assert is_tasks_path(("Задачи+abc", "file.md")) is True
    assert is_tasks_path(("Docs", "file.md")) is False


def test_normalize_match_key() -> None:
    assert normalize_match_key("  Foo   Bar  ") == "foo bar"
