"""HTTP-контракт комментариев к документам: CRUD, IDOR, media."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_regular, user_portal_user_b
from tests.portal_documents.conftest import DOCS_API, as_user, assert_api_error, create_doc

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


async def _post_comment(client: AsyncClient, doc_id: str, **kwargs: object) -> dict:
    data = {"body": "Тестовый комментарий", **kwargs}
    r = await client.post(f"{DOCS_API}/documents/{doc_id}/comments", json=data)
    assert r.status_code == 201, r.text
    return r.json()


async def test_list_and_create_comments(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin)
    r = await client_admin.get(f"{DOCS_API}/documents/{doc['id']}/comments")
    assert r.status_code == 200
    assert r.json() == []

    created = await _post_comment(client_admin, doc["id"], body="Мой комментарий", mentions=["user-sub"])
    assert created["body"] == "Мой комментарий"
    assert created["author_sub"] == "admin-sub"
    assert created["document_id"] == doc["id"]
    assert created["parent_id"] is None
    assert "user-sub" in created["mentions"]

    listed = await client_admin.get(f"{DOCS_API}/documents/{doc['id']}/comments")
    assert any(c["body"] == "Мой комментарий" for c in listed.json())


async def test_create_comment_requires_body_or_media(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin)
    r = await client_admin.post(
        f"{DOCS_API}/documents/{doc['id']}/comments",
        json={"body": "", "media_ids": []},
    )
    assert r.status_code == 422
    assert "detail" in r.json()


async def test_reply_and_unknown_parent(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin)
    parent = await _post_comment(client_admin, doc["id"], body="Корень")
    r = await client_admin.post(
        f"{DOCS_API}/documents/{doc['id']}/comments",
        json={"body": "Ответ", "parent_id": parent["id"]},
    )
    assert r.status_code == 201
    assert r.json()["parent_id"] == parent["id"]

    r = await client_admin.post(
        f"{DOCS_API}/documents/{doc['id']}/comments",
        json={"body": "Ответ", "parent_id": str(uuid.uuid4())},
    )
    assert_api_error(r, 404, "not_found")


async def test_update_and_delete_own_comment(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin)
    comment = await _post_comment(client_admin, doc["id"], body="Исходный")
    r = await client_admin.patch(
        f"{DOCS_API}/documents/{doc['id']}/comments/{comment['id']}",
        json={"expected_version": 1, "body": "Обновлённый"},
    )
    assert r.status_code == 200
    assert r.json()["body"] == "Обновлённый"

    r = await client_admin.delete(f"{DOCS_API}/documents/{doc['id']}/comments/{comment['id']}")
    assert r.status_code == 204
    listed = await client_admin.get(f"{DOCS_API}/documents/{doc['id']}/comments")
    assert all(c["id"] != comment["id"] for c in listed.json())


async def test_comment_unknown_and_trashed_document(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Скоро в корзине")
    missing = str(uuid.uuid4())
    r = await client_admin.patch(
        f"{DOCS_API}/documents/{doc['id']}/comments/{missing}",
        json={"expected_version": 1, "body": "Нет"},
    )
    assert_api_error(r, 404, "not_found")
    r = await client_admin.delete(f"{DOCS_API}/documents/{doc['id']}/comments/{missing}")
    assert_api_error(r, 404, "not_found")

    await client_admin.delete(f"/api/v1/admin/portal-documents/{doc['id']}")
    r = await client_admin.get(f"{DOCS_API}/documents/{doc['id']}/comments")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.post(f"{DOCS_API}/documents/{doc['id']}/comments", json={"body": "нельзя"})
    assert_api_error(r, 404, "not_found")


async def test_comment_id_cross_document_idor(client_admin: AsyncClient) -> None:
    a = await create_doc(client_admin, title="Документ A")
    b = await create_doc(client_admin, title="Документ B")
    comment = await _post_comment(client_admin, b["id"], body="чужой")
    r = await client_admin.patch(
        f"{DOCS_API}/documents/{a['id']}/comments/{comment['id']}",
        json={"expected_version": 1, "body": "подмена"},
    )
    assert_api_error(r, 404, "not_found")
    r = await client_admin.delete(f"{DOCS_API}/documents/{a['id']}/comments/{comment['id']}")
    assert_api_error(r, 404, "not_found")

    r = await client_admin.post(
        f"{DOCS_API}/documents/{a['id']}/comments",
        json={"body": "ответ", "parent_id": comment["id"]},
    )
    assert_api_error(r, 404, "not_found")


async def test_comment_patch_delete_author_or_admin(
    client_admin: AsyncClient,
) -> None:
    doc = await create_doc(client_admin, title="RBAC комментария")
    with as_user(user_portal_regular):
        comment = await _post_comment(client_admin, doc["id"], body="моё")

    with as_user(user_portal_user_b):
        r = await client_admin.patch(
            f"{DOCS_API}/documents/{doc['id']}/comments/{comment['id']}",
            json={"expected_version": 1, "body": "взлом"},
        )
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.delete(f"{DOCS_API}/documents/{doc['id']}/comments/{comment['id']}")
        assert_api_error(r, 403, "forbidden")

    with as_user(user_portal_regular):
        r = await client_admin.patch(
            f"{DOCS_API}/documents/{doc['id']}/comments/{comment['id']}",
            json={"expected_version": comment["version"], "body": "автор правил"},
        )
        assert r.status_code == 200
        assert r.json()["body"] == "автор правил"
        version = r.json()["version"]

    r = await client_admin.patch(
        f"{DOCS_API}/documents/{doc['id']}/comments/{comment['id']}",
        json={"expected_version": version, "body": "админ правил"},
    )
    assert r.status_code == 200
    assert r.json()["body"] == "админ правил"
    r = await client_admin.delete(f"{DOCS_API}/documents/{doc['id']}/comments/{comment['id']}")
    assert r.status_code == 204


async def test_comment_media_ids_validation(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    doc_a = await create_doc(client_admin, title="Медиа A")
    doc_b = await create_doc(client_admin, title="Медиа B")
    media_id = uuid.uuid4()
    sqlite_session.add(
        PortalRichMedia(
            id=media_id,
            storage_key="test-key",
            content_type="image/png",
            original_filename="a.png",
            file_size=100,
            uploader_sub="admin-sub",
            document_id=uuid.UUID(doc_b["id"]),
            created_at=datetime.now(UTC),
        )
    )
    await sqlite_session.commit()

    r = await client_admin.post(
        f"{DOCS_API}/documents/{doc_a['id']}/comments",
        json={"body": "", "media_ids": [str(media_id)]},
    )
    assert_api_error(r, 403, "forbidden")

    r = await client_admin.post(
        f"{DOCS_API}/documents/{doc_a['id']}/comments",
        json={"body": "", "media_ids": [str(uuid.uuid4())]},
    )
    assert_api_error(r, 404, "not_found")

    own_id = uuid.uuid4()
    sqlite_session.add(
        PortalRichMedia(
            id=own_id,
            storage_key="own-key",
            content_type="image/png",
            original_filename="own.png",
            file_size=100,
            uploader_sub="admin-sub",
            document_id=uuid.UUID(doc_a["id"]),
            created_at=datetime.now(UTC),
        )
    )
    await sqlite_session.commit()
    with patch("app.services.rich_media.build_download_url", return_value="https://minio.local/x"):
        r = await client_admin.post(
            f"{DOCS_API}/documents/{doc_a['id']}/comments",
            json={"body": "", "media_ids": [str(own_id)]},
        )
    assert r.status_code == 201, r.text
    assert r.json()["media"][0]["id"] == str(own_id)


async def test_upload_comment_rich_media(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin)
    with (
        patch("app.services.rich_media_upload.async_upload_stream_to_key", new_callable=AsyncMock),
        patch("app.services.rich_media.get_presigned_url", return_value="https://minio.local/img"),
    ):
        r = await client_admin.post(
            f"{DOCS_API}/documents/{doc['id']}/comments/rich-media",
            files={"file": ("shot.png", io.BytesIO(_PNG), "image/png")},
        )
    assert r.status_code == 201, r.text
    assert r.json()["id"]
    assert r.json()["content_type"] == "image/png"
