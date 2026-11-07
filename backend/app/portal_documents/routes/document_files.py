"""HTTP API файлов-вложений документов."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, UploadFile, status

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.core.config import get_settings
from app.infrastructure.db.models.portal_document import PortalDocumentFile
from app.portal_documents.schemas.document import DocumentFileRead
from app.portal_documents.services import document_file as file_svc
from app.services.file_upload_validation import open_upload_stream

router = APIRouter(tags=["Документы"])


def _to_read(row: PortalDocumentFile) -> DocumentFileRead:
    return DocumentFileRead(
        id=row.id,
        document_id=row.document_id,
        original_filename=row.original_filename,
        content_type=row.content_type,
        file_size=row.file_size,
        download_url=file_svc.build_download_url(row),
        view_url=file_svc.build_view_url(row),
        uploaded_by_sub=row.uploaded_by_sub,
        created_at=row.created_at,
    )


@router.get(
    "/documents/{document_id}/files",
    summary="Список файлов-вложений документа",
    response_model=list[DocumentFileRead],
)
async def list_document_files(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> list[DocumentFileRead]:
    rows = await file_svc.list_files(db, user, document_id)
    return [_to_read(r) for r in rows]


@router.post(
    "/documents/{document_id}/files",
    summary="Прикрепить файл к документу",
    response_model=DocumentFileRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_file(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(..., description="Файл документа (PDF, Word, Excel, …)"),
) -> DocumentFileRead:
    async with open_upload_stream(file, get_settings().attachment_max_size_bytes) as (file_data, file_size):
        row = await file_svc.upload_file(
            db,
            user,
            document_id,
            file_data=file_data,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            original_filename=file.filename or "document.bin",
        )
    return _to_read(row)


@router.delete(
    "/documents/{document_id}/files/{file_id}",
    summary="Удалить файл-вложение документа",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document_file(
    document_id: uuid.UUID,
    file_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await file_svc.delete_file(db, user, document_id, file_id)
