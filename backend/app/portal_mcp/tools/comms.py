"""Таймшиты, календарь, чаты, избранное, уведомления и поиск."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.core.exceptions import ValidationError
from app.core.portal_search_constants import PORTAL_SEARCH_ENTITY_TYPES, PORTAL_SEARCH_MIN_QUERY_LEN
from app.portal_calendar.remote import CalendarRemote, opened_remote
from app.portal_mcp.auth import McpCall, clamp_limit, current_authorization, dump_dict, dump_list, mcp_call
from app.portal_mcp.constants import LIST_LIMIT_DEFAULT
from app.portal_mcp.tools._values import parse_date, parse_datetime, parse_uuid


def _calendar_remote(call: McpCall) -> CalendarRemote | None:
    return opened_remote(call.user, current_authorization(), call.http)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        description=(
            "Таймшиты. Без user_sub админ видит всех, менеджер — свои. Явный user_sub показывает этого человека."
        ),
    )
    async def timesheets_list(
        limit: int = LIST_LIMIT_DEFAULT,
        user_sub: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, object]:
        from app.portal_time_entries.schemas.time_entry import PortalTimeEntryRead
        from app.portal_time_entries.services.time_entry import list_time_entries

        async with mcp_call("timesheets_list") as call:
            bounded = clamp_limit(limit)
            rows, total = await list_time_entries(
                call.session,
                call.user,
                filter_user_sub=user_sub,
                date_from=parse_date(date_from) if date_from else None,
                date_to=parse_date(date_to) if date_to else None,
                task_id=parse_uuid(task_id) if task_id else None,
                limit=bounded,
            )
            return {
                "items": dump_list([PortalTimeEntryRead.model_validate(row) for row in rows]),
                "total": total,
                "limit": bounded,
            }

    @mcp.tool(description="Часы специалистов за месяц ГГГГ-ММ. Доступно менеджеру и админу.")
    async def timesheets_monthly_summary(month: str, limit: int = LIST_LIMIT_DEFAULT) -> dict[str, object]:
        from app.portal_time_entries.services._time_entry_reports import list_specialists_monthly_summary

        async with mcp_call("timesheets_monthly_summary") as call:
            bounded = clamp_limit(limit)
            rows, total = await list_specialists_monthly_summary(
                call.session,
                call.user,
                month=month,
                limit=bounded,
            )
            return {"items": dump_list(rows), "total": total, "limit": bounded}

    @mcp.tool(description="Календари текущего пользователя.")
    async def calendars_list(limit: int = LIST_LIMIT_DEFAULT) -> list[dict[str, object]]:
        from app.portal_calendar.services._calendars import list_calendars

        async with mcp_call("calendars_list") as call:
            remote = _calendar_remote(call)
            if remote is None:
                rows = await list_calendars(call.session, call.user)
            else:
                rows = await remote.list_calendars()
            return dump_list(rows[: clamp_limit(limit)])

    @mcp.tool(description="События календаря в окне. Время — ISO 8601 с часовым поясом.")
    async def calendar_occurrences(
        window_start: str,
        window_end: str,
        limit: int = LIST_LIMIT_DEFAULT,
        calendar_ids: list[str] | None = None,
    ) -> list[dict[str, object]]:
        from app.portal_calendar.services._events import list_occurrences

        ids = [parse_uuid(item) for item in calendar_ids] if calendar_ids else None
        async with mcp_call("calendar_occurrences") as call:
            remote = _calendar_remote(call)
            if remote is None:
                rows = await list_occurrences(
                    call.session,
                    call.user,
                    window_start=parse_datetime(window_start),
                    window_end=parse_datetime(window_end),
                    calendar_ids=ids,
                )
            else:
                rows = await remote.list_occurrences(
                    starts=parse_datetime(window_start),
                    ends=parse_datetime(window_end),
                    calendar_ids=ids,
                    peer_user_sub=None,
                )
            return dump_list(rows[: clamp_limit(limit)])

    @mcp.tool(description="Создать событие. Нужен хотя бы один участник.")
    async def calendar_events_create(
        calendar_id: str,
        title: str,
        starts_at: str,
        attendee_subs: list[str],
        ends_at: str | None = None,
        description: str | None = None,
        location: str | None = None,
    ) -> dict[str, object]:
        from app.portal_calendar.schemas.calendar import AttendeeCreate, EventCreate
        from app.portal_calendar.services._events import create_event

        data = EventCreate(
            calendar_id=parse_uuid(calendar_id),
            title=title,
            description=description,
            location=location,
            starts_at=parse_datetime(starts_at),
            ends_at=parse_datetime(ends_at) if ends_at else None,
            attendees=[AttendeeCreate(user_sub=sub) for sub in attendee_subs],
        )
        async with mcp_call("calendar_events_create") as call:
            remote = _calendar_remote(call)
            if remote is None:
                return dump_dict(await create_event(call.session, call.user, data))
            from app.portal_calendar.remote import attendee_bodies

            payload = data.model_dump(mode="json", exclude={"calendar_id"})
            attendees = payload.get("attendees")
            if attendees is not None:
                payload["attendees"] = await attendee_bodies(call.session, attendees)
            return dump_dict(await remote.create_event(data.calendar_id, payload))

    @mcp.tool(description="Изменить событие. Нужна версия.")
    async def calendar_events_update(
        event_id: str,
        expected_version: int,
        title: str | None = None,
        starts_at: str | None = None,
        ends_at: str | None = None,
        description: str | None = None,
        location: str | None = None,
        attendee_subs: list[str] | None = None,
    ) -> dict[str, object]:
        from app.portal_calendar.schemas.calendar import AttendeeCreate, EventUpdate
        from app.portal_calendar.services._events import update_event

        payload: dict[str, object] = {"expected_version": expected_version}
        if title is not None:
            payload["title"] = title
        if starts_at is not None:
            payload["starts_at"] = parse_datetime(starts_at)
        if ends_at is not None:
            payload["ends_at"] = parse_datetime(ends_at)
        if description is not None:
            payload["description"] = description
        if location is not None:
            payload["location"] = location
        if attendee_subs is not None:
            payload["attendees"] = [AttendeeCreate(user_sub=sub) for sub in attendee_subs]
        async with mcp_call("calendar_events_update") as call:
            data = EventUpdate.model_validate(payload)
            remote = _calendar_remote(call)
            if remote is None:
                event = await update_event(call.session, call.user, parse_uuid(event_id), data)
                return dump_dict(event)
            from app.portal_calendar.remote import attendee_bodies

            body = data.model_dump(mode="json", exclude_unset=True)
            attendees = body.get("attendees")
            if attendees is not None:
                body["attendees"] = await attendee_bodies(call.session, attendees)
            return dump_dict(await remote.update_event(parse_uuid(event_id), body))

    @mcp.tool(description="Чаты, в которых состоит пользователь. Админ тоже видит только свои.")
    async def chats_list(limit: int = LIST_LIMIT_DEFAULT, skip: int = 0) -> list[dict[str, object]]:
        from app.portal_chat.schemas.chat import PortalChatRead
        from app.portal_chat.services.chat import list_chats_for_user

        async with mcp_call("chats_list") as call:
            rows = await list_chats_for_user(call.session, call.user, skip=skip, limit=clamp_limit(limit))
            return dump_list([PortalChatRead.model_validate(row) for row in rows])

    @mcp.tool(description="Сообщения чата. Чтение чужого чата по id доступно админу.")
    async def chats_messages(chat_id: str, limit: int = LIST_LIMIT_DEFAULT, skip: int = 0) -> list[dict[str, object]]:
        from app.portal_chat.services._queries_messages import list_messages, message_to_read

        async with mcp_call("chats_messages") as call:
            rows = await list_messages(
                call.session,
                call.user,
                parse_uuid(chat_id),
                skip=skip,
                limit=clamp_limit(limit),
            )
            return dump_list([message_to_read(row) for row in rows])

    @mcp.tool(description="Отправить сообщение. Только участник чата, в том числе админ.")
    async def chats_send(chat_id: str, body: str) -> dict[str, object]:
        from app.portal_chat.schemas.chat import PortalChatMessageCreate
        from app.portal_chat.services._mutations import post_message
        from app.portal_chat.services._queries_messages import message_to_read

        async with mcp_call("chats_send") as call:
            message = await post_message(
                call.session,
                call.user,
                parse_uuid(chat_id),
                PortalChatMessageCreate(body=body),
            )
            return dump_dict(message_to_read(message))

    @mcp.tool(description="Избранное текущего пользователя.")
    async def favorites_list(limit: int = LIST_LIMIT_DEFAULT, skip: int = 0) -> list[dict[str, object]]:
        from app.portal_favorites.services.favorite import list_favorites

        async with mcp_call("favorites_list") as call:
            rows = await list_favorites(call.session, call.user, skip=skip, limit=clamp_limit(limit))
            return dump_list(rows)

    @mcp.tool(description="Добавить документ в избранное.")
    async def favorites_add(document_id: str) -> dict[str, object]:
        from app.core.enums import FavoriteTargetType
        from app.portal_favorites.schemas.favorite import PortalFavoriteCreate
        from app.portal_favorites.services.favorite import add_favorite

        data = PortalFavoriteCreate(target_type=FavoriteTargetType.DOCUMENT, target_id=parse_uuid(document_id))
        async with mcp_call("favorites_add") as call:
            return dump_dict(await add_favorite(call.session, call.user, data))

    @mcp.tool(description="Убрать запись из избранного.")
    async def favorites_remove(favorite_id: str) -> dict[str, bool]:
        from app.portal_favorites.services.favorite import remove_favorite

        async with mcp_call("favorites_remove") as call:
            await remove_favorite(call.session, call.user, parse_uuid(favorite_id))
            return {"ok": True}

    @mcp.tool(description="Уведомления текущего пользователя.")
    async def notifications_list(
        limit: int = LIST_LIMIT_DEFAULT,
        skip: int = 0,
        unread_only: bool = True,
    ) -> list[dict[str, object]]:
        from app.portal_collab.schemas.notification import PortalNotificationRead
        from app.portal_collab.services._notification_queries import list_notifications

        async with mcp_call("notifications_list") as call:
            rows = await list_notifications(
                call.session,
                call.user,
                unread_only=unread_only,
                skip=skip,
                limit=clamp_limit(limit),
            )
            return dump_list([PortalNotificationRead.model_validate(row) for row in rows])

    @mcp.tool(
        description="Поиск по порталу в правах пользователя: документы, задачи, чаты, специалисты, календарь.",
    )
    async def portal_search(
        q: str,
        limit: int = LIST_LIMIT_DEFAULT,
        skip: int = 0,
        types: list[str] | None = None,
    ) -> list[dict[str, object]]:
        from app.portal_search.services.search_orchestrator import run_fulltext_search

        query = q.strip()
        resolved = types if types else list(PORTAL_SEARCH_ENTITY_TYPES)
        async with mcp_call("portal_search") as call:
            if len(query) < PORTAL_SEARCH_MIN_QUERY_LEN:
                raise ValidationError(
                    f"Запрос после удаления пробелов должен быть не короче {PORTAL_SEARCH_MIN_QUERY_LEN} символов",
                )
            unknown = set(resolved) - PORTAL_SEARCH_ENTITY_TYPES
            if unknown:
                raise ValidationError("Неизвестный тип поиска")
            hits = await run_fulltext_search(
                call.session,
                call.user,
                query,
                resolved,
                tag_slug=None,
                status_ids=None,
                skip=skip,
                limit=clamp_limit(limit),
                calendar_remote=_calendar_remote(call),
            )
            return dump_list(hits)
