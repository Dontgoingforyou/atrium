"""Оркестрация импорта документов BuildIn → PostgreSQL (+ MinIO).

Папка «Задачи» в экспорте не импортируется (только документы и CSV-таблицы вне неё).
"""

from __future__ import annotations

import logging
import mimetypes
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from buildin_import.csv_html import csv_rows_to_html
from buildin_import.ids import buildin_entity_id
from buildin_import.md_html import markdown_to_html, rewrite_internal_links
from buildin_import.scan import (
    CsvTable,
    MarkdownPage,
    WorkspaceScan,
    resolve_workspace_root,
    scan_workspace,
)

logger = logging.getLogger(__name__)

_IMG_SRC_RE = re.compile(r'src=(["\'])([^"\']+)\1')
_PRESIGN_TTL_IMPORT = 7 * 24 * 3600


@dataclass
class ImportStats:
    documents_created: int = 0
    documents_updated: int = 0
    assets_uploaded: int = 0
    csv_documents: int = 0
    skipped_empty_md: int = 0
    tasks_skipped: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class ImportContext:
    dry_run: bool
    author_sub: str
    workspace: Path
    scan: WorkspaceScan
    page_uuid_to_portal_id: dict[str, uuid.UUID] = field(default_factory=dict)
    asset_url_by_rel: dict[str, str] = field(default_factory=dict)
    stats: ImportStats = field(default_factory=ImportStats)


async def resolve_author_sub(session: AsyncSession, *, dry_run: bool) -> str:
    if dry_run:
        return "buildin-import-dry-run"
    result = await session.execute(
        select(PortalUserProfile).order_by(PortalUserProfile.updated_at.desc()).limit(1)
    )
    profile = result.scalar_one_or_none()
    if profile is not None:
        return profile.sub
    sub = "buildin-import-user"
    session.add(
        PortalUserProfile(
            sub=sub,
            email="buildin-import@localhost",
            full_name="BuildIn Import",
            username="buildin-import",
        )
    )
    await session.flush()
    return sub


def upload_assets(ctx: ImportContext) -> None:
    if ctx.dry_run:
        ctx.stats.assets_uploaded = len(ctx.scan.assets)
        return
    from app.core.config import get_settings
    from app.infrastructure.storage.client import ensure_bucket_exists, get_presigned_url, upload_bytes_to_key

    settings = get_settings()
    ensure_bucket_exists(settings.minio_bucket)

    for asset in ctx.scan.assets:
        data = asset.path.read_bytes()
        content_type = mimetypes.guess_type(asset.path.name)[0] or "application/octet-stream"
        key = f"buildin-import/{uuid.uuid4()}"
        try:
            upload_bytes_to_key(data=data, storage_key=key, content_type=content_type)
            url = get_presigned_url(key, ttl_seconds=_PRESIGN_TTL_IMPORT, filename=asset.path.name)
            ctx.asset_url_by_rel[asset.rel_path] = url
            ctx.stats.assets_uploaded += 1
        except Exception as exc:
            ctx.stats.warnings.append(f"MinIO {asset.rel_path}: {exc}")


def _normalize_asset_key(path: str) -> str:
    return unquote(path).replace("\\", "/").lower()


def _rewrite_asset_refs(html: str, asset_urls: dict[str, str]) -> str:
    if not asset_urls:
        return html

    by_key = {_normalize_asset_key(rel): url for rel, url in asset_urls.items()}
    by_name: dict[str, str] = {}
    for rel, url in asset_urls.items():
        by_name[Path(rel).name.lower()] = url

    def repl_src(match: re.Match[str]) -> str:
        quote = match.group(1)
        src = unquote(match.group(2))
        norm = _normalize_asset_key(src)
        url = by_key.get(norm)
        if url is None:
            for key, candidate in by_key.items():
                if norm.endswith(key) or key.endswith(norm):
                    url = candidate
                    break
        if url is None:
            url = by_name.get(Path(norm).name)
        if url is None:
            return match.group(0)
        return f"src={quote}{url}{quote}"

    return _IMG_SRC_RE.sub(repl_src, html)


def _csv_table_portal_id(table: CsvTable) -> uuid.UUID:
    return buildin_entity_id(f"csv:{table.page_uuid}")


def _ordered_pages(pages: list[MarkdownPage]) -> list[MarkdownPage]:
    """Родители раньше детей (топологическая сортировка по parent_page_uuid)."""
    children: dict[str | None, list[MarkdownPage]] = {}
    for p in pages:
        children.setdefault(p.parent_page_uuid, []).append(p)

    out: list[MarkdownPage] = []

    def walk(parent: str | None) -> None:
        for p in sorted(children.get(parent, []), key=lambda x: x.sort_index):
            out.append(p)
            walk(p.page_uuid)

    walk(None)
    for p in pages:
        if p not in out:
            out.append(p)
    return out


