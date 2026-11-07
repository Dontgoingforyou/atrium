"""RBAC / IDOR / 401 документов: матрица auth, timesheet, developer-docs, purge."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import Settings
from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.constants import (
    DEVELOPER_DOCS_ROOT_ID,
    VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG,
    VIRTUAL_DOCS_ROOT_SLUG,
)
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_au_specialist_with_outstaff,
    user_manager_students_outstaff,
    user_portal_developer,
    user_portal_no_idp_groups,
    user_portal_regular,
)
from tests.portal_documents.conftest import (
    DOCS_ADMIN,
    DOCS_API,
    as_user,
    assert_api_error,
    async_client_as,
    create_doc,
)
from tests.portal_documents.dev_docs_fixtures import ensure_developer_docs_root

_AUTH_UUID = "00000000-0000-0000-0000-000000000001"
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _file_kw() -> dict[str, object]:
    return {"files": {"file": ("pic.png", _PNG, "image/png")}}


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", f"{DOCS_API}/documents", {}),
        ("GET", f"{DOCS_API}/documents/{_AUTH_UUID}", {}),
        ("GET", f"{DOCS_API}/documents/{_AUTH_UUID}/related", {}),
        ("GET", f"{DOCS_API}/documents/{_AUTH_UUID}/history", {}),
        ("GET", f"{DOCS_API}/documents/{_AUTH_UUID}/children", {}),
        ("POST", f"{DOCS_API}/documents/{_AUTH_UUID}/rich-media", _file_kw()),
        ("GET", f"{DOCS_API}/documents/{_AUTH_UUID}/comments", {}),
        ("POST", f"{DOCS_API}/documents/{_AUTH_UUID}/comments", {"json": {"body": "hi"}}),
        (
            "PATCH",
            f"{DOCS_API}/documents/{_AUTH_UUID}/comments/{_AUTH_UUID}",
            {"json": {"expected_version": 1, "body": "x"}},
        ),
        ("DELETE", f"{DOCS_API}/documents/{_AUTH_UUID}/comments/{_AUTH_UUID}", {}),
        ("POST", f"{DOCS_API}/documents/{_AUTH_UUID}/comments/rich-media", _file_kw()),
        ("POST", f"{DOCS_API}/documents/{_AUTH_UUID}/comments/ws-ticket", {}),
        ("POST", f"{DOCS_API}/documents/{_AUTH_UUID}/content-ws-ticket", {}),
        ("POST", f"{DOCS_API}/navigation-tree-ws-ticket", {}),
        ("GET", f"{DOCS_ADMIN}/trash", {}),
        ("POST", DOCS_ADMIN, {"json": {"expected_version": 1, "title": "X"}}),
        ("POST", f"{DOCS_ADMIN}/quick-create", {"json": {}}),
        ("PATCH", f"{DOCS_ADMIN}/{_AUTH_UUID}", {"json": {"expected_version": 1, "title": "X"}}),
        ("PATCH", f"{DOCS_ADMIN}/{_AUTH_UUID}/reorder", {"json": {"after_id": _AUTH_UUID}}),
        ("POST", f"{DOCS_ADMIN}/{_AUTH_UUID}/restore", {}),
        ("POST", f"{DOCS_ADMIN}/{_AUTH_UUID}/duplicate", {}),
        ("DELETE", f"{DOCS_ADMIN}/{_AUTH_UUID}", {}),
        ("DELETE", f"{DOCS_ADMIN}/{_AUTH_UUID}/purge", {}),
    ],
)
async def test_document_endpoints_require_auth(
    client_sqlite_only: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_sqlite_only.request(method, path, **kwargs)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", f"{DOCS_ADMIN}/trash", {}),
        ("POST", DOCS_ADMIN, {"json": {"expected_version": 1, "title": "X"}}),
        ("POST", f"{DOCS_ADMIN}/quick-create", {"json": {}}),
        ("PATCH", f"{DOCS_ADMIN}/{_AUTH_UUID}", {"json": {"expected_version": 1, "title": "X"}}),
        ("PATCH", f"{DOCS_ADMIN}/{_AUTH_UUID}/reorder", {"json": {"after_id": _AUTH_UUID}}),
        ("POST", f"{DOCS_ADMIN}/{_AUTH_UUID}/restore", {}),
        ("POST", f"{DOCS_ADMIN}/{_AUTH_UUID}/duplicate", {}),
        ("DELETE", f"{DOCS_ADMIN}/{_AUTH_UUID}", {}),
        ("DELETE", f"{DOCS_ADMIN}/{_AUTH_UUID}/purge", {}),
    ],
)
async def test_timesheet_forbidden_on_admin_document_routes(
    client_developer: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_developer.request(method, path, **kwargs)
    assert_api_error(r, 403, "forbidden")


async def test_timesheet_cannot_read_general_document(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Общий секрет")
    did = doc["id"]
    with as_user(user_portal_developer):
        r = await client_admin.get(f"{DOCS_API}/documents/{did}")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.get(f"{DOCS_API}/documents/{did}/history")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.get(f"{DOCS_API}/documents/{did}/related")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.get(f"{DOCS_API}/documents/{did}/children")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.get(f"{DOCS_API}/documents/{did}/comments")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.post(f"{DOCS_API}/documents/{did}/comments", json={"body": "нельзя"})
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.post(f"{DOCS_API}/documents/{did}/content-ws-ticket")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.post(f"{DOCS_API}/documents/{did}/comments/ws-ticket")
        assert_api_error(r, 403, "forbidden")


async def test_unknown_document_is_404_not_403(client_admin: AsyncClient) -> None:
    missing = _AUTH_UUID
    r = await client_admin.get(f"{DOCS_API}/documents/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{DOCS_API}/documents/{missing}/history")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{DOCS_API}/documents/{missing}/related")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{DOCS_API}/documents/{missing}/children")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{DOCS_API}/documents/{missing}/comments")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.post(f"{DOCS_API}/documents/{missing}/comments/ws-ticket")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.post(f"{DOCS_API}/documents/{missing}/content-ws-ticket")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.patch(f"{DOCS_ADMIN}/{missing}", json={"expected_version": 1, "title": "X"})
    assert_api_error(r, 404, "not_found")
    r = await client_admin.post(f"{DOCS_ADMIN}/{missing}/restore")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.post(f"{DOCS_ADMIN}/{missing}/duplicate")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.delete(f"{DOCS_ADMIN}/{missing}")
    assert_api_error(r, 404, "not_found")


async def test_developer_docs_readable_for_timesheet(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    await ensure_developer_docs_root(sqlite_session)
    child = PortalDocument(
        id=uuid.uuid4(),
        title="Гайд",
        author_sub="admin-sub",
        body="",
        parent_document_id=DEVELOPER_DOCS_ROOT_ID,
        sort_order=1,
    )
    general = PortalDocument(
        id=uuid.uuid4(),
        title="Секретный документ",
        author_sub="admin-sub",
        body="secret",
        sort_order=2,
    )
    sqlite_session.add_all([child, general])
    await sqlite_session.commit()

    async with async_client_as(sqlite_session, user_portal_developer) as ac:
        r = await ac.get(f"{DOCS_API}/documents")
        assert r.status_code == 200, r.text
        ids = {item["id"] for item in r.json()["items"]}
        assert str(DEVELOPER_DOCS_ROOT_ID) in ids
        assert str(child.id) in ids
        assert str(general.id) not in ids

        r = await ac.get(f"{DOCS_API}/documents/{DEVELOPER_DOCS_ROOT_ID}")
        assert r.status_code == 200, r.text
        r = await ac.get(f"{DOCS_API}/documents/{child.id}")
        assert r.status_code == 200, r.text
        r = await ac.post(f"{DOCS_API}/documents/{child.id}/comments", json={"body": "вопрос"})
        assert r.status_code == 201, r.text
        assert r.json()["body"] == "вопрос"
        r = await ac.post(f"{DOCS_API}/documents/{child.id}/content-ws-ticket")
        assert r.status_code == 201, r.text
        r = await ac.post(f"{DOCS_API}/navigation-tree-ws-ticket")
        assert r.status_code == 201, r.text

        r = await ac.get(f"{DOCS_API}/documents/{general.id}")
        assert_api_error(r, 403, "forbidden")


async def test_au_specialist_sees_only_developer_docs(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    await ensure_developer_docs_root(sqlite_session)
    other = PortalDocument(
        id=uuid.uuid4(),
        title="Чужой",
        author_sub="admin-sub",
        body="x",
        sort_order=2,
    )
    sqlite_session.add(other)
    await sqlite_session.commit()

    async with async_client_as(sqlite_session, user_au_specialist_with_outstaff) as ac:
        r = await ac.get(f"{DOCS_API}/documents")
        assert r.status_code == 200, r.text
        ids = {item["id"] for item in r.json()["items"]}
        assert str(DEVELOPER_DOCS_ROOT_ID) in ids
        assert str(other.id) not in ids
        r = await ac.get(f"{DOCS_API}/documents/{other.id}")
        assert_api_error(r, 403, "forbidden")
        r = await ac.post(
            DOCS_ADMIN,
            json={"title": "Новый", "body": "", "parent_document_id": str(DEVELOPER_DOCS_ROOT_ID)},
        )
        assert_api_error(r, 403, "forbidden")


async def test_manager_can_mutate_but_cannot_purge(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Для менеджера")
    did = doc["id"]
    with as_user(user_portal_regular):
        r = await client_admin.patch(f"{DOCS_ADMIN}/{did}", json={"expected_version": 1, "title": "Менеджер правил"})
        assert r.status_code == 200, r.text
        assert r.json()["title"] == "Менеджер правил"
        r = await client_admin.post(f"{DOCS_ADMIN}/{did}/duplicate")
        assert r.status_code == 201, r.text
        r = await client_admin.get(f"{DOCS_ADMIN}/trash")
        assert r.status_code == 200, r.text
        r = await client_admin.delete(f"{DOCS_ADMIN}/{did}")
        assert r.status_code == 204, r.text
        r = await client_admin.post(f"{DOCS_ADMIN}/{did}/restore")
        assert r.status_code == 200, r.text
        r = await client_admin.delete(f"{DOCS_ADMIN}/{did}/purge")
        assert_api_error(r, 403, "forbidden")


async def test_non_manager_cannot_mutate_documents(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Защищённый")
    did = doc["id"]
    with as_user(user_portal_no_idp_groups):
        r = await client_admin.post(DOCS_ADMIN, json={"expected_version": 1, "title": "X"})
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.post(f"{DOCS_ADMIN}/quick-create", json={})
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.patch(f"{DOCS_ADMIN}/{did}", json={"expected_version": 1, "title": "Хакер"})
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.delete(f"{DOCS_ADMIN}/{did}")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.post(f"{DOCS_ADMIN}/{did}/duplicate")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.get(f"{DOCS_ADMIN}/trash")
        assert_api_error(r, 403, "forbidden")


async def test_reader_cannot_upload_document_rich_media(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Картинка в теле")
    with (
        as_user(user_portal_no_idp_groups),
        patch("app.services.rich_media_upload.async_upload_stream_to_key", new_callable=AsyncMock),
        patch("app.services.rich_media.get_presigned_url", return_value="https://minio.local/img"),
    ):
        r = await client_admin.post(
            f"{DOCS_API}/documents/{doc['id']}/rich-media",
            files={"file": ("pic.png", _PNG, "image/png")},
        )
    assert_api_error(r, 403, "forbidden")


async def test_timesheet_cannot_upload_comment_rich_media(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    await ensure_developer_docs_root(sqlite_session)
    child = PortalDocument(
        id=uuid.uuid4(),
        title="Гайд с медиа",
        author_sub="admin-sub",
        body="",
        parent_document_id=DEVELOPER_DOCS_ROOT_ID,
        sort_order=1,
    )
    sqlite_session.add(child)
    await sqlite_session.commit()

    async with async_client_as(sqlite_session, user_portal_developer) as ac:
        with (
            patch("app.services.rich_media_upload.async_upload_stream_to_key", new_callable=AsyncMock),
            patch("app.services.rich_media.get_presigned_url", return_value="https://minio.local/img"),
        ):
            r = await ac.post(
                f"{DOCS_API}/documents/{child.id}/comments/rich-media",
                files={"file": ("pic.png", _PNG, "image/png")},
            )
        assert_api_error(r, 403, "forbidden")


async def test_au_specialist_rich_media_object_rbac(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    from app.infrastructure.db.models.portal_rich_media import PortalRichMedia

    await ensure_developer_docs_root(sqlite_session)
    child = PortalDocument(
        id=uuid.uuid4(),
        title="Гайд с картинкой",
        author_sub="admin-sub",
        body="",
        parent_document_id=DEVELOPER_DOCS_ROOT_ID,
        sort_order=1,
    )
    general = PortalDocument(
        id=uuid.uuid4(),
        title="Общий",
        author_sub="admin-sub",
        body="",
        sort_order=2,
    )
    media_ok = PortalRichMedia(
        storage_key=f"rich-media/{uuid.uuid4()}/img.png",
        content_type="image/png",
        original_filename="img.png",
        file_size=32,
        uploader_sub="admin-sub",
        document_id=child.id,
    )
    media_denied = PortalRichMedia(
        storage_key=f"rich-media/{uuid.uuid4()}/img.png",
        content_type="image/png",
        original_filename="img.png",
        file_size=32,
        uploader_sub="admin-sub",
        document_id=general.id,
    )
    sqlite_session.add_all([child, general, media_ok, media_denied])
    await sqlite_session.commit()

    async with async_client_as(sqlite_session, user_au_specialist_with_outstaff) as ac:
        with patch("app.services.rich_media.get_presigned_url", return_value="https://minio.local/dev"):
            r = await ac.get(f"{DOCS_API}/rich-media/{media_ok.id}")
            assert r.status_code == 200, r.text
            assert r.json()["id"] == str(media_ok.id)
            r = await ac.get(f"{DOCS_API}/rich-media/{media_denied.id}")
            assert_api_error(r, 403, "forbidden")


async def test_get_document_returns_virtual_nav_slug(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    await ensure_developer_docs_root(sqlite_session)
    general = PortalDocument(
        id=uuid.uuid4(),
        title="Общий",
        author_sub="admin-sub",
        body="",
        sort_order=1,
    )
    child = PortalDocument(
        id=uuid.uuid4(),
        title="Dev child",
        author_sub="admin-sub",
        body="",
        parent_document_id=DEVELOPER_DOCS_ROOT_ID,
        sort_order=1,
    )
    sqlite_session.add_all([general, child])
    await sqlite_session.commit()

    async with async_client_as(sqlite_session, user_manager_students_outstaff) as ac:
        r_dev = await ac.get(f"{DOCS_API}/documents/{child.id}")
        assert r_dev.status_code == 200, r_dev.text
        assert r_dev.json()["nav_node_slug"] == VIRTUAL_DEVELOPER_DOCS_ROOT_SLUG
        r_gen = await ac.get(f"{DOCS_API}/documents/{general.id}")
        assert r_gen.status_code == 200, r_gen.text
        assert r_gen.json()["nav_node_slug"] == VIRTUAL_DOCS_ROOT_SLUG
        listed = await ac.get(f"{DOCS_API}/documents")
        assert listed.status_code == 200, listed.text
        listed_ids = {item["id"] for item in listed.json()["items"]}
        assert str(general.id) in listed_ids
        assert str(child.id) in listed_ids
