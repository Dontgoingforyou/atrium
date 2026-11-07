"""Прямые вызовы сервиса portal_collab.services.task_file (список/загрузка/удаление файлов задачи)."""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.portal_collab.schemas.task import PortalTaskCreate
from app.portal_collab.services import task as task_svc
from app.portal_collab.services import task_file as file_svc
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular


@pytest.mark.asyncio
async def test_task_file_service_list_upload_delete(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Сервис файлов", assignee_sub="admin-sub"),
    )
    assert await file_svc.list_files(sqlite_session, admin, task.id) == []

    with patch("app.portal_collab.services.task_file.async_upload_file", new_callable=AsyncMock, return_value="sk-1"):
        file = await file_svc.upload_file(
            sqlite_session,
            admin,
            task.id,
            file_data=io.BytesIO(b"%PDF-1.4 test"),
            file_size=13,
            content_type="application/pdf",
            original_filename="report.pdf",
        )
    assert file.original_filename == "report.pdf"
    assert file.content_type == "application/pdf"

    rows = await file_svc.list_files(sqlite_session, admin, task.id)
    assert len(rows) == 1
    assert rows[0].id == file.id

    with patch("app.portal_collab.services.task_file.async_delete_object", new_callable=AsyncMock) as del_mock:
        await file_svc.delete_file(sqlite_session, admin, task.id, file.id)
    del_mock.assert_called_once_with("sk-1")
    assert await file_svc.list_files(sqlite_session, admin, task.id) == []


@pytest.mark.asyncio
async def test_task_file_delete_forbidden_for_non_uploader_non_admin(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    user = user_portal_regular()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Чужой файл", assignee_sub=user.sub),
    )
    with patch("app.portal_collab.services.task_file.async_upload_file", new_callable=AsyncMock, return_value="sk-2"):
        file = await file_svc.upload_file(
            sqlite_session,
            admin,
            task.id,
            file_data=io.BytesIO(b"plain text"),
            file_size=10,
            content_type="text/plain",
            original_filename="notes.txt",
        )
    with pytest.raises(ForbiddenError, match="загрузивший"):
        await file_svc.delete_file(sqlite_session, user, task.id, file.id)


@pytest.mark.asyncio
async def test_task_file_delete_not_found(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Нет файла", assignee_sub="admin-sub"),
    )
    with pytest.raises(NotFoundError, match="Файл не найден"):
        await file_svc.delete_file(sqlite_session, admin, task.id, uuid.uuid4())


@pytest.mark.asyncio
async def test_task_file_upload_zero_size_validation(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Пустой файл", assignee_sub="admin-sub"),
    )
    with pytest.raises(ValidationError, match="Размер файла"):
        await file_svc.upload_file(
            sqlite_session,
            admin,
            task.id,
            file_data=io.BytesIO(b""),
            file_size=0,
            content_type="text/plain",
            original_filename="empty.txt",
        )


@pytest.mark.asyncio
async def test_task_file_upload_too_large(sqlite_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.portal_collab.services import task_file as file_mod

    fake = MagicMock()
    fake.attachment_max_size_bytes = 100
    monkeypatch.setattr(file_mod, "get_settings", lambda: fake)

    admin = user_portal_admin()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Слишком большой файл", assignee_sub="admin-sub"),
    )
    with pytest.raises(ValidationError, match="Размер файла"):
        await file_svc.upload_file(
            sqlite_session,
            admin,
            task.id,
            file_data=io.BytesIO(b"x" * 200),
            file_size=200,
            content_type="text/plain",
            original_filename="big.bin",
        )


@pytest.mark.asyncio
async def test_task_file_upload_rejects_disallowed_mime(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Недопустимый тип", assignee_sub="admin-sub"),
    )
    with pytest.raises(ValidationError, match="не поддерживается"):
        await file_svc.upload_file(
            sqlite_session,
            admin,
            task.id,
            file_data=io.BytesIO(b"binary"),
            file_size=6,
            content_type="application/octet-stream",
            original_filename="mystery.bin",
        )


@pytest.mark.asyncio
async def test_task_file_upload_rejects_magic_bytes_mismatch(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    task = await task_svc.create_task(
        sqlite_session,
        admin,
        PortalTaskCreate(title="Подмена типа", assignee_sub="admin-sub"),
    )
    with pytest.raises(ValidationError, match="не соответствует заявленному типу"):
        await file_svc.upload_file(
            sqlite_session,
            admin,
            task.id,
            file_data=io.BytesIO(b"not really a pdf"),
            file_size=16,
            content_type="application/pdf",
            original_filename="fake.pdf",
        )