async def import_documents(ctx: ImportContext, session: AsyncSession) -> None:
    doc_pages = list(ctx.scan.markdown_pages)
    bodies: dict[str, str] = {}

    for page in _ordered_pages(doc_pages):
        if not page.path.is_file():
            bodies[page.page_uuid] = "<p><em>Раздел без текста в экспорте BuildIn</em></p>"
            continue
        raw = page.path.read_text(encoding="utf-8", errors="replace")
        if not raw.strip():
            ctx.stats.skipped_empty_md += 1
            bodies[page.page_uuid] = ""
            continue
        bodies[page.page_uuid] = markdown_to_html(raw)

    for table in ctx.scan.csv_tables:
        bodies[table.page_uuid] = csv_rows_to_html(table.rows, caption=table.title)

    uuid_to_url = {
        uid: f"/documents/{buildin_entity_id(uid)}"
        for uid in set(bodies) | {t.page_uuid for t in ctx.scan.csv_tables}
    }
    for uid, html in list(bodies.items()):
        bodies[uid] = rewrite_internal_links(html, uuid_to_url)
        bodies[uid] = _rewrite_asset_refs(bodies[uid], ctx.asset_url_by_rel)

    for page in _ordered_pages(doc_pages):
        portal_id = buildin_entity_id(page.page_uuid)
        ctx.page_uuid_to_portal_id[page.page_uuid] = portal_id
        parent_id = buildin_entity_id(page.parent_page_uuid) if page.parent_page_uuid else None
        body = bodies.get(page.page_uuid) or "<p><em>Пустая страница</em></p>"
        if ctx.dry_run:
            ctx.stats.documents_created += 1
            continue
        existing = await session.get(PortalDocument, portal_id)
        if existing is None:
            session.add(
                PortalDocument(
                    id=portal_id,
                    title=page.title[:512],
                    parent_document_id=parent_id,
                    author_sub=ctx.author_sub,
                    body=body,
                    sort_order=page.sort_index,
                )
            )
            ctx.stats.documents_created += 1
        else:
            existing.title = page.title[:512]
            existing.body = body
            existing.parent_document_id = parent_id
            existing.sort_order = page.sort_index
            ctx.stats.documents_updated += 1

    for table in ctx.scan.csv_tables:
        portal_id = _csv_table_portal_id(table)
        ctx.page_uuid_to_portal_id[table.page_uuid] = portal_id
        parent_id = buildin_entity_id(table.parent_page_uuid) if table.parent_page_uuid else None
        body = bodies[table.page_uuid]
        if ctx.dry_run:
            ctx.stats.csv_documents += 1
            ctx.stats.documents_created += 1
            continue
        existing = await session.get(PortalDocument, portal_id)
        if existing is None:
            session.add(
                PortalDocument(
                    id=portal_id,
                    title=table.title[:512],
                    parent_document_id=parent_id,
                    author_sub=ctx.author_sub,
                    body=body,
                    sort_order=9999,
                )
            )
            ctx.stats.csv_documents += 1
            ctx.stats.documents_created += 1
        else:
            existing.body = body
            existing.title = table.title[:512]
            ctx.stats.documents_updated += 1


def _count_tasks_tree(workspace: Path) -> int:
    """Сколько файлов в папке «Задачи» пропускаем (для отчёта)."""
    from buildin_import.ids import is_tasks_path

    n = 0
    for path in workspace.rglob("*"):
        if path.is_file() and is_tasks_path(path.relative_to(workspace).parts):
            n += 1
    return n


async def run_import(
    *,
    import_root: Path,
    dry_run: bool,
    session: AsyncSession,
) -> ImportStats:
    workspace = resolve_workspace_root(import_root)
    scan = scan_workspace(workspace)
    author_sub = await resolve_author_sub(session, dry_run=dry_run)

    ctx = ImportContext(
        dry_run=dry_run,
        author_sub=author_sub,
        workspace=workspace,
        scan=scan,
    )
    ctx.stats.tasks_skipped = _count_tasks_tree(workspace)

    upload_assets(ctx)
    await import_documents(ctx, session)
    return ctx.stats


def print_report(stats: ImportStats, workspace: Path, *, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"\n=== BuildIn import [{mode}] — только документы ===")
    print(f"Workspace: {workspace}")
    print(f"Документы: создано {stats.documents_created}, обновлено {stats.documents_updated}")
    print(f"CSV-документы: {stats.csv_documents}")
    print(f"Вложения в MinIO: {stats.assets_uploaded}")
    print(f"Пустых .md (тело): {stats.skipped_empty_md}")
    print(f"Пропущено файлов в «Задачи» (не импортируем): {stats.tasks_skipped}")
    if stats.warnings:
        print("Предупреждения:")
        for w in stats.warnings[:30]:
            print(f"  - {w}")
        if len(stats.warnings) > 30:
            print(f"  … ещё {len(stats.warnings) - 30}")
