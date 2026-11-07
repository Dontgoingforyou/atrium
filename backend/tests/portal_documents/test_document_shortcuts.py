"""Тесты парсинга и синхронизации ярлыков documentLink в body."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from app.infrastructure.db.models.portal_document import PortalDocumentShortcut
from app.portal_documents.constants import DEVELOPER_DOCS_ROOT_ID
from app.portal_documents.schemas.document import PortalDocumentCreate, PortalDocumentUpdate
from app.portal_documents.services.portal_document_duplicate import duplicate_document_subtree
from app.portal_documents.services.portal_document_mutations import create_document, update_document
from app.portal_documents.services.portal_document_shortcuts import (
    extract_document_link_ids_from_body,
    sync_document_shortcuts,
)
from sqlalchemy import select

from tests.helpers.portal_test_users import user_portal_developer
from tests.portal_documents.dev_docs_fixtures import ensure_developer_docs_root


def test_extract_document_link_ids_from_body_unique_and_valid() -> None:
    tid = uuid.uuid4()
    other = uuid.uuid4()
    body = (
        f'<p>См. <a class="portal-doc-link" href="/documents/{tid}" '
        f'data-document-id="{tid}">Цель</a></p>'
        f'<a data-document-id="{tid}">дубль</a>'
        f'<a data-document-id="{other}">другой</a>'
        '<a data-document-id="not-a-uuid">мусор</a>'
    )
    assert extract_document_link_ids_from_body(body) == [tid, other]


def test_extract_document_link_ids_empty_body() -> None:
    assert extract_document_link_ids_from_body(None) == []
    assert extract_document_link_ids_from_body("") == []
    assert extract_document_link_ids_from_body("<p>без ссылок</p>") == []


@pytest.mark.asyncio
async def test_sync_document_shortcuts_replaces_rows(sqlite_session: Any) -> None:
    source = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="Источник", body="<p/>"),
        author_sub="admin-sub",
    )
    target_a = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="A", body="<p/>"),
        author_sub="admin-sub",
    )
    target_b = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="B", body="<p/>"),
        author_sub="admin-sub",
    )

    body = (
        f'<a class="portal-doc-link" data-document-id="{target_a.id}">A</a>'
        f'<a class="portal-doc-link" data-document-id="{target_b.id}">B</a>'
        f'<a class="portal-doc-link" data-document-id="{source.id}">self</a>'
    )
    await sync_document_shortcuts(sqlite_session, source.id, body)
    await sqlite_session.commit()

    rows = (
        (
            await sqlite_session.execute(
                select(PortalDocumentShortcut.target_document_id).where(
                    PortalDocumentShortcut.source_document_id == source.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert set(rows) == {target_a.id, target_b.id}

    await sync_document_shortcuts(
        sqlite_session,
        source.id,
        f'<a data-document-id="{target_a.id}">только A</a>',
    )
    await sqlite_session.commit()
    rows2 = (
        (
            await sqlite_session.execute(
                select(PortalDocumentShortcut.target_document_id).where(
                    PortalDocumentShortcut.source_document_id == source.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows2 == [target_a.id]


@pytest.mark.asyncio
async def test_update_document_body_syncs_shortcuts(sqlite_session: Any) -> None:
    source = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="Источник", body="<p/>"),
        author_sub="admin-sub",
    )
    target = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="Цель", body="<p/>"),
        author_sub="admin-sub",
    )
    body = f'<a class="portal-doc-link" data-document-id="{target.id}">Цель</a>'
    await update_document(
        sqlite_session,
        source.id,
        PortalDocumentUpdate(expected_version=1, body=body),
        changed_by_sub="admin-sub",
    )
    rows = (
        (
            await sqlite_session.execute(
                select(PortalDocumentShortcut).where(PortalDocumentShortcut.source_document_id == source.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].target_document_id == target.id


@pytest.mark.asyncio
async def test_sync_skips_target_that_is_already_child(sqlite_session: Any) -> None:
    parent = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="Родитель", body="<p/>"),
        author_sub="admin-sub",
    )
    child = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="Ребёнок", parent_document_id=parent.id, body="<p/>"),
        author_sub="admin-sub",
    )
    other = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="Чужой", body="<p/>"),
        author_sub="admin-sub",
    )
    body = f'<a data-document-id="{child.id}">ребёнок</a><a data-document-id="{other.id}">чужой</a>'
    await sync_document_shortcuts(sqlite_session, parent.id, body)
    await sqlite_session.commit()
    rows = (
        (
            await sqlite_session.execute(
                select(PortalDocumentShortcut.target_document_id).where(
                    PortalDocumentShortcut.source_document_id == parent.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows == [other.id]


@pytest.mark.asyncio
async def test_sync_document_shortcuts_drops_target_outside_author_rbac(sqlite_session: Any) -> None:
    """Ярлык — вторичная операция над target: автор без доступа к нему не должен сохранить ссылку.

    `user_portal_developer()` — пользователь с должностью «student» (только
    developer-docs, см. `core/permissions.is_timesheet_only`). Он может сослаться
    на документ внутри developer-docs, но не на документ общего раздела, к
    которому у него нет доступа — даже если тот существует и не удалён.
    """
    await ensure_developer_docs_root(sqlite_session)
    source = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="Источник", parent_document_id=DEVELOPER_DOCS_ROOT_ID, body="<p/>"),
        author_sub="admin-sub",
    )
    allowed_target = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="В developer-docs", parent_document_id=DEVELOPER_DOCS_ROOT_ID, body="<p/>"),
        author_sub="admin-sub",
    )
    forbidden_target = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="Документ общего раздела", body="<p/>"),
        author_sub="admin-sub",
    )

    body = (
        f'<a data-document-id="{allowed_target.id}">разрешён</a>'
        f'<a data-document-id="{forbidden_target.id}">запрещён</a>'
    )
    await sync_document_shortcuts(sqlite_session, source.id, body, author=user_portal_developer())
    await sqlite_session.commit()

    rows = (
        (
            await sqlite_session.execute(
                select(PortalDocumentShortcut.target_document_id).where(
                    PortalDocumentShortcut.source_document_id == source.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows == [allowed_target.id]


@pytest.mark.asyncio
async def test_duplicate_document_subtree_syncs_shortcuts(sqlite_session: Any) -> None:
    """Копия документа с ярлыком documentLink в body должна получить свою строку PortalDocumentShortcut.

    До фикса duplicate_document_subtree копировал body «как есть», но не вызывал
    sync_document_shortcuts — ссылка была видна в теле документа, но не в дереве
    навигации (portal_navigation.services.navigation._attach_shortcuts читает
    только таблицу PortalDocumentShortcut).
    """
    target = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="Цель", body="<p/>"),
        author_sub="admin-sub",
    )
    source = await create_document(
        sqlite_session,
        PortalDocumentCreate(
            title="Источник",
            body=f'<a class="portal-doc-link" data-document-id="{target.id}">Цель</a>',
        ),
        author_sub="admin-sub",
    )

    copy = await duplicate_document_subtree(sqlite_session, source.id, author_sub="admin-sub")

    rows = (
        (
            await sqlite_session.execute(
                select(PortalDocumentShortcut.target_document_id).where(
                    PortalDocumentShortcut.source_document_id == copy.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows == [target.id]


@pytest.mark.asyncio
async def test_duplicate_document_subtree_shortcuts_respect_author_rbac(sqlite_session: Any) -> None:
    """Ярлык копии — вторичная операция над target: недоступный автору target не должен сохраняться."""
    await ensure_developer_docs_root(sqlite_session)
    forbidden_target = await create_document(
        sqlite_session,
        PortalDocumentCreate(title="Документ общего раздела", body="<p/>"),
        author_sub="admin-sub",
    )
    source = await create_document(
        sqlite_session,
        PortalDocumentCreate(
            title="Источник",
            parent_document_id=DEVELOPER_DOCS_ROOT_ID,
            body=f'<a data-document-id="{forbidden_target.id}">запрещён</a>',
        ),
        author_sub="admin-sub",
    )

    copy = await duplicate_document_subtree(
        sqlite_session,
        source.id,
        author_sub="dev-sub",
        author=user_portal_developer(),
    )

    rows = (
        (
            await sqlite_session.execute(
                select(PortalDocumentShortcut.target_document_id).where(
                    PortalDocumentShortcut.source_document_id == copy.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows == []
