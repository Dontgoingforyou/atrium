"""Сканирование дерева экспорта BuildIn."""

from __future__ import annotations

from pathlib import Path

import pytest
from buildin_import.scan import resolve_workspace_root, scan_workspace
from tests.scripts.conftest import (
    CHILD_PAGE_UUID,
    CSV_PAGE_UUID,
    DIR_ONLY_UUID,
    ROOT_PAGE_UUID,
    TASKS_PAGE_UUID,
)


def test_resolve_workspace_root_outstaff_wrapper(buildin_workspace: Path) -> None:
    root = buildin_workspace.parent
    assert resolve_workspace_root(root) == buildin_workspace


def test_resolve_workspace_root_direct(tmp_path: Path) -> None:
    (tmp_path / "Задачи+abc").mkdir()
    assert resolve_workspace_root(tmp_path) == tmp_path.resolve()


def test_resolve_workspace_root_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Каталог не найден"):
        resolve_workspace_root(tmp_path / "nope")


def test_scan_workspace_skips_tasks_and_collects_pages(buildin_workspace: Path) -> None:
    scan = scan_workspace(buildin_workspace)
    uuids = {p.page_uuid for p in scan.markdown_pages}
    assert ROOT_PAGE_UUID in uuids
    assert CHILD_PAGE_UUID in uuids
    assert DIR_ONLY_UUID in uuids
    assert TASKS_PAGE_UUID not in uuids

    dir_page = next(p for p in scan.markdown_pages if p.page_uuid == DIR_ONLY_UUID)
    assert not dir_page.path.is_file()

    assert len(scan.csv_tables) == 1
    assert scan.csv_tables[0].page_uuid == CSV_PAGE_UUID
    assert scan.csv_tables[0].rows[0]["col1"] == "a"

    assert any(a.rel_path.endswith("photo.png") for a in scan.assets)


def test_scan_workspace_parent_links(buildin_workspace: Path) -> None:
    scan = scan_workspace(buildin_workspace)
    child = next(p for p in scan.markdown_pages if p.page_uuid == CHILD_PAGE_UUID)
    assert child.parent_page_uuid == ROOT_PAGE_UUID
