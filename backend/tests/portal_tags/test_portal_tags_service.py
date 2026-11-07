"""Публичный сервис тегов: slug, replace, admin resolve (без дубля HTTP-контракта)."""

from __future__ import annotations

import uuid

import pytest
from app.core.exceptions import ConflictError, NotFoundError
from app.infrastructure.db.models.portal_document import PortalDocument, PortalDocumentTag
from app.schemas.tags import PortalTagCreate, PortalTagUpdate
from app.services.portal_tags import (
    create_tag,
    list_tags,
    replace_document_tags,
    resolve_name_and_slug_for_admin_form,
    update_tag,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.helpers.portal_test_users import user_portal_admin


@pytest.mark.asyncio
async def test_update_tag_color_only(sqlite_session: AsyncSession) -> None:
    t = await create_tag(sqlite_session, PortalTagCreate(name="Цветок", color="#445566"))
    upd = await update_tag(sqlite_session, t.id, PortalTagUpdate(expected_version=1, color="#ABCDEF"))
    assert upd.name == "Цветок"
    assert upd.color == "#ABCDEF"
    assert upd.slug == t.slug


@pytest.mark.asyncio
async def test_update_tag_rename_changes_slug(sqlite_session: AsyncSession) -> None:
    t = await create_tag(sqlite_session, PortalTagCreate(name="СтароеИмя", color="#445566"))
    old_slug = t.slug
    upd = await update_tag(sqlite_session, t.id, PortalTagUpdate(expected_version=1, name="Новое Имя"))
    assert upd.name == "Новое Имя"
    assert upd.slug != old_slug
    assert upd.slug.startswith("novoe-imia")


@pytest.mark.asyncio
async def test_replace_document_tags(sqlite_session: AsyncSession) -> None:
    t1 = await create_tag(sqlite_session, PortalTagCreate(name="Тег1", color="#445566"))
    t2 = await create_tag(sqlite_session, PortalTagCreate(name="Тег2", color="#556677"))
    admin = user_portal_admin()
    doc = PortalDocument(title="Док2", author_sub=admin.sub, body="")
    sqlite_session.add(doc)
    await sqlite_session.commit()
    await sqlite_session.refresh(doc)

    sqlite_session.add(PortalDocumentTag(document_id=doc.id, tag_id=t1.id))
    await sqlite_session.commit()

    await replace_document_tags(sqlite_session, doc.id, [t2.id])
    await sqlite_session.commit()

    rows = (
        await sqlite_session.execute(
            select(PortalDocumentTag.tag_id).where(PortalDocumentTag.document_id == doc.id),
        )
    ).all()
    assert [r[0] for r in rows] == [t2.id]


@pytest.mark.asyncio
async def test_replace_document_tags_empty_list_clears(sqlite_session: AsyncSession) -> None:
    tag = await create_tag(sqlite_session, PortalTagCreate(name="Снять", color="#445566"))
    admin = user_portal_admin()
    doc = PortalDocument(title="ДокClear", author_sub=admin.sub, body="")
    sqlite_session.add(doc)
    await sqlite_session.commit()
    await sqlite_session.refresh(doc)
    sqlite_session.add(PortalDocumentTag(document_id=doc.id, tag_id=tag.id))
    await sqlite_session.commit()

    await replace_document_tags(sqlite_session, doc.id, [])
    await sqlite_session.commit()

    count = await sqlite_session.scalar(
        select(func.count()).select_from(PortalDocumentTag).where(PortalDocumentTag.document_id == doc.id),
    )
    assert count == 0


@pytest.mark.asyncio
async def test_replace_document_tags_dedupes_ids(sqlite_session: AsyncSession) -> None:
    tag = await create_tag(sqlite_session, PortalTagCreate(name="Dedup", color="#445566"))
    admin = user_portal_admin()
    doc = PortalDocument(title="ДокDedup", author_sub=admin.sub, body="")
    sqlite_session.add(doc)
    await sqlite_session.commit()
    await sqlite_session.refresh(doc)

    await replace_document_tags(sqlite_session, doc.id, [tag.id, tag.id])
    await sqlite_session.commit()

    rows = (
        await sqlite_session.execute(
            select(PortalDocumentTag.tag_id).where(PortalDocumentTag.document_id == doc.id),
        )
    ).all()
    assert [r[0] for r in rows] == [tag.id]


@pytest.mark.asyncio
async def test_replace_document_tags_unknown_id_raises(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    doc = PortalDocument(title="Док3", author_sub=admin.sub, body="")
    sqlite_session.add(doc)
    await sqlite_session.commit()
    await sqlite_session.refresh(doc)
    with pytest.raises(NotFoundError, match="Тег не найден"):
        await replace_document_tags(sqlite_session, doc.id, [uuid.uuid4()])


@pytest.mark.asyncio
async def test_resolve_name_and_slug_empty_raw_name(sqlite_session: AsyncSession) -> None:
    display, slug = await resolve_name_and_slug_for_admin_form(sqlite_session, raw_name="   ", exclude_tag_id=None)
    assert display == ""
    assert slug == "tag"


@pytest.mark.asyncio
async def test_resolve_name_and_slug_normal(sqlite_session: AsyncSession) -> None:
    display, slug = await resolve_name_and_slug_for_admin_form(
        sqlite_session,
        raw_name="  Мой тег  ",
        exclude_tag_id=None,
    )
    assert display == "Мой тег"
    assert slug.startswith("moi-teg")


@pytest.mark.asyncio
async def test_resolve_name_and_slug_duplicate_raises_conflict(sqlite_session: AsyncSession) -> None:
    existing = await create_tag(sqlite_session, PortalTagCreate(name="Занято", color="#445566"))
    with pytest.raises(ConflictError, match="уже существует"):
        await resolve_name_and_slug_for_admin_form(
            sqlite_session,
            raw_name="занято",
            exclude_tag_id=None,
        )
    # exclude_tag_id позволяет сохранить своё имя при edit
    display, slug = await resolve_name_and_slug_for_admin_form(
        sqlite_session,
        raw_name="Занято",
        exclude_tag_id=existing.id,
    )
    assert display == "Занято"
    assert slug


@pytest.mark.asyncio
async def test_allocate_unique_slug_suffix_on_collision(sqlite_session: AsyncSession) -> None:
    """Два разных названия с одним и тем же slugify-базовым slug — второй получает суффикс."""
    await create_tag(sqlite_session, PortalTagCreate(name="dup-slug-a", color="#445566"))
    t2 = await create_tag(sqlite_session, PortalTagCreate(name="dup slug a", color="#556677"))
    assert t2.slug == "dup-slug-a-2"


@pytest.mark.asyncio
async def test_list_tags_pagination_respects_name_order(sqlite_session: AsyncSession) -> None:
    await create_tag(sqlite_session, PortalTagCreate(name="aaa-list", color="#445566"))
    await create_tag(sqlite_session, PortalTagCreate(name="bbb-list", color="#556677"))
    page = await list_tags(sqlite_session, skip=1, limit=1)
    assert len(page) == 1
    assert page[0].name == "bbb-list"
