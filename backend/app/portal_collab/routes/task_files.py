from __future__ import annotations

import uuid

from fastapi import APIRouter, File, UploadFile

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.core.config import get_settings
from app.infrastructure.db.models.portal_task import PortalTaskFile
from app.portal_collab.schemas.task import TaskFileRead
from app.portal_collab.services import task_file as file_svc
from app.services.file_upload_validation import open_upload_stream

router = APIRouter(prefix="/portal", tags=["Задачи"])


def _to_read(file: PortalTaskFile) -> TaskFileRead:
    return TaskFileRead(
        id=file.id,
        task_id=file.task_id,
        original_filename=file.original_filename,
        content_type=file.content_type,
        file_size=file.file_size,
        download_url=file_svc.build_download_url(file),
        view_url=file_svc.build_view_url(file),
        uploaded_by_sub=file.uploaded_by_sub,
        created_at=file.created_at,
    )


@router.get(
    "/tasks/{task_id}/files",
    summary="Список файлов задачи",
    response_model=list[TaskFileRead],
)
async def list_task_files(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> list[TaskFileRead]:
    rows = await file_svc.list_files(db, user, task_id)
    return [_to_read(r) for r in rows]


@router.post(
    "/tasks/{task_id}/files",
    summary="Прикрепить файл к задаче",
    response_model=TaskFileRead,
    status_code=201,
)
async def upload_task_file(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(..., description="Прикрепляемый файл (лимит размера — настройка сервера)"),
) -> TaskFileRead:
    async with open_upload_stream(file, get_settings().attachment_max_size_bytes) as (file_data, file_size):
        row = await file_svc.upload_file(
            db,
            user,
            task_id,
            file_data=file_data,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            original_filename=file.filename or "file",
        )
    return _to_read(row)


@router.delete(
    "/tasks/{task_id}/files/{file_id}",
    summary="Удалить файл задачи",
    status_code=204,
)
async def delete_task_file(
    task_id: uuid.UUID,
    file_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await file_svc.delete_file(db, user, task_id, file_id)
