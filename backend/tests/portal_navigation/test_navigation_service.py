"""Правила сборки дерева навигации через публичный get_navigation_tree."""

from __future__ import annotations

import logging
from datetime import timedelta

import pytest
from app.infrastructure.db.models.portal_document import PortalDocument, PortalDocumentShortcut
from app.portal_documents.constants import (
    DEVELOPER_DOCS_ROOT_ID,
    VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG,
    VIRTUAL_DOCS_ROOT_SLUG,
)
from app.portal_navigation.schemas.navigation import NavDocumentBrief, PortalNavNodeTree
from app.portal_navigation.services import navigation as nav_svc
from app.portal_navigation.services.navigation import get_navigation_tree
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_developer, user_portal_regular
from tests.portal_documents.dev_docs_fixtures import ensure_developer_docs_root
from tests.portal_navigation.conftest import add_doc, now_utc


def _general(out: list[PortalNavNodeTree]) -> PortalNavNodeTree:
    return out[0]


def _ids(docs: list[NavDocumentBrief]) -> set[object]:
    return {d.id for d in docs}


@pytest.mark.asyncio
async def test_get_navigation_tree_without_user_returns_empty(
    sqlite_session: AsyncSession,
) -> None:
    out = await get_navigation_tree(sqlite_session, user=None)
    assert out == []


@pytest.mark.asyncio
async def test_get_navigation_tree_parent_child_and_icon_emoji(
    sqlite_session: AsyncSession,
) -> None:
    parent_doc = await add_doc(sqlite_session, title="Корень", icon_emoji="📘")
    child_doc = await add_doc(sqlite_session, title="Дочерняя", parent_document_id=parent_doc.id)
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    assert len(out) == 2
    virtual = _general(out)
    assert virtual.slug == VIRTUAL_DOCS_ROOT_SLUG
    assert virtual.document_count_subtree == 1
    assert len(virtual.documents) == 1
    top = virtual.documents[0]
    assert top.id == parent_doc.id
    assert top.title == "Корень"
    assert top.icon_emoji == "📘"
    assert len(top.children) == 1
    assert top.children[0].id == child_doc.id
    assert top.children[0].title == "Дочерняя"


@pytest.mark.asyncio
async def test_get_navigation_tree_soft_deleted_doc_absent(
    sqlite_session: AsyncSession,
) -> None:
    alive = await add_doc(sqlite_session, title="Живой")
    await add_doc(sqlite_session, title="В корзине", deleted_at=now_utc())
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    titles = {d.title for d in _general(out).documents}
    assert titles == {"Живой"}
    assert alive.id in _ids(_general(out).documents)


@pytest.mark.asyncio
async def test_get_navigation_tree_orphan_when_parent_soft_deleted(
    sqlite_session: AsyncSession,
) -> None:
    parent_doc = await add_doc(sqlite_session, title="Родитель в корзине")
    child_doc = await add_doc(
        sqlite_session,
        title="Активный при удалённом родителе",
        parent_document_id=parent_doc.id,
    )
    parent_doc.deleted_at = now_utc()
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    virtual = _general(out)
    assert virtual.document_count_subtree == 1
    assert len(virtual.documents) == 1
    lone = virtual.documents[0]
    assert lone.id == child_doc.id
    assert lone.children == []


@pytest.mark.asyncio
async def test_get_navigation_tree_sort_order_then_created_at_then_id(
    sqlite_session: AsyncSession,
) -> None:
    t0 = now_utc()
    late = await add_doc(sqlite_session, title="Позже", sort_order=1, created_at=t0)
    early = await add_doc(
        sqlite_session,
        title="Раньше того же sort",
        sort_order=1,
        created_at=t0 - timedelta(hours=1),
    )
    first = await add_doc(sqlite_session, title="Меньший sort", sort_order=0, created_at=t0)
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    titles = [d.title for d in _general(out).documents]
    assert titles == ["Меньший sort", "Позже", "Раньше того же sort"]
    assert [d.id for d in _general(out).documents] == [first.id, late.id, early.id]


@pytest.mark.asyncio
async def test_get_navigation_tree_developer_nested_child_not_root(
    sqlite_session: AsyncSession,
) -> None:
    await ensure_developer_docs_root(sqlite_session)
    child = await add_doc(
        sqlite_session,
        title="Раздел АУ",
        parent_document_id=DEVELOPER_DOCS_ROOT_ID,
        sort_order=1,
    )
    grandchild = await add_doc(
        sqlite_session,
        title="Страница АУ",
        parent_document_id=child.id,
        sort_order=1,
    )
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    assert out[0].slug == VIRTUAL_DOCS_ROOT_SLUG
    assert DEVELOPER_DOCS_ROOT_ID not in _ids(out[0].documents)
    assert out[1].slug == VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG
    assert DEVELOPER_DOCS_ROOT_ID not in _ids(out[1].documents)
    assert len(out[1].documents) == 1
    top = out[1].documents[0]
    assert top.id == child.id
    assert [c.id for c in top.children] == [grandchild.id]


