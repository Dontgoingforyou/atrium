"""Списки файлов документа и комментариев для HTTP MCP."""

from __future__ import annotations

import uuid

from mcp.server.fastmcp import FastMCP

from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
from app.portal_mcp.auth import clamp_limit, dump_dict, mcp_call
from app.portal_mcp.constants import LIST_LIMIT_DEFAULT
from app.portal_mcp.tools._values import parse_uuid


def register(mcp: FastMCP) -> None:
    @mcp.tool(description="Файлы документа. В ответе есть id, чтобы удалить файл.")
    async def documents_files_list(
        document_id: str,
        limit: int = LIST_LIMIT_DEFAULT,
    ) -> list[dict[str, object]]:
        from app.portal_documents.schemas.document import DocumentFileRead
        from app.portal_documents.services import document_file as file_svc

        async with mcp_call("documents_files_list") as call:
            rows = await file_svc.list_files(call.session, call.user, parse_uuid(document_id))
            return [
                dump_dict(
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
                for row in rows[: clamp_limit(limit)]
            ]

    @mcp.tool(description="Комментарии задачи. В ответе есть comment_id, чтобы удалить комментарий.")
    async def task_comments_list(task_id: str, limit: int = LIST_LIMIT_DEFAULT) -> list[dict[str, object]]:
        from app.portal_collab.services import task_comment as comment_svc

        async with mcp_call("task_comments_list") as call:
            parsed_id = parse_uuid(task_id)
            rows = await comment_svc.list_comments(
                call.session,
                call.user,
                parsed_id,
                limit=clamp_limit(limit),
            )
            return [_comment_list_card(row.id, "task_id", parsed_id, row.body, row.media) for row in rows]

    @mcp.tool(description="Комментарии документа. В ответе есть comment_id, чтобы удалить комментарий.")
    async def document_comments_list(
        document_id: str,
        limit: int = LIST_LIMIT_DEFAULT,
    ) -> list[dict[str, object]]:
        from app.portal_documents.services import document_comment as comment_svc

        async with mcp_call("document_comments_list") as call:
            parsed_id = parse_uuid(document_id)
            rows = await comment_svc.list_comments(
                call.session,
                call.user,
                parsed_id,
                limit=clamp_limit(limit),
            )
            return [_comment_list_card(row.id, "document_id", parsed_id, row.body, row.media) for row in rows]


def _comment_list_card(
    comment_id: uuid.UUID,
    host_key: str,
    host_id: uuid.UUID,
    body: str,
    media: list[PortalRichMedia],
) -> dict[str, object]:
    card: dict[str, object] = {
        "comment_id": str(comment_id),
        host_key: str(host_id),
        "body": body,
    }
    if media:
        card["media_id"] = str(media[0].id)
    return card
