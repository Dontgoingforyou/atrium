"""Интеграционные тесты HTTP API файлов задачи (/portal/tasks/{task_id}/files)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular
from tests.portal_collab.conftest import assert_api_error, async_client_as


@pytest.mark.asyncio
async def test_task_files_crud(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Задача с файлами", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    r = await client_admin.get(f"/api/v1/portal/tasks/{tid}/files")
    assert r.status_code == 200
    assert r.json() == []

    def _fake_presigned_url(_storage_key: str, **kwargs: object) -> str:
        suffix = "attachment" if kwargs.get("force_download") else "inline"
        return f"https://minio.local/sk-x?disposition={suffix}"

    with (
        patch("app.portal_collab.services.task_file.async_upload_file", new_callable=AsyncMock, return_value="sk-x"),
        patch(
            "app.portal_collab.services.task_file.get_presigned_url",
            MagicMock(side_effect=_fake_presigned_url),
        ),
        patch("app.portal_collab.services.task_file.async_delete_object", new_callable=AsyncMock) as del_mock,
    ):
        r = await client_admin.post(
            f"/api/v1/portal/tasks/{tid}/files",
            files={"file": ("report.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")},
        )
        assert r.status_code == 201, r.text
        file = r.json()
        assert file["original_filename"] == "report.pdf"
        assert file["content_type"] == "application/pdf"
        assert file["download_url"] == "https://minio.local/sk-x?disposition=attachment"
        assert file["view_url"] == "https://minio.local/sk-x?disposition=inline"
        fid = file["id"]

        r = await client_admin.get(f"/api/v1/portal/tasks/{tid}/files")
        assert r.status_code == 200
        files = r.json()
        assert len(files) == 1
        assert files[0]["id"] == fid

        r = await client_admin.delete(f"/api/v1/portal/tasks/{tid}/files/{fid}")
        assert r.status_code == 204
    del_mock.assert_called_once_with("sk-x")

    r = await client_admin.get(f"/api/v1/portal/tasks/{tid}/files")
    assert r.json() == []


@pytest.mark.asyncio
async def test_task_file_upload_rejects_disallowed_mime(client_admin: AsyncClient) -> None:
    r = await client_admin.post(
        "/api/v1/portal/tasks",
        json={"title": "Задача с недопустимым файлом", "assignee_sub": "admin-sub"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    r = await client_admin.post(
        f"/api/v1/portal/tasks/{tid}/files",
        files={"file": ("mystery.bin", b"binary content", "application/octet-stream")},
    )
    assert r.status_code == 422, r.text
    assert r.json().get("code") == "validation_error"


@pytest.mark.asyncio
async def test_task_file_delete_forbidden_for_non_uploader(
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    other = user_portal_regular()

    with (
        patch(
            "app.portal_collab.services.task_file.async_upload_file",
            new_callable=AsyncMock,
            return_value="sk-y",
        ),
        patch(
            "app.portal_collab.services.task_file.get_presigned_url",
            return_value="https://minio.local/sk-y?sig=1",
        ),
    ):
        async with async_client_as(sqlite_session, user_portal_admin) as ac:
            r = await ac.post(
                "/api/v1/portal/tasks",
                json={"title": "Файл другого автора", "assignee_sub": other.sub},
            )
            assert r.status_code == 201, r.text
            tid = r.json()["id"]

            r = await ac.post(
                f"/api/v1/portal/tasks/{tid}/files",
                files={"file": ("notes.txt", b"plain text", "text/plain")},
            )
            assert r.status_code == 201, r.text
            fid = r.json()["id"]

    async with async_client_as(sqlite_session, user_portal_regular) as ac:
        r = await ac.delete(f"/api/v1/portal/tasks/{tid}/files/{fid}")
        assert_api_error(r, 403, "forbidden")
