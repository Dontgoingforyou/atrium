"""Файлы задач, документов и комментариев и ссылки задачи."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import BinaryIO

from mcp.server.fastmcp import FastMCP

from app.core.exceptions import ValidationError
from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
from app.portal_mcp.auth import dump_dict, mcp_call
from app.portal_mcp.file_payload import decode_mcp_file
from app.portal_mcp.tools._values import parse_uuid

_UploadImage = Callable[[BinaryIO, int, str], Awaitable[PortalRichMedia]]


def register(mcp: FastMCP) -> None:
    @mcp.tool(description="Прикрепить файл к задаче. Содержимое — base64, не больше предела MCP.")
    async def tasks_files_add(
        task_id: str,
        filename: str,
        content_type: str,
        content_base64: str,
    ) -> dict[str, object]:
        from app.portal_collab.schemas.task import TaskFileRead
        from app.portal_collab.services import task_file as file_svc

        async with mcp_call("tasks_files_add") as call:
            file_data, file_size, name = _decoded_file(filename, content_base64)
            row = await file_svc.upload_file(
                call.session,
                call.user,
                parse_uuid(task_id),
                file_data=file_data,
                file_size=file_size,
                content_type=content_type,
                original_filename=name,
            )
            return dump_dict(
                TaskFileRead(
                    id=row.id,
                    task_id=row.task_id,
                    original_filename=row.original_filename,
                    content_type=row.content_type,
                    file_size=row.file_size,
                    download_url=file_svc.build_download_url(row),
                    view_url=file_svc.build_view_url(row),
                    uploaded_by_sub=row.uploaded_by_sub,
                    created_at=row.created_at,
                )
            )

    @mcp.tool(
        description=("Удалить файл задачи. Это может сделать загрузивший файл или администратор портала."),
    )
    async def tasks_files_delete(task_id: str, file_id: str) -> dict[str, bool]:
        from app.portal_collab.services import task_file as file_svc

        async with mcp_call("tasks_files_delete") as call:
            await file_svc.delete_file(
                call.session,
                call.user,
                parse_uuid(task_id),
                parse_uuid(file_id),
            )
            return {"ok": True}

    @mcp.tool(description="Прикрепить файл к документу. PDF, Office или текст. Содержимое — base64.")
    async def documents_files_add(
        document_id: str,
        filename: str,
        content_type: str,
        content_base64: str,
    ) -> dict[str, object]:
        from app.portal_documents.schemas.document import DocumentFileRead
        from app.portal_documents.services import document_file as file_svc

        async with mcp_call("documents_files_add") as call:
            file_data, file_size, name = _decoded_file(filename, content_base64)
            row = await file_svc.upload_file(
                call.session,
                call.user,
                parse_uuid(document_id),
                file_data=file_data,
                file_size=file_size,
                content_type=content_type,
                original_filename=name,
            )
            return dump_dict(
                DocumentFileRead(
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
            )

    @mcp.tool(
        description=("Удалить файл документа. Это может сделать загрузивший файл, менеджер или администратор."),
    )
    async def documents_files_delete(document_id: str, file_id: str) -> dict[str, bool]:
        from app.portal_documents.services import document_file as file_svc

        async with mcp_call("documents_files_delete") as call:
            await file_svc.delete_file(
                call.session,
                call.user,
                parse_uuid(document_id),
                parse_uuid(file_id),
            )
            return {"ok": True}

    @mcp.tool(
        description=(
            "Текстовый комментарий к задаче. Картинку не прикладывать. "
            "Изображение — только через task_comments_add_file, если оно действительно есть."
        ),
    )
    async def task_comments_add(task_id: str, body: str) -> dict[str, object]:
        from app.portal_collab.schemas.task import TaskCommentCreate
        from app.portal_collab.services import task_comment as comment_svc

        async with mcp_call("task_comments_add") as call:
            parsed_id = parse_uuid(task_id)
            comment = await comment_svc.create_comment(
                call.session,
                call.user,
                parsed_id,
                TaskCommentCreate(body=body),
            )
            return _comment_text_card(comment.id, "task_id", parsed_id, comment.body)

    @mcp.tool(
        description=(
            "Изображение в комментарий задачи: jpeg, png, gif или webp, содержимое — base64. "
            "Только настоящая картинка. Текст без картинки — через task_comments_add. "
            "Служебную заглушку не передавать."
        ),
    )
    async def task_comments_add_file(
        task_id: str,
        filename: str,
        content_type: str,
        content_base64: str,
        body: str = "",
    ) -> dict[str, object]:
        from app.portal_collab.schemas.task import TaskCommentCreate
        from app.portal_collab.services import task_comment as comment_svc

        async with mcp_call("task_comments_add_file") as call:
            parsed_id = parse_uuid(task_id)

            async def _upload(data: BinaryIO, size: int, name: str) -> PortalRichMedia:
                return await comment_svc.upload_comment_rich_media(
                    call.session,
                    call.user,
                    parsed_id,
                    file_data=data,
                    file_size=size,
                    content_type=content_type,
                    original_filename=name,
                )

            media = await _store_comment_image(filename, content_base64, _upload)
            comment = await comment_svc.create_comment(
                call.session,
                call.user,
                parsed_id,
                TaskCommentCreate(body=body, media_ids=[media.id]),
            )
            return _comment_file_card(comment.id, "task_id", parsed_id, media)

    @mcp.tool(
        description=(
            "Удалить комментарий задачи целиком, вместе с картинкой. "
            "Это может сделать автор комментария или администратор."
        ),
    )
    async def task_comments_delete(task_id: str, comment_id: str) -> dict[str, bool]:
        from app.portal_collab.services import task_comment as comment_svc

        async with mcp_call("task_comments_delete") as call:
            await comment_svc.delete_comment(
                call.session,
                call.user,
                parse_uuid(task_id),
                parse_uuid(comment_id),
            )
            return {"ok": True}

    @mcp.tool(
        description=(
            "Текстовый комментарий к документу. Картинку не прикладывать. "
            "Изображение — только через document_comments_add_file, если оно действительно есть."
        ),
    )
    async def document_comments_add(document_id: str, body: str) -> dict[str, object]:
        from app.portal_documents.schemas.document_comment import DocumentCommentCreate
        from app.portal_documents.services import document_comment as comment_svc

        async with mcp_call("document_comments_add") as call:
            parsed_id = parse_uuid(document_id)
            comment = await comment_svc.create_comment(
                call.session,
                call.user,
                parsed_id,
                DocumentCommentCreate(body=body),
            )
            return _comment_text_card(comment.id, "document_id", parsed_id, comment.body)

    @mcp.tool(
        description=(
            "Изображение в комментарий документа: jpeg, png, gif или webp, содержимое — base64. "
            "Только настоящая картинка. Текст без картинки — через document_comments_add. "
            "Служебную заглушку не передавать."
        ),
    )
    async def document_comments_add_file(
        document_id: str,
        filename: str,
        content_type: str,
        content_base64: str,
        body: str = "",
    ) -> dict[str, object]:
        from app.portal_documents.schemas.document_comment import DocumentCommentCreate
        from app.portal_documents.services import document_comment as comment_svc

        async with mcp_call("document_comments_add_file") as call:
            parsed_id = parse_uuid(document_id)

            async def _upload(data: BinaryIO, size: int, name: str) -> PortalRichMedia:
                return await comment_svc.upload_comment_rich_media(
                    call.session,
                    call.user,
                    parsed_id,
                    file_data=data,
                    file_size=size,
                    content_type=content_type,
                    original_filename=name,
                )

            media = await _store_comment_image(filename, content_base64, _upload)
            comment = await comment_svc.create_comment(
                call.session,
                call.user,
                parsed_id,
                DocumentCommentCreate(body=body, media_ids=[media.id]),
            )
            return _comment_file_card(comment.id, "document_id", parsed_id, media)

    @mcp.tool(
        description=(
            "Удалить комментарий документа целиком, вместе с картинкой. "
            "Это может сделать автор комментария или администратор."
        ),
    )
    async def document_comments_delete(document_id: str, comment_id: str) -> dict[str, bool]:
        from app.portal_documents.services import document_comment as comment_svc

        async with mcp_call("document_comments_delete") as call:
            await comment_svc.delete_comment(
                call.session,
                call.user,
                parse_uuid(document_id),
                parse_uuid(comment_id),
            )
            return {"ok": True}

    @mcp.tool(description="Добавить ссылку в блок «Ссылки» задачи. Название необязательно. Адрес — http или https.")
    async def tasks_links_add(task_id: str, url: str, title: str | None = None) -> dict[str, object]:
        from app.portal_collab.schemas.task import TaskLinkCreate, TaskLinkRead
        from app.portal_collab.services import task_link as link_svc

        async with mcp_call("tasks_links_add") as call:
            link = await link_svc.create_link(
                call.session,
                call.user,
                parse_uuid(task_id),
                TaskLinkCreate(title=title, url=url),
            )
            return dump_dict(TaskLinkRead.model_validate(link))

    @mcp.tool(
        description=(
            "Удалить ссылку из блока «Ссылки» задачи. Это может сделать автор ссылки или администратор портала."
        ),
    )
    async def tasks_links_delete(task_id: str, link_id: str) -> dict[str, bool]:
        from app.portal_collab.services import task_link as link_svc

        async with mcp_call("tasks_links_delete") as call:
            await link_svc.delete_link(
                call.session,
                call.user,
                parse_uuid(task_id),
                parse_uuid(link_id),
            )
            return {"ok": True}

    from app.portal_mcp.tools.file_lists import register as register_lists

    register_lists(mcp)


def _decoded_file(filename: str, content_base64: str) -> tuple[BinaryIO, int, str]:
    file_data, file_size = decode_mcp_file(content_base64)
    return file_data, file_size, _filename(filename)


def _filename(value: str) -> str:
    name = value.strip().replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name or name in {".", ".."}:
        raise ValidationError("Укажите имя файла")
    return name[:512]


def _comment_text_card(
    comment_id: uuid.UUID,
    host_key: str,
    host_id: uuid.UUID,
    body: str,
) -> dict[str, object]:
    return {
        "comment_id": str(comment_id),
        host_key: str(host_id),
        "body": body,
    }


def _comment_file_card(
    comment_id: uuid.UUID,
    host_key: str,
    host_id: uuid.UUID,
    media: PortalRichMedia,
) -> dict[str, object]:
    """Карточка комментария без presigned URL: файл открывается в портале."""
    return {
        "comment_id": str(comment_id),
        host_key: str(host_id),
        "media_id": str(media.id),
        "original_filename": media.original_filename,
        "content_type": media.content_type,
        "file_size": int(media.file_size),
    }


async def _store_comment_image(
    filename: str,
    content_base64: str,
    upload: _UploadImage,
) -> PortalRichMedia:
    file_data, file_size, name = _decoded_file(filename, content_base64)
    return await upload(file_data, file_size, name)