@pytest.mark.asyncio
async def test_get_navigation_tree_includes_shortcuts(
    sqlite_session: AsyncSession,
) -> None:
    source = await add_doc(sqlite_session, title="Источник")
    target = await add_doc(sqlite_session, title="Цель ярлыка", icon_emoji="🔗")
    sqlite_session.add(PortalDocumentShortcut(source_document_id=source.id, target_document_id=target.id))
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    docs = {d.id: d for d in _general(out).documents}
    assert source.id in docs
    assert target.id in docs
    assert len(docs[source.id].shortcuts) == 1
    assert docs[source.id].shortcuts[0].id == target.id
    assert docs[source.id].shortcuts[0].title == "Цель ярлыка"
    assert docs[source.id].shortcuts[0].icon_emoji == "🔗"


@pytest.mark.asyncio
async def test_get_navigation_tree_skips_self_and_child_shortcuts(
    sqlite_session: AsyncSession,
) -> None:
    parent = await add_doc(sqlite_session, title="Родитель")
    child = await add_doc(sqlite_session, title="Ребёнок", parent_document_id=parent.id)
    sqlite_session.add_all(
        [
            PortalDocumentShortcut(source_document_id=parent.id, target_document_id=parent.id),
            PortalDocumentShortcut(source_document_id=parent.id, target_document_id=child.id),
        ]
    )
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    docs = {d.id: d for d in _general(out).documents}
    assert docs[parent.id].shortcuts == []
    assert [c.id for c in docs[parent.id].children] == [child.id]


@pytest.mark.asyncio
async def test_get_navigation_tree_skips_shortcut_to_soft_deleted(
    sqlite_session: AsyncSession,
) -> None:
    source = await add_doc(sqlite_session, title="Источник")
    target = await add_doc(sqlite_session, title="Удалённая цель", deleted_at=now_utc())
    sqlite_session.add(PortalDocumentShortcut(source_document_id=source.id, target_document_id=target.id))
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    docs = {d.id: d for d in _general(out).documents}
    assert source.id in docs
    assert target.id not in docs
    assert docs[source.id].shortcuts == []


@pytest.mark.asyncio
async def test_get_navigation_tree_two_shortcuts_from_one_source(
    sqlite_session: AsyncSession,
) -> None:
    source = await add_doc(sqlite_session, title="Источник")
    a = await add_doc(sqlite_session, title="Цель A")
    b = await add_doc(sqlite_session, title="Цель B")
    sqlite_session.add_all(
        [
            PortalDocumentShortcut(source_document_id=source.id, target_document_id=a.id),
            PortalDocumentShortcut(source_document_id=source.id, target_document_id=b.id),
        ]
    )
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    docs = {d.id: d for d in _general(out).documents}
    assert {s.id for s in docs[source.id].shortcuts} == {a.id, b.id}


@pytest.mark.asyncio
async def test_get_navigation_tree_cross_section_shortcut_visible_for_full_access(
    sqlite_session: AsyncSession,
) -> None:
    await ensure_developer_docs_root(sqlite_session)
    general = await add_doc(sqlite_session, title="Общий")
    developer = await add_doc(
        sqlite_session,
        title="Гайд АУ",
        parent_document_id=DEVELOPER_DOCS_ROOT_ID,
    )
    sqlite_session.add(PortalDocumentShortcut(source_document_id=general.id, target_document_id=developer.id))
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    general_docs = {d.id: d for d in out[0].documents}
    assert general.id in general_docs
    assert len(general_docs[general.id].shortcuts) == 1
    assert general_docs[general.id].shortcuts[0].id == developer.id
    assert general_docs[general.id].shortcuts[0].title == "Гайд АУ"


@pytest.mark.asyncio
async def test_get_navigation_tree_developer_to_general_shortcut_for_full_access(
    sqlite_session: AsyncSession,
) -> None:
    await ensure_developer_docs_root(sqlite_session)
    general = await add_doc(sqlite_session, title="Общий")
    developer = await add_doc(
        sqlite_session,
        title="Гайд АУ",
        parent_document_id=DEVELOPER_DOCS_ROOT_ID,
    )
    sqlite_session.add(PortalDocumentShortcut(source_document_id=developer.id, target_document_id=general.id))
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    dev_docs = {d.id: d for d in out[1].documents}
    assert developer.id in dev_docs
    assert [s.id for s in dev_docs[developer.id].shortcuts] == [general.id]


@pytest.mark.asyncio
async def test_get_navigation_tree_timesheet_hides_shortcut_to_general(
    sqlite_session: AsyncSession,
) -> None:
    await ensure_developer_docs_root(sqlite_session)
    general = await add_doc(sqlite_session, title="Общий скрытый")
    developer = await add_doc(
        sqlite_session,
        title="Только АУ",
        parent_document_id=DEVELOPER_DOCS_ROOT_ID,
    )
    sqlite_session.add(PortalDocumentShortcut(source_document_id=developer.id, target_document_id=general.id))
    await sqlite_session.commit()

    out = await get_navigation_tree(sqlite_session, user=user_portal_developer())
    assert len(out) == 1
    assert out[0].slug == VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG
    docs = {d.id: d for d in out[0].documents}
    assert general.id not in docs
    assert developer.id in docs
    assert docs[developer.id].shortcuts == []


