"""Сканирование дерева экспорта BuildIn."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

from buildin_import.ids import (
    extract_page_uuid,
    is_tasks_path,
    title_from_buildin_name,
)


@dataclass(slots=True)
class MarkdownPage:
    page_uuid: str
    path: Path
    title: str
    parent_page_uuid: str | None
    sort_index: int


@dataclass(slots=True)
class CsvTable:
    page_uuid: str
    path: Path
    title: str
    parent_page_uuid: str | None
    rows: list[dict[str, str]]


@dataclass(slots=True)
class BinaryAsset:
    path: Path
    rel_path: str
    page_uuid: str | None


@dataclass(slots=True)
class WorkspaceScan:
    workspace: Path
    markdown_pages: list[MarkdownPage] = field(default_factory=list)
    csv_tables: list[CsvTable] = field(default_factory=list)
    assets: list[BinaryAsset] = field(default_factory=list)


def resolve_workspace_root(import_root: Path) -> Path:
    import_root = import_root.resolve()
    if not import_root.is_dir():
        raise FileNotFoundError(f"Каталог не найден: {import_root}")
    outstaff_dirs = [p for p in import_root.iterdir() if p.is_dir() and p.name.startswith("Outstaff+")]
    if len(outstaff_dirs) == 1:
        return outstaff_dirs[0]
    if any(p.name.startswith("Задачи+") or p.name.startswith("Account+") for p in import_root.iterdir()):
        return import_root
    if outstaff_dirs:
        return outstaff_dirs[0]
    raise FileNotFoundError(
        f"Не найден workspace BuildIn в {import_root} (ожидали Outstaff+…/ или корневые разделы)"
    )


def _parent_uuid_for(rel_parts: tuple[str, ...]) -> str | None:
    if len(rel_parts) < 2:
        return None
    parent_name = rel_parts[-2]
    return extract_page_uuid(parent_name)


def scan_workspace(workspace: Path) -> WorkspaceScan:
    result = WorkspaceScan(workspace=workspace)
    md_candidates: list[tuple[Path, tuple[str, ...], int]] = []

    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(workspace)
        parts = rel.parts
        if is_tasks_path(parts):
            continue
        if path.suffix.lower() == ".md":
            page_uuid = extract_page_uuid(path.name)
            if page_uuid is None:
                continue
            md_candidates.append((path, parts, len(md_candidates)))
            continue
        if path.suffix.lower() == ".csv":
            page_uuid = extract_page_uuid(path.stem)
            if page_uuid is None:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            rows = [dict(row) for row in reader]
            result.csv_tables.append(
                CsvTable(
                    page_uuid=page_uuid,
                    path=path,
                    title=f"{title_from_buildin_name(path.stem)} (таблица CSV)",
                    parent_page_uuid=_parent_uuid_for(parts),
                    rows=rows,
                )
            )
            continue
        rel_str = str(rel).replace("\\", "/")
        container_uuid = _parent_uuid_for(parts) if parts else None
        if container_uuid is None and parts:
            container_uuid = extract_page_uuid(parts[0])
        result.assets.append(
            BinaryAsset(
                path=path,
                rel_path=rel_str,
                page_uuid=container_uuid,
            )
        )

    for path, parts, sort_index in md_candidates:
        page_uuid = extract_page_uuid(path.name)
        assert page_uuid is not None
        result.markdown_pages.append(
            MarkdownPage(
                page_uuid=page_uuid,
                path=path,
                title=title_from_buildin_name(path.name),
                parent_page_uuid=_parent_uuid_for(parts),
                sort_index=sort_index,
            )
        )

    seen_md_uuids = {p.page_uuid for p in result.markdown_pages}
    dir_sort = len(result.markdown_pages)
    for path in sorted(workspace.rglob("*")):
        if not path.is_dir():
            continue
        rel = path.relative_to(workspace)
        if is_tasks_path(rel.parts):
            continue
        page_uuid = extract_page_uuid(path.name)
        if page_uuid is None or page_uuid in seen_md_uuids:
            continue
        result.markdown_pages.append(
            MarkdownPage(
                page_uuid=page_uuid,
                path=path / ".buildin-dir-placeholder",
                title=title_from_buildin_name(path.name),
                parent_page_uuid=_parent_uuid_for(rel.parts),
                sort_index=dir_sort,
            )
        )
        seen_md_uuids.add(page_uuid)
        dir_sort += 1

    return result
