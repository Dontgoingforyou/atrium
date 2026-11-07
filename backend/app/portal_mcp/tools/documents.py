"""Документы и теги."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.portal_mcp.auth import clamp_limit, dump_dict, dump_list, mcp_call, require_admin
from app.portal_mcp.constants import LIST_LIMIT_DEFAULT
from app.portal_mcp.tools._values import parse_uuid, parse_uuids


def register(mcp: FastMCP) -> None:
    @mcp.tool(description="Список документов, которые пользователь может читать.")
    async def documents_list(
        limit: int = LIST_LIMIT_DEFAULT,
        skip: int = 0,
        tag_slug: str | None = None,
        owner_sub: str | None = None,
    ) -> dict[str, object]:
        from app.portal_documents.schemas.document import PortalDocumentListItem
        from app.portal_documents.services import portal_document as svc

        async with mcp_call("documents_list") as call:
            bounded = clamp_limit(limit)
            document_ids = await svc.readable_document_ids_for_user(call.session, call.user)
            tag_slugs = [tag_slug] if tag_slug else None
            total = await svc.count_documents(
                call.session,
                tag_slugs=tag_slugs,
                owner_sub=owner_sub,
                document_ids=document_ids,
            )
            docs = await svc.list_documents(
                call.session,
                tag_slugs=tag_slugs,
                owner_sub=owner_sub,
                document_ids=document_ids,
                skip=skip,
                limit=bounded,
            )
            items = [PortalDocumentListItem.model_validate(doc) for doc in docs]
            return {"items": dump_list(items), "total": total, "skip": skip, "limit": bounded}

    @mcp.tool(description="Документ по идентификатору.")
    async def documents_get(document_id: str) -> dict[str, object]:
        from app.portal_documents.schemas.document import PortalDocumentRead
        from app.portal_documents.services import portal_document as svc

        async with mcp_call("documents_get") as call:
            doc = await svc.ensure_user_can_read_document(call.session, call.user, parse_uuid(document_id))
            return dump_dict(PortalDocumentRead.model_validate(doc))

    @mcp.tool(description="Создать документ.")
    async def documents_create(
        title: str,
        body: str | None = None,
        parent_document_id: str | None = None,
        tag_ids: list[str] | None = None,
    ) -> dict[str, object]:
        from app.portal_documents.schemas.document import PortalDocumentCreate, PortalDocumentRead
        from app.portal_documents.services import portal_document as svc

        data = PortalDocumentCreate(
            title=title,
            body=body,
            parent_document_id=parse_uuid(parent_document_id) if parent_document_id else None,
            tag_ids=parse_uuids(tag_ids) or [],
        )
        async with mcp_call("documents_create") as call:
            doc = await svc.create_document(
                call.session,
                data,
                call.user.sub,
                author_display_name=call.user.full_name,
                author_email=call.user.email,
                author=call.user,
            )
            return dump_dict(PortalDocumentRead.model_validate(doc))

    @mcp.tool(description="Изменить документ. Нужна версия карточки.")
    async def documents_update(
        document_id: str,
        expected_version: int,
        title: str | None = None,
        body: str | None = None,
        parent_document_id: str | None = None,
        tag_ids: list[str] | None = None,
    ) -> dict[str, object]:
        from app.portal_documents.schemas.document import PortalDocumentRead, PortalDocumentUpdate
        from app.portal_documents.services import portal_document as svc

        payload: dict[str, object] = {"expected_version": expected_version}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if parent_document_id is not None:
            payload["parent_document_id"] = parse_uuid(parent_document_id)
        if tag_ids is not None:
            payload["tag_ids"] = parse_uuids(tag_ids)
        async with mcp_call("documents_update") as call:
            doc = await svc.update_document(
                call.session,
                parse_uuid(document_id),
                PortalDocumentUpdate.model_validate(payload),
                call.user.sub,
                changed_by_display_name=call.user.full_name,
                changed_by_email=call.user.email,
                changed_by=call.user,
            )
            return dump_dict(PortalDocumentRead.model_validate(doc))

    @mcp.tool(description="Убрать документ в корзину.")
    async def documents_trash(document_id: str) -> dict[str, object]:
        from app.portal_documents.services import portal_document as svc

        async with mcp_call("documents_trash") as call:
            ids = await svc.soft_delete_document(
                call.session,
                parse_uuid(document_id),
                call.user.sub,
                deleted_by_display_name=call.user.full_name,
                deleted_by_email=call.user.email,
            )
            return {"ids": [str(item) for item in ids]}

    @mcp.tool(description="Вернуть документ из корзины.")
    async def documents_restore(document_id: str) -> dict[str, object]:
        from app.portal_documents.schemas.document import PortalDocumentRead
        from app.portal_documents.services import portal_document as svc

        async with mcp_call("documents_restore") as call:
            doc = await svc.restore_document(
                call.session,
                parse_uuid(document_id),
                call.user.sub,
                changed_by_display_name=call.user.full_name,
                changed_by_email=call.user.email,
            )
            return dump_dict(PortalDocumentRead.model_validate(doc))

    @mcp.tool(description="Удалить документ навсегда. Только администратор портала.")
    async def documents_purge(document_id: str) -> dict[str, object]:
        from app.portal_documents.services import portal_document as svc

        async with mcp_call("documents_purge") as call:
            await require_admin(call, "documents_purge")
            ids = await svc.permanently_purge_document(call.session, parse_uuid(document_id))
            return {"ids": [str(item) for item in ids]}

    @mcp.tool(description="Список тегов документов.")
    async def tags_list(limit: int = LIST_LIMIT_DEFAULT, skip: int = 0) -> list[dict[str, object]]:
        from app.schemas.tags import PortalTagRead
        from app.services.portal_tags import list_tags

        async with mcp_call("tags_list") as call:
            rows = await list_tags(call.session, skip=skip, limit=clamp_limit(limit))
            return dump_list([PortalTagRead.model_validate(row) for row in rows])

    @mcp.tool(description="Создать тег.")
    async def tags_create(name: str, color: str = "#3B82F6") -> dict[str, object]:
        from app.schemas.tags import PortalTagCreate, PortalTagRead
        from app.services.portal_tags import create_tag

        async with mcp_call("tags_create") as call:
            tag = await create_tag(call.session, PortalTagCreate(name=name, color=color))
            return dump_dict(PortalTagRead.model_validate(tag))

    @mcp.tool(description="Изменить тег. Нужна версия.")
    async def tags_update(
        tag_id: str,
        expected_version: int,
        name: str | None = None,
        color: str | None = None,
    ) -> dict[str, object]:
        from app.schemas.tags import PortalTagRead, PortalTagUpdate
        from app.services.portal_tags import update_tag

        data = PortalTagUpdate(expected_version=expected_version, name=name, color=color)
        async with mcp_call("tags_update") as call:
            tag = await update_tag(call.session, parse_uuid(tag_id), data)
            return dump_dict(PortalTagRead.model_validate(tag))

    @mcp.tool(description="Удалить тег.")
    async def tags_delete(tag_id: str) -> dict[str, bool]:
        from app.services.portal_tags import delete_tag

        async with mcp_call("tags_delete") as call:
            await delete_tag(call.session, parse_uuid(tag_id))
            return {"ok": True}