@pytest.mark.asyncio
async def test_get_navigation_tree_cycle_nodes_appear_as_roots(
    sqlite_session: AsyncSession,
    caplog: pytest.LogCaptureFixture,
) -> None:
    a_doc = await add_doc(sqlite_session, title="Цикл A")
    b_doc = await add_doc(sqlite_session, title="Цикл B")
    a_doc.parent_document_id = b_doc.id
    b_doc.parent_document_id = a_doc.id
    await sqlite_session.commit()

    caplog.set_level(logging.WARNING, logger="app.portal_navigation.services.navigation")
    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    ids = _ids(_general(out).documents)
    assert a_doc.id in ids
    assert b_doc.id in ids
    assert any("Цикл parent_document_id" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_get_navigation_tree_self_parent_and_three_cycle_are_roots(
    sqlite_session: AsyncSession,
    caplog: pytest.LogCaptureFixture,
) -> None:
    self_doc = await add_doc(sqlite_session, title="Self")
    self_doc.parent_document_id = self_doc.id
    a_doc = await add_doc(sqlite_session, title="A")
    b_doc = await add_doc(sqlite_session, title="B")
    c_doc = await add_doc(sqlite_session, title="C")
    a_doc.parent_document_id = b_doc.id
    b_doc.parent_document_id = c_doc.id
    c_doc.parent_document_id = a_doc.id
    await sqlite_session.commit()

    caplog.set_level(logging.WARNING, logger="app.portal_navigation.services.navigation")
    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    ids = _ids(_general(out).documents)
    assert {self_doc.id, a_doc.id, b_doc.id, c_doc.id} <= ids
    assert any("Цикл parent_document_id" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_get_navigation_tree_warns_when_doc_cap_hit(
    sqlite_session: AsyncSession,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nav_svc, "_MAX_NAV_TREE_DOCS", 2)
    await add_doc(sqlite_session, title="Кап 1", sort_order=1)
    await add_doc(sqlite_session, title="Кап 2", sort_order=2)
    await add_doc(sqlite_session, title="Кап 3", sort_order=3)
    await sqlite_session.commit()

    caplog.set_level(logging.WARNING, logger="app.portal_navigation.services.navigation")
    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    titles = {d.title for d in _general(out).documents}
    assert len(titles) == 2
    assert "Кап 3" not in titles
    assert any("обрезано по потолку" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_get_navigation_tree_cap_orphan_child_becomes_root(
    sqlite_session: AsyncSession,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nav_svc, "_MAX_NAV_TREE_DOCS", 2)
    parent = await add_doc(sqlite_session, title="Родитель за капом", sort_order=3)
    child = await add_doc(
        sqlite_session,
        title="Ребёнок в капе",
        parent_document_id=parent.id,
        sort_order=1,
    )
    await add_doc(sqlite_session, title="Сосед в капе", sort_order=2)
    await sqlite_session.commit()

    caplog.set_level(logging.WARNING, logger="app.portal_navigation.services.navigation")
    out = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    titles = [d.title for d in _general(out).documents]
    assert "Родитель за капом" not in titles
    assert "Ребёнок в капе" in titles
    assert child.id in _ids(_general(out).documents)
    assert any("обрезано по потолку" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_get_navigation_tree_deleted_developer_root_keeps_children_in_section(
    sqlite_session: AsyncSession,
) -> None:
    await ensure_developer_docs_root(sqlite_session)
    child = await add_doc(
        sqlite_session,
        title="Живой ребёнок АУ",
        parent_document_id=DEVELOPER_DOCS_ROOT_ID,
    )
    general = await add_doc(sqlite_session, title="Общий")
    root = await sqlite_session.get(PortalDocument, DEVELOPER_DOCS_ROOT_ID)
    assert root is not None
    root.deleted_at = now_utc()
    await sqlite_session.commit()

    full = await get_navigation_tree(sqlite_session, user=user_portal_regular())
    assert full[0].slug == VIRTUAL_DOCS_ROOT_SLUG
    assert child.id not in _ids(full[0].documents)
    assert general.id in _ids(full[0].documents)
    assert full[1].slug == VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG
    assert DEVELOPER_DOCS_ROOT_ID not in _ids(full[1].documents)
    assert _ids(full[1].documents) == {child.id}

    timesheet = await get_navigation_tree(sqlite_session, user=user_portal_developer())
    assert len(timesheet) == 1
    assert timesheet[0].slug == VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG
    assert _ids(timesheet[0].documents) == {child.id}
    assert general.id not in _ids(timesheet[0].documents)
