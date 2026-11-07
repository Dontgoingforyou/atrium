"""Оркестрация импорта BuildIn → portal_document."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from app.infrastructure.db.models.portal_document import PortalDocument
from buildin_import.ids import buildin_entity_id
from buildin_import.importer import run_import
from sqlalchemy.ext.asyncio import AsyncSession
from tests.scripts.conftest import CHILD_PAGE_UUID, ROOT_PAGE_UUID, write_minimal_buildin_workspace


@pytest.mark.asyncio
async def test_run_import_dry_run(buildin_workspace: Path, sqlite_session: AsyncSession) -> None:
    stats = await run_import(
        import_root=buildin_workspace.parent,
        dry_run=True,
        session=sqlite_session,
    )
    assert stats.documents_created >= 3
    assert stats.csv_documents == 1
    assert stats.tasks_skipped >= 1
    assert stats.assets_uploaded >= 1


@pytest.mark.asyncio
async def test_run_import_rewrites_internal_links_and_assets(
    tmp_path: Path,
    sqlite_session: AsyncSession,
) -> None:
    workspace = write_minimal_buildin_workspace(tmp_path)
    child_id = buildin_entity_id(CHILD_PAGE_UUID)
    presigned = "https://minio.example/presigned/photo.png"

    with (
        patch("app.infrastructure.storage.client.upload_bytes_to_key"),
        patch("app.infrastructure.storage.client.get_presigned_url", return_value=presigned),
        patch("app.infrastructure.storage.client.ensure_bucket_exists"),
    ):
        stats = await run_import(
            import_root=workspace.parent,
            dry_run=False,
            session=sqlite_session,
        )
    await sqlite_session.commit()
    assert stats.documents_created >= 3
    root = await sqlite_session.get(PortalDocument, buildin_entity_id(ROOT_PAGE_UUID))
    assert root is not None
    assert f'href="/documents/{child_id}"' in root.body


@pytest.mark.asyncio
async def test_run_import_update_is_idempotent(
    tmp_path: Path,
    sqlite_session: AsyncSession,
) -> None:
    workspace = write_minimal_buildin_workspace(tmp_path)

    with (
        patch("app.infrastructure.storage.client.upload_bytes_to_key"),
        patch("app.infrastructure.storage.client.get_presigned_url", return_value="https://u"),
        patch("app.infrastructure.storage.client.ensure_bucket_exists"),
    ):
        first = await run_import(import_root=workspace.parent, dry_run=False, session=sqlite_session)
        await sqlite_session.commit()
        second = await run_import(import_root=workspace.parent, dry_run=False, session=sqlite_session)
    await sqlite_session.commit()

    assert first.documents_created >= 1
    assert second.documents_updated >= 1
    assert second.documents_created == 0

    from sqlalchemy import func, select

    total = await sqlite_session.scalar(select(func.count()).select_from(PortalDocument))
    assert total is not None and total >= 3
