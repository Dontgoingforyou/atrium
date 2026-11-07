"""Фикстуры для тестов BuildIn-import (минимальное дерево экспорта)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT_PAGE_UUID = "11111111-1111-1111-1111-111111111111"
CHILD_PAGE_UUID = "22222222-2222-2222-2222-222222222222"
CSV_PAGE_UUID = "33333333-3333-3333-3333-333333333333"
TASKS_PAGE_UUID = "44444444-4444-4444-4444-444444444444"
DIR_ONLY_UUID = "55555555-5555-5555-5555-555555555555"


def write_minimal_buildin_workspace(root: Path) -> Path:
    """Outstaff+ workspace: md, csv, dir-only, задачи (skip), asset."""
    workspace = root / "Outstaff+aaa"
    workspace.mkdir(parents=True)

    (workspace / f"Root+{ROOT_PAGE_UUID}.md").write_text(
        f"# Root\n\nSee [child](Child+{CHILD_PAGE_UUID}.md)\n",
        encoding="utf-8",
    )
    parent_dir = workspace / f"Parent+{ROOT_PAGE_UUID}"
    parent_dir.mkdir()
    (parent_dir / f"Child+{CHILD_PAGE_UUID}.md").write_text("Child body\n", encoding="utf-8")

    csv_dir = workspace / f"Table+{CSV_PAGE_UUID}"
    csv_dir.mkdir()
    (csv_dir / f"Table+{CSV_PAGE_UUID}.csv").write_text(
        "col1,col2\na,b\n",
        encoding="utf-8-sig",
    )

    dir_only = workspace / f"Section+{DIR_ONLY_UUID}"
    dir_only.mkdir()

    tasks = workspace / f"Задачи+{TASKS_PAGE_UUID}"
    tasks.mkdir()
    (tasks / f"Task+{TASKS_PAGE_UUID}.md").write_text("must skip\n", encoding="utf-8")

    assets_dir = workspace / f"Assets+{ROOT_PAGE_UUID}"
    assets_dir.mkdir()
    (assets_dir / "photo.png").write_bytes(b"\x89PNG\r\n")

    return workspace


@pytest.fixture
def buildin_workspace(tmp_path: Path) -> Path:
    return write_minimal_buildin_workspace(tmp_path)
