"""Доска специалистов, карточка, заметки, ссылки и Jira."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.portal_mcp.auth import clamp_limit, dump_dict, dump_list, mcp_call
from app.portal_mcp.constants import LIST_LIMIT_DEFAULT
from app.portal_mcp.tools._values import parse_date, parse_uuid


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        description=(
            "Доска специалистов. Менеджер видит свою. Админ без manager_sub видит все, с manager_sub — выбранную."
        ),
    )
    async def specialists_board(
        manager_sub: str | None = None,
        limit: int = LIST_LIMIT_DEFAULT,
    ) -> list[dict[str, object]]:
        from app.portal_specialists.services.board_entries import list_board_entries

        async with mcp_call("specialists_board") as call:
            rows = await list_board_entries(call.session, call.user, manager_sub=manager_sub)
            return dump_list(rows[: clamp_limit(limit)])

    @mcp.tool(description="Карточка специалиста.")
    async def specialists_get(specialist_sub: str) -> dict[str, object]:
        from app.portal_specialists.services.specialist_detail import get_specialist_profile

        async with mcp_call("specialists_get") as call:
            return dump_dict(await get_specialist_profile(call.session, call.user, specialist_sub))

    @mcp.tool(description="Изменить карточку специалиста, если он закреплён за этим менеджером.")
    async def specialists_update(
        specialist_sub: str,
        expected_version: int,
        birthdate: str | None = None,
        location: str | None = None,
        telegram: str | None = None,
    ) -> dict[str, object]:
        from app.portal_specialists.schemas.specialist_detail import SpecialistProfileUpdate
        from app.portal_specialists.services.specialist_detail import update_specialist_profile

        payload: dict[str, object] = {"expected_version": expected_version}
        if birthdate is not None:
            payload["birthdate"] = parse_date(birthdate)
        if location is not None:
            payload["location"] = location
        if telegram is not None:
            payload["telegram"] = telegram
        async with mcp_call("specialists_update") as call:
            profile = await update_specialist_profile(
                call.session,
                call.user,
                specialist_sub,
                SpecialistProfileUpdate.model_validate(payload),
            )
            return dump_dict(profile)

    @mcp.tool(description="Заметки по специалисту.")
    async def specialists_notes_list(specialist_sub: str, limit: int = LIST_LIMIT_DEFAULT) -> list[dict[str, object]]:
        from app.portal_specialists.services.specialist_note import list_specialist_notes

        async with mcp_call("specialists_notes_list") as call:
            rows = await list_specialist_notes(call.session, call.user, specialist_sub)
            return dump_list(rows[: clamp_limit(limit)])

    @mcp.tool(description="Добавить заметку о специалисте.")
    async def specialists_notes_create(specialist_sub: str, body: str) -> dict[str, object]:
        from app.portal_specialists.schemas.specialist_detail import SpecialistNoteCreate
        from app.portal_specialists.services.specialist_note import create_specialist_note

        async with mcp_call("specialists_notes_create") as call:
            note = await create_specialist_note(
                call.session,
                call.user,
                specialist_sub,
                SpecialistNoteCreate(body=body),
            )
            return dump_dict(note)

    @mcp.tool(description="Изменить свою заметку. Админ может изменить чужую — это решает сервис.")
    async def specialists_notes_update(specialist_sub: str, note_id: str, body: str) -> dict[str, object]:
        from app.portal_specialists.schemas.specialist_detail import SpecialistNoteUpdate
        from app.portal_specialists.services.specialist_note import update_specialist_note

        async with mcp_call("specialists_notes_update") as call:
            note = await update_specialist_note(
                call.session,
                call.user,
                specialist_sub,
                parse_uuid(note_id),
                SpecialistNoteUpdate(body=body),
            )
            return dump_dict(note)

    @mcp.tool(description="Удалить заметку.")
    async def specialists_notes_delete(specialist_sub: str, note_id: str) -> dict[str, bool]:
        from app.portal_specialists.services.specialist_note import delete_specialist_note

        async with mcp_call("specialists_notes_delete") as call:
            await delete_specialist_note(call.session, call.user, specialist_sub, parse_uuid(note_id))
            return {"ok": True}

    @mcp.tool(description="Ссылки специалиста.")
    async def specialists_links_list(specialist_sub: str, limit: int = LIST_LIMIT_DEFAULT) -> list[dict[str, object]]:
        from app.portal_specialists.services.specialist_detail import list_specialist_links

        async with mcp_call("specialists_links_list") as call:
            rows = await list_specialist_links(call.session, call.user, specialist_sub)
            return dump_list(rows[: clamp_limit(limit)])

    @mcp.tool(description="Добавить ссылку специалисту.")
    async def specialists_links_create(specialist_sub: str, title: str, url: str) -> dict[str, object]:
        from app.portal_specialists.schemas.specialist_detail import SpecialistLinkCreate
        from app.portal_specialists.services.specialist_detail import create_specialist_link

        async with mcp_call("specialists_links_create") as call:
            link = await create_specialist_link(
                call.session,
                call.user,
                specialist_sub,
                SpecialistLinkCreate(title=title, url=url),
            )
            return dump_dict(link)

    @mcp.tool(description="Удалить ссылку специалиста.")
    async def specialists_links_delete(specialist_sub: str, link_id: str) -> dict[str, bool]:
        from app.portal_specialists.services.specialist_detail import delete_specialist_link

        async with mcp_call("specialists_links_delete") as call:
            await delete_specialist_link(call.session, call.user, specialist_sub, parse_uuid(link_id))
            return {"ok": True}

    @mcp.tool(description="Поиск карточек специалистов в Jira.")
    async def specialists_jira_search(q: str) -> list[dict[str, str]]:
        from app.portal_specialists.services.jira_import import search_jira_specialists

        async with mcp_call("specialists_jira_search") as call:
            return await search_jira_specialists(call.user, call.http, q)

    @mcp.tool(description="Привязать специалиста к карточке Jira.")
    async def specialists_jira_link(specialist_sub: str, issue_key: str) -> dict[str, object]:
        from app.portal_specialists.services.jira_import import link_specialist_to_jira

        async with mcp_call("specialists_jira_link") as call:
            profile = await link_specialist_to_jira(call.session, call.user, call.http, specialist_sub, issue_key)
            return {"specialist_sub": profile.specialist_sub, "jira_issue_key": profile.jira_issue_key}

    @mcp.tool(description="Перенести специалиста к другому менеджеру. Только администратор, это решает сервис.")
    async def specialists_reassign(specialist_sub: str, from_manager_sub: str, to_manager_sub: str) -> dict[str, str]:
        from app.portal_specialists.services.board_entries import reassign_manager

        async with mcp_call("specialists_reassign") as call:
            entry = await reassign_manager(
                call.session,
                call.user,
                specialist_sub,
                from_manager_sub=from_manager_sub,
                to_manager_sub=to_manager_sub,
            )
            return {"specialist_sub": entry.specialist_sub, "manager_sub": entry.manager_sub}

    @mcp.tool(
        description=(
            "Перенести специалиста в колонку воронки. Нужна версия записи с доски. "
            "Чужую доску двигает только администратор, это решает сервис."
        ),
    )
    async def specialists_move(
        specialist_sub: str,
        column_key: str,
        expected_version: int,
        position: int | None = None,
        manager_sub: str | None = None,
    ) -> dict[str, object]:
        from app.portal_specialists.schemas.board import ManagerSpecialistPatch
        from app.portal_specialists.services.board_entries import move_on_board

        async with mcp_call("specialists_move") as call:
            entry = await move_on_board(
                call.session,
                call.user,
                specialist_sub,
                ManagerSpecialistPatch(
                    expected_version=expected_version,
                    column_key=column_key,
                    position=position,
                ),
                target_manager_sub=manager_sub,
            )
            return {
                "specialist_sub": entry.specialist_sub,
                "manager_sub": entry.manager_sub,
                "column_key": entry.column_key,
                "position": entry.position,
                "version": entry.version,
            }

    @mcp.tool(description="Менеджеры, за которыми закреплён специалист. Только администратор, это решает сервис.")
    async def specialists_managers(specialist_sub: str) -> list[dict[str, object]]:
        from app.portal_specialists.services.board_entries import list_managers_for_specialist

        async with mcp_call("specialists_managers") as call:
            return dump_list(await list_managers_for_specialist(call.session, call.user, specialist_sub))

    @mcp.tool(description="Колонки воронки специалистов.")
    async def specialists_columns_list() -> list[dict[str, object]]:
        from app.portal_specialists.schemas.board import SpecialistColumnRead
        from app.portal_specialists.services.board_columns_statuses import list_specialist_columns

        async with mcp_call("specialists_columns_list") as call:
            rows = await list_specialist_columns(call.session, call.user)
            return dump_list([SpecialistColumnRead.model_validate(row) for row in rows])

    @mcp.tool(description="Создать колонку воронки. Только администратор, это решает сервис.")
    async def specialists_columns_create(
        key: str,
        title: str,
        color: str = "#888888",
        position: int = 0,
    ) -> dict[str, object]:
        from app.portal_specialists.schemas.board import SpecialistColumnCreate, SpecialistColumnRead
        from app.portal_specialists.services.board_columns_statuses import create_specialist_column

        data = SpecialistColumnCreate(key=key, title=title, color=color, position=position)
        async with mcp_call("specialists_columns_create") as call:
            column = await create_specialist_column(call.session, call.user, data)
            return dump_dict(SpecialistColumnRead.model_validate(column))

    @mcp.tool(description="Изменить колонку воронки. Только администратор, это решает сервис.")
    async def specialists_columns_update(
        column_id: str,
        title: str | None = None,
        color: str | None = None,
        position: int | None = None,
    ) -> dict[str, object]:
        from app.portal_specialists.schemas.board import SpecialistColumnRead, SpecialistColumnUpdate
        from app.portal_specialists.services.board_columns_statuses import update_specialist_column

        data = SpecialistColumnUpdate(title=title, color=color, position=position)
        async with mcp_call("specialists_columns_update") as call:
            column = await update_specialist_column(call.session, call.user, parse_uuid(column_id), data)
            return dump_dict(SpecialistColumnRead.model_validate(column))

    @mcp.tool(description="Удалить колонку воронки. Только администратор, это решает сервис.")
    async def specialists_columns_delete(column_id: str) -> dict[str, bool]:
        from app.portal_specialists.services.board_columns_statuses import delete_specialist_column

        async with mcp_call("specialists_columns_delete") as call:
            await delete_specialist_column(call.session, call.user, parse_uuid(column_id))
            return {"ok": True}

    @mcp.tool(description="Статусы специалистов.")
    async def specialists_statuses_list() -> list[dict[str, object]]:
        from app.portal_specialists.schemas.board import SpecialistStatusRead
        from app.portal_specialists.services.board_columns_statuses import list_specialist_statuses

        async with mcp_call("specialists_statuses_list") as call:
            rows = await list_specialist_statuses(call.session, call.user)
            return dump_list([SpecialistStatusRead.model_validate(row) for row in rows])

    @mcp.tool(description="Изменить статус специалиста. Только администратор, это решает сервис.")
    async def specialists_statuses_update(
        status_id: str,
        title: str | None = None,
        color: str | None = None,
    ) -> dict[str, object]:
        from app.portal_specialists.schemas.board import SpecialistStatusRead, SpecialistStatusUpdate
        from app.portal_specialists.services.board_columns_statuses import update_specialist_status

        data = SpecialistStatusUpdate(title=title, color=color)
        async with mcp_call("specialists_statuses_update") as call:
            status = await update_specialist_status(call.session, call.user, parse_uuid(status_id), data)
            return dump_dict(SpecialistStatusRead.model_validate(status))

    @mcp.tool(description="Удалить статус специалиста. Только администратор, это решает сервис.")
    async def specialists_statuses_delete(status_id: str) -> dict[str, bool]:
        from app.portal_specialists.services.board_columns_statuses import delete_specialist_status

        async with mcp_call("specialists_statuses_delete") as call:
            await delete_specialist_status(call.session, call.user, parse_uuid(status_id))
            return {"ok": True}

    @mcp.tool(description="Подтянуть колонки воронки из доски Jira. Только администратор, это решает сервис.")
    async def specialists_columns_sync_jira() -> list[dict[str, object]]:
        from app.portal_specialists.schemas.board import SpecialistColumnRead
        from app.portal_specialists.services.jira_board_sync import sync_columns_from_jira

        async with mcp_call("specialists_columns_sync_jira") as call:
            rows = await sync_columns_from_jira(call.session, call.user, call.http)
            return dump_list([SpecialistColumnRead.model_validate(row) for row in rows])

    @mcp.tool(description="Полностью убрать карточку специалиста из портала. Только администратор, это решает сервис.")
    async def specialists_purge(specialist_sub: str) -> dict[str, object]:
        from app.portal_specialists.services.specialist_detail import purge_specialist_from_portal

        async with mcp_call("specialists_purge") as call:
            ids = await purge_specialist_from_portal(call.session, call.user, specialist_sub)
            return {"ids": [str(item) for item in ids]}
