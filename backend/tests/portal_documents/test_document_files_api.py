"""HTTP API вложений документов (/portal/documents/.../files)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_portal_admin,
    user_portal_developer,
    user_portal_no_idp_groups,
)
from tests.portal_documents.conftest import DOCS_ADMIN, assert_api_error, async_client_as, create_doc


@pytest.mark.asyncio
async def test_document_files_crud(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Документ с вложением")
    did = doc["id"]

    r = await client_admin.get(f"/api/v1/portal/documents/{did}/files")
    assert r.status_code == 200
    assert r.json() == []

    def _fake_presigned_url(_storage_key: str, **kwargs: object) -> str:
        suffix = "attachment" if kwargs.get("force_download") else "inline"
        return f"https://minio.local/sk-doc?disposition={suffix}"

    with (
        patch(
            "app.portal_documents.services.document_file.async_upload_file",
            new_callable=AsyncMock,
            return_value="sk-doc",
        ),
        patch(
            "app.portal_documents.services.document_file.get_presigned_url",
            MagicMock(side_effect=_fake_presigned_url),
        ),
        patch(
            "app.portal_documents.services.document_file.async_delete_object",
            new_callable=AsyncMock,
        ) as del_mock,
    ):
        r = await client_admin.post(
            f"/api/v1/portal/documents/{did}/files",
            files={"file": ("report.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")},
        )
        assert r.status_code == 201, r.text
        file_json = r.json()
        assert file_json["original_filename"] == "report.pdf"
        assert file_json["content_type"] == "application/pdf"
        assert file_json["download_url"] == "https://minio.local/sk-doc?disposition=attachment"
        assert file_json["view_url"] == "https://minio.local/sk-doc?disposition=inline"
        assert file_json["uploaded_by_sub"]
        assert file_json["created_at"]
        fid = file_json["id"]

        r = await client_admin.get(f"/api/v1/portal/documents/{did}/files")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["id"] == fid

        r = await client_admin.delete(f"/api/v1/portal/documents/{did}/files/{fid}")
        assert r.status_code == 204
    del_mock.assert_called_once_with("sk-doc")

    r = await client_admin.get(f"/api/v1/portal/documents/{did}/files")
    assert r.json() == []


@pytest.mark.asyncio
async def test_document_file_rejects_unsupported_type(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Документ без чужих типов")
    did = doc["id"]

    r = await client_admin.post(
        f"/api/v1/portal/documents/{did}/files",
        files={"file": ("shot.png", b"\x89PNG\r\n\x1a\n" + b"x" * 20, "image/png")},
    )
    assert_api_error(r, 422, "validation_error")
    assert "Допустимы документы" in r.json().get("message", "")


@pytest.mark.asyncio
async def test_document_file_accepts_docx(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Документ с Word")
    did = doc["id"]
    # OOXML — ZIP; magic для этого MIME в словаре нет (pass-through).
    payload = b"PK\x03\x04" + b"fake-docx-body"

    with (
        patch(
            "app.portal_documents.services.document_file.async_upload_file",
            new_callable=AsyncMock,
            return_value="sk-docx",
        ),
        patch(
            "app.portal_documents.services.document_file.get_presigned_url",
            return_value="https://minio.local/sk-docx",
        ),
    ):
        r = await client_admin.post(
            f"/api/v1/portal/documents/{did}/files",
            files={
                "file": (
                    "spec.docx",
                    payload,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["original_filename"] == "spec.docx"
        assert "wordprocessingml" in r.json()["content_type"]


@pytest.mark.asyncio
async def test_document_file_rejects_bad_magic(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="Документ magic")
    did = doc["id"]

    r = await client_admin.post(
        f"/api/v1/portal/documents/{did}/files",
        files={"file": ("fake.pdf", b"not-a-pdf-payload", "application/pdf")},
    )
    assert_api_error(r, 422, "validation_error")


@pytest.mark.asyncio
async def test_document_file_upload_forbidden_for_non_manager(
    sqlite_session: object,
    patch_oidc_settings: object,
) -> None:
    assert isinstance(sqlite_session, AsyncSession)

    async with async_client_as(sqlite_session, user_portal_admin) as ac:
        doc = await create_doc(ac, title="Файлы только менеджерам")
        did = doc["id"]

    async with async_client_as(sqlite_session, user_portal_no_idp_groups) as ac:
        r = await ac.post(
            f"/api/v1/portal/documents/{did}/files",
            files={"file": ("report.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
        assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_document_files_list_forbidden_outside_developer_docs(
    sqlite_session: object,
    patch_oidc_settings: object,
) -> None:
    """Timesheet-only (developer) не читает вложения обычного документа."""
    assert isinstance(sqlite_session, AsyncSession)

    async with async_client_as(sqlite_session, user_portal_admin) as ac:
        doc = await create_doc(ac, title="Секретный с файлами")
        did = doc["id"]

    async with async_client_as(sqlite_session, user_portal_developer) as ac:
        r = await ac.get(f"/api/v1/portal/documents/{did}/files")
        assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_document_file_delete_forbidden_for_non_uploader_non_manager(
    sqlite_session: object,
    patch_oidc_settings: object,
) -> None:
    assert isinstance(sqlite_session, AsyncSession)

    with (
        patch(
            "app.portal_documents.services.document_file.async_upload_file",
            new_callable=AsyncMock,
            return_value="sk-del-forbid",
        ),
        patch(
            "app.portal_documents.services.document_file.get_presigned_url",
            return_value="https://minio.local/sk-del-forbid",
        ),
    ):
        async with async_client_as(sqlite_session, user_portal_admin) as ac:
            doc = await create_doc(ac, title="Чужой файл")
            did = doc["id"]
            r = await ac.post(
                f"/api/v1/portal/documents/{did}/files",
                files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")},
            )
            assert r.status_code == 201, r.text
            fid = r.json()["id"]

    async with async_client_as(sqlite_session, user_portal_no_idp_groups) as ac:
        r = await ac.delete(f"/api/v1/portal/documents/{did}/files/{fid}")
        assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_purge_document_deletes_file_storage(client_admin: AsyncClient) -> None:
    doc = await create_doc(client_admin, title="К purge с файлом")
    did = doc["id"]

    with (
        patch(
            "app.portal_documents.services.document_file.async_upload_file",
            new_callable=AsyncMock,
            return_value="sk-purge",
        ),
        patch(
            "app.portal_documents.services.document_file.get_presigned_url",
            return_value="https://minio.local/sk-purge",
        ),
    ):
        r = await client_admin.post(
            f"/api/v1/portal/documents/{did}/files",
            files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")},
        )
        assert r.status_code == 201, r.text

    with patch(
        "app.portal_documents.services.document_file.async_delete_objects",
        new_callable=AsyncMock,
    ) as del_batch:
        r = await client_admin.delete(f"{DOCS_ADMIN}/{did}")
        assert r.status_code == 204, r.text
        r = await client_admin.delete(f"{DOCS_ADMIN}/{did}/purge")
        assert r.status_code == 204, r.text
        del_batch.assert_called()
        keys = del_batch.call_args[0][0]
        assert "sk-purge" in keys
