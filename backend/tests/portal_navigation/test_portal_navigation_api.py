"""HTTP-контракт дерева навигации: 401, RBAC секций, document_count_subtree."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from app.portal_documents.constants import (
    DEVELOPER_DOCS_ROOT_ID,
    VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG,
    VIRTUAL_DOCS_ROOT_SLUG,
)
from app.schemas.auth import UserPublic
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_au_specialist_with_outstaff,
    user_manager_students_outstaff,
    user_outstaff_not_manager,
    user_portal_admin,
    user_portal_manager,
    user_portal_no_idp_groups,
    user_portal_regular,
)
from tests.portal_documents.dev_docs_fixtures import ensure_developer_docs_root
from tests.portal_navigation.conftest import NAV_API, add_doc, as_user, assert_api_error


def _slugs(tree: list[dict[str, object]]) -> list[str]:
    return [str(node["slug"]) for node in tree]


async def test_navigation_tree_requires_auth(client_sqlite_only: AsyncClient) -> None:
    r = await client_sqlite_only.get(NAV_API)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize(
    "user_factory",
    [
        user_portal_admin,
        user_portal_regular,
        user_portal_manager,
        user_portal_no_idp_groups,
        user_outstaff_not_manager,
    ],
)
async def test_navigation_tree_full_access_two_empty_sections(
    client_admin: AsyncClient,
    user_factory: Callable[[], UserPublic],
) -> None:
    with as_user(user_factory):
        r = await client_admin.get(NAV_API)
    assert r.status_code == 200, r.text
    tree = r.json()
    assert _slugs(tree) == [VIRTUAL_DOCS_ROOT_SLUG, VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG]
    assert tree[0]["title"] == "Документы"
    assert tree[0]["sort_order"] == 0
    assert tree[0]["children"] == []
    assert tree[0]["documents"] == []
    assert tree[0]["document_count_subtree"] == 0
    assert tree[1]["title"] == "Документы для разработчиков"
    assert tree[1]["sort_order"] == 10
    assert tree[1]["children"] == []
    assert tree[1]["documents"] == []


async def test_navigation_tree_manager_students_outstaff_two_sections(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await ensure_developer_docs_root(sqlite_session)
    general = await add_doc(sqlite_session, title="Общий корень", author_sub="admin-sub", sort_order=1)
    await sqlite_session.commit()

    with as_user(user_manager_students_outstaff):
        r = await client_admin.get(NAV_API)
    assert r.status_code == 200, r.text
    tree = r.json()
    assert _slugs(tree) == [VIRTUAL_DOCS_ROOT_SLUG, VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG]
    general_ids = {d["id"] for d in tree[0]["documents"]}
    assert str(general.id) in general_ids
    assert str(DEVELOPER_DOCS_ROOT_ID) not in general_ids


@pytest.mark.parametrize(
    "user_factory",
    [None, user_au_specialist_with_outstaff],
)
async def test_navigation_tree_timesheet_only_developer_section(
    client_developer: AsyncClient,
    sqlite_session: AsyncSession,
    user_factory: Callable[[], UserPublic] | None,
) -> None:
    await ensure_developer_docs_root(sqlite_session)
    child = await add_doc(
        sqlite_session,
        title="Гайд для АУ",
        author_sub="admin-sub",
        parent_document_id=DEVELOPER_DOCS_ROOT_ID,
        sort_order=1,
    )
    general = await add_doc(
        sqlite_session,
        title="Общие документы",
        author_sub="admin-sub",
        sort_order=5,
    )
    await sqlite_session.commit()

    if user_factory is None:
        r = await client_developer.get(NAV_API)
    else:
        with as_user(user_factory):
            r = await client_developer.get(NAV_API)
    assert r.status_code == 200, r.text
    tree = r.json()
    assert _slugs(tree) == [VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG]
    docs = tree[0]["documents"]
    assert {d["id"] for d in docs} == {str(child.id)}
    assert {d["title"] for d in docs} == {"Гайд для АУ"}
    assert str(general.id) not in {d["id"] for d in docs}


async def test_navigation_tree_document_count_subtree_is_section_roots(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    d_root = await add_doc(sqlite_session, title="Root in obuchenie")
    d2 = await add_doc(sqlite_session, title="R1 onboarding")
    d3 = await add_doc(sqlite_session, title="R2 onboarding")
    child = await add_doc(sqlite_session, title="Child of R1", parent_document_id=d2.id)
    await sqlite_session.commit()

    r = await client_user.get(NAV_API)
    assert r.status_code == 200, r.text
    tree = r.json()
    assert _slugs(tree) == [VIRTUAL_DOCS_ROOT_SLUG, VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG]
    virtual_root = tree[0]
    assert virtual_root["document_count_subtree"] == 3
    doc_ids = {d["id"] for d in virtual_root["documents"]}
    assert {str(d_root.id), str(d2.id), str(d3.id)} <= doc_ids
    assert str(child.id) not in doc_ids
    d2_node = next(d for d in virtual_root["documents"] if d["id"] == str(d2.id))
    assert len(d2_node["children"]) == 1
    assert d2_node["children"][0]["id"] == str(child.id)
