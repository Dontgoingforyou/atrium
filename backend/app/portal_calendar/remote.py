"""Вызов микросервиса календаря. Экран Космолета остаётся на прежних адресах."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps_auth import extract_bearer_token
from app.core.config import get_settings
from app.core.enums import CalendarMemberRole
from app.core.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.core.utils import decode_jwt_payload_unverified
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_calendar.schemas.calendar import (
    AttendeeRead,
    CalendarEventSearchHitRead,
    CalendarRead,
    EventOccurrenceRead,
    EventRead,
    ReminderRead,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_PAGE = 200
# Страница больше 100 микросервис не принимает: отказ гасит весь поиск портала.
_REMOTE_EVENT_SEARCH_QUERY_MAX = 200
_REMOTE_EVENT_SEARCH_LIMIT_MAX = 100
# SSO-sub, который микросервис пишет владельцем, а профиль Космолета помнит другим id.
_learned_owners: dict[str, set[str]] = {}
_STATUS = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: BadRequestError,
}


def _owner_aliases(token: str) -> set[str]:
    """Тот же человек в токене. Подпись уже проверена входом в портал."""
    payload = decode_jwt_payload_unverified(token)
    if not payload:
        return set()
    found: set[str] = set()
    for key in ("public_id", "keycloak_id", "sub"):
        value = payload.get(key)
        if not isinstance(value, str):
            continue
        text = value.strip()
        if text and "@" not in text:
            found.add(text)
    return found


def _portal_person(remote_sub: str, user_sub: str, aliases: set[str] | None) -> str:
    if remote_sub == user_sub or (aliases and remote_sub in aliases):
        return user_sub
    return remote_sub


def remote_event_search_query_fits(q: str) -> bool:
    """Сервис календаря принимает строку не длиннее 200 символов."""
    return len(q) <= _REMOTE_EVENT_SEARCH_QUERY_MAX


def opened_remote(
    user: UserPublic,
    authorization: str | None,
    http: httpx.AsyncClient,
) -> CalendarRemote | None:
    """Клиент микросервиса или None, если адрес не задан."""
    settings = get_settings()
    base = settings.calendar_service_url.strip().rstrip("/")
    if not base:
        return None
    product = settings.calendar_product.strip()
    if not product:
        raise ServiceUnavailableError("Календарь временно недоступен")
    token = extract_bearer_token(authorization)
    if token is None:
        raise UnauthorizedError("Требуется заголовок Authorization: Bearer")
    if not user.gid_number:
        raise BadRequestError("Нет отдела вызывающего")
    aliases = _owner_aliases(token) | _learned_owners.get(user.sub, set())
    return CalendarRemote(http, base, token, user.gid_number, user.sub, product, aliases)


def calendar_remote_for_search(
    user: UserPublic,
    authorization: str | None,
    http: httpx.AsyncClient,
) -> tuple[CalendarRemote | None, bool]:
    """Клиент календаря для общего поиска и флаг «не подменять локальной базой».

    Адрес не задан — ``(None, False)``, поиск событий идёт по таблицам портала.
    Адрес задан, но календарь не открылся — ``(None, True)``: события пропускаем, остальной поиск жив.
    """
    try:
        return opened_remote(user, authorization, http), False
    except AppError:
        logger.warning("Календарь недоступен для поиска: user_sub=%s", user.sub)
        return None, True


def require_remote(
    user: UserPublic,
    authorization: str | None,
    http: httpx.AsyncClient,
) -> CalendarRemote:
    """Календарь, события и участники живут в микросервисе."""
    remote = opened_remote(user, authorization, http)
    if remote is None:
        raise ServiceUnavailableError("Календарь временно недоступен")
    return remote


def calendar_from_remote(
    raw: dict[str, Any],
    user_sub: str,
    aliases: set[str] | None = None,
) -> CalendarRead:
    owner = _portal_person(str(raw["owner_sub"]), user_sub, aliases)
    role = CalendarMemberRole.OWNER.value if owner == user_sub else CalendarMemberRole.VIEWER.value
    return CalendarRead(
        id=uuid.UUID(str(raw["id"])),
        owner_sub=owner,
        title=str(raw["title"]),
        color=str(raw["color"]),
        timezone=str(raw["timezone"]),
        is_primary=bool(raw["is_primary"]),
        show_to_other_departments=bool(raw.get("show_to_other_departments")),
        my_role=role,
        created_at=_EPOCH,
        updated_at=_EPOCH,
        members=[],
    )


def event_from_remote(raw: dict[str, Any], user_sub: str = "", aliases: set[str] | None = None) -> EventRead:
    organizer = str(raw["organizer_sub"])
    if user_sub:
        organizer = _portal_person(organizer, user_sub, aliases)
    return EventRead(
        id=uuid.UUID(str(raw["id"])),
        calendar_id=uuid.UUID(str(raw["calendar_id"])),
        organizer_sub=organizer,
        title=str(raw["title"]),
        description=raw.get("description"),
        location=raw.get("location"),
        starts_at=_dt(raw["starts_at"]),
        ends_at=_dt(raw["ends_at"]) if raw.get("ends_at") else None,
        timezone=str(raw["timezone"]),
        rrule=raw.get("rrule"),
        color=raw.get("color"),
        version=int(raw["version"]),
        created_at=_EPOCH,
        updated_at=_EPOCH,
        attendees=[_attendee(item) for item in raw.get("attendees") or []],
        reminders=[_reminder(item) for item in raw.get("reminders") or []],
    )


def occurrence_kept_on_peer_grid(
    *,
    owner_sub: str,
    raw_owner_sub: str,
    peer_user_sub: str,
    attendees: list[dict[str, Any]] | None,
    peer_email: str | None,
) -> bool:
    """Чужой просмотр: календари человека и события, куда его пригласили."""
    peer = peer_user_sub.strip()
    if owner_sub == peer or raw_owner_sub == peer:
        return True
    email = (peer_email or "").strip().lower()
    for item in attendees or []:
        if str(item.get("user_sub") or "").strip() == peer:
            return True
        attendee_email = str(item.get("email") or "").strip().lower()
        if email and attendee_email == email:
            return True
    return False


def occurrence_from_remote(
    raw: dict[str, Any],
    *,
    owner_sub: str,
    user_sub: str,
    aliases: set[str] | None = None,
) -> EventOccurrenceRead:
    return EventOccurrenceRead(
        event_id=uuid.UUID(str(raw["event_id"])),
        calendar_id=uuid.UUID(str(raw["calendar_id"])),
        calendar_color=str(raw["calendar_color"]),
        color=raw.get("color"),
        original_start=_dt(raw["original_start"]),
        starts_at=_dt(raw["starts_at"]),
        ends_at=_dt(raw["ends_at"]) if raw.get("ends_at") else None,
        title=str(raw["title"]),
        description=raw.get("description"),
        location=raw.get("location"),
        timezone=str(raw["timezone"]),
        rrule=raw.get("rrule"),
        organizer_sub=_portal_person(str(raw["organizer_sub"]), user_sub, aliases),
        is_cancelled=False,
        is_peer_view=owner_sub != user_sub,
        attendees=[_attendee(item) for item in raw.get("attendees") or []],
        reminders=[_reminder(item) for item in raw.get("reminders") or []],
    )


def search_hit_from_remote(raw: dict[str, Any], calendar_title: str) -> CalendarEventSearchHitRead:
    return CalendarEventSearchHitRead(
        id=uuid.UUID(str(raw["id"])),
        calendar_id=uuid.UUID(str(raw["calendar_id"])),
        title=str(raw["title"]),
        starts_at=_dt(raw["starts_at"]),
        ends_at=_dt(raw["ends_at"]) if raw.get("ends_at") else None,
        calendar_title=calendar_title,
        location=raw.get("location"),
    )


async def attendee_bodies(session: AsyncSession, attendees: list[dict[str, Any]]) -> list[dict[str, str | None]]:
    """Микросервис принимает почту. Sub Космолет достаёт из своего профиля."""
    subs = [str(item["user_sub"]) for item in attendees if item.get("user_sub")]
    if not subs:
        return []
    rows = (
        await session.execute(
            select(PortalUserProfile.sub, PortalUserProfile.email).where(PortalUserProfile.sub.in_(subs))
        )
    ).all()
    by_sub = {sub: (email or "").strip().lower() for sub, email in rows}
    result: list[dict[str, str | None]] = []
    for sub in subs:
        email = by_sub.get(sub) or ""
        if "@" not in email:
            raise BadRequestError("У участника нет почты в профиле")
        result.append({"email": email, "user_sub": sub})
    return result


class CalendarRemote:
    def __init__(
        self,
        http: httpx.AsyncClient,
        base: str,
        token: str,
        department: str,
        user_sub: str,
        product: str,
        aliases: set[str] | None = None,
    ) -> None:
        self._http = http
        self._base = base
        self._token = token
        self._department = department
        self._user_sub = user_sub
        self._product = product
        self._aliases = set(aliases or ())

    def _calendar(self, raw: dict[str, Any]) -> CalendarRead:
        return calendar_from_remote(raw, self._user_sub, self._aliases)

    def _event(self, raw: dict[str, Any]) -> EventRead:
        return event_from_remote(raw, self._user_sub, self._aliases)

    def _learn_owner(self, remote_sub: str) -> None:
        if not remote_sub or remote_sub == self._user_sub:
            return
        self._aliases.add(remote_sub)
        _learned_owners.setdefault(self._user_sub, set()).add(remote_sub)

    async def list_calendars(self) -> list[CalendarRead]:
        items = await self._all_calendars()
        return [self._calendar(item) for item in items]

    async def primary_for(self, owner_sub: str) -> CalendarRead:
        items = await self._all_calendars()
        aliases = self._aliases if owner_sub == self._user_sub else None
        owned = [item for item in items if _portal_person(str(item["owner_sub"]), owner_sub, aliases) == owner_sub]
        primary = next((item for item in owned if item.get("is_primary")), None)
        chosen = primary or (owned[0] if owned else None)
        if chosen is None:
            raise NotFoundError("Календарь не найден")
        return self._calendar(chosen)

    async def create_calendar(self, payload: dict[str, Any]) -> CalendarRead:
        raw = await self._send("POST", "/calendars", json=payload)
        self._learn_owner(str(raw.get("owner_sub") or ""))
        return self._calendar(raw)

    async def get_calendar(self, calendar_id: uuid.UUID) -> CalendarRead:
        raw = await self._send("GET", f"/calendars/{calendar_id}")
        return self._calendar(raw)

    async def set_show(self, calendar_id: uuid.UUID, enabled: bool) -> CalendarRead:
        raw = await self._send("PATCH", f"/calendars/{calendar_id}/show", json={"enabled": enabled})
        return self._calendar(raw)

    async def update_calendar(self, calendar_id: uuid.UUID, payload: dict[str, Any]) -> CalendarRead:
        raw = await self._send("PATCH", f"/calendars/{calendar_id}", json=payload)
        return self._calendar(raw)

    async def delete_calendar(self, calendar_id: uuid.UUID) -> None:
        await self._send("DELETE", f"/calendars/{calendar_id}")

    async def issue_ws_ticket(self) -> str:
        raw = await self._send("POST", "/calendars/ws-ticket")
        return str(raw["ticket"])

    async def list_occurrences(
        self,
        *,
        starts: datetime,
        ends: datetime,
        calendar_ids: list[uuid.UUID] | None,
        peer_user_sub: str | None,
        peer_email: str | None = None,
    ) -> list[EventOccurrenceRead]:
        owners = {str(item["id"]): str(item["owner_sub"]) for item in await self._all_calendars()}
        params: list[tuple[str, str]] = [("from", starts.isoformat()), ("to", ends.isoformat())]
        for calendar_id in calendar_ids or []:
            params.append(("calendar_id", str(calendar_id)))
        rows = await self._send("GET", "/calendars/occurrences", params=params)
        peer = (peer_user_sub or "").strip()
        result: list[EventOccurrenceRead] = []
        for raw in rows:
            raw_owner = owners.get(str(raw["calendar_id"]), "")
            owner = _portal_person(raw_owner, self._user_sub, self._aliases)
            if peer and not occurrence_kept_on_peer_grid(
                owner_sub=owner,
                raw_owner_sub=raw_owner,
                peer_user_sub=peer,
                attendees=raw.get("attendees"),
                peer_email=peer_email,
            ):
                continue
            result.append(
                occurrence_from_remote(raw, owner_sub=owner, user_sub=self._user_sub, aliases=self._aliases),
            )
        return result

    async def search_events(self, q: str, skip: int, limit: int) -> tuple[list[CalendarEventSearchHitRead], int]:
        titles = {str(item["id"]): str(item["title"]) for item in await self._all_calendars()}
        page = await self._send(
            "GET",
            "/calendars/events/search",
            params={"q": q, "skip": skip, "limit": min(limit, _REMOTE_EVENT_SEARCH_LIMIT_MAX)},
        )
        hits = [search_hit_from_remote(item, titles.get(str(item["calendar_id"]), "")) for item in page["items"]]
        return hits, int(page["total"])

    async def create_event(self, calendar_id: uuid.UUID, payload: dict[str, Any]) -> EventRead:
        raw = await self._send("POST", f"/calendars/{calendar_id}/events", json=payload)
        return self._event(raw)

    async def get_event(self, event_id: uuid.UUID, calendar_id: uuid.UUID | None = None) -> EventRead:
        resolved = calendar_id or await self._calendar_of_event(event_id)
        raw = await self._send("GET", f"/calendars/{resolved}/events/{event_id}")
        return self._event(raw)

    async def update_event(
        self,
        event_id: uuid.UUID,
        payload: dict[str, Any],
        calendar_id: uuid.UUID | None = None,
    ) -> EventRead:
        resolved = calendar_id or await self._calendar_of_event(event_id)
        raw = await self._send("PATCH", f"/calendars/{resolved}/events/{event_id}", json=payload)
        return self._event(raw)

    async def delete_event(self, event_id: uuid.UUID, calendar_id: uuid.UUID | None = None) -> None:
        resolved = calendar_id or await self._calendar_of_event(event_id)
        await self._send("DELETE", f"/calendars/{resolved}/events/{event_id}")

    async def add_attendee(self, event_id: uuid.UUID, payload: dict[str, str | None]) -> AttendeeRead:
        calendar_id = await self._calendar_of_event(event_id)
        raw = await self._send("POST", f"/calendars/{calendar_id}/events/{event_id}/attendees", json=payload)
        return _attendee(raw)

    async def remove_attendee(self, event_id: uuid.UUID, attendee_id: uuid.UUID) -> None:
        calendar_id = await self._calendar_of_event(event_id)
        await self._send("DELETE", f"/calendars/{calendar_id}/events/{event_id}/attendees/{attendee_id}")

    async def override_occurrence(
        self,
        event_id: uuid.UUID,
        payload: dict[str, Any],
        calendar_id: uuid.UUID | None = None,
    ) -> EventRead:
        resolved = calendar_id or await self._calendar_of_event(event_id)
        await self._send("POST", f"/calendars/{resolved}/events/{event_id}/overrides", json=payload)
        return await self.get_event(event_id, resolved)

    async def _calendar_of_event(self, event_id: uuid.UUID) -> uuid.UUID:
        wanted = str(event_id)
        for item in await self._all_calendars():
            calendar_id = uuid.UUID(str(item["id"]))
            skip = 0
            while True:
                page = await self._send("GET", f"/calendars/{calendar_id}", params={"skip": skip, "limit": _PAGE})
                for event in page.get("events") or []:
                    if str(event["id"]) == wanted:
                        return calendar_id
                total = int(page.get("events_total") or 0)
                skip += _PAGE
                if skip >= total:
                    break
        raise NotFoundError("Событие не найдено")

    async def _all_calendars(self) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        skip = 0
        while True:
            page = await self._send("GET", "/calendars", params={"skip": skip, "limit": _PAGE})
            collected.extend(page["items"])
            if skip + _PAGE >= int(page["total"]):
                return collected
            skip += _PAGE

    async def _send(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._http.request(
                method,
                f"{self._base}{path}",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "X-Product": self._product,
                    "X-Department": self._department,
                },
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError("Календарь временно недоступен") from exc
        if response.status_code >= 400:
            _raise_remote(response)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()


def _raise_remote(response: httpx.Response) -> None:
    message = "Календарь отклонил запрос"
    try:
        body = response.json()
        if isinstance(body, dict) and body.get("message"):
            message = str(body["message"])
    except ValueError:
        message = "Календарь отклонил запрос"
    error_cls = _STATUS.get(response.status_code, ServiceUnavailableError)
    raise error_cls(message)


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _attendee(raw: dict[str, Any]) -> AttendeeRead:
    return AttendeeRead(
        id=uuid.UUID(str(raw["id"])),
        user_sub=raw.get("user_sub"),
        email=str(raw["email"]),
        status=str(raw.get("status") or "accepted"),
        responded_at=None,
        created_at=_EPOCH,
    )


def _reminder(raw: dict[str, Any]) -> ReminderRead:
    return ReminderRead(
        id=uuid.UUID(str(raw["id"])),
        offset_minutes=int(raw["offset_minutes"]),
        channel=str(raw["channel"]),
    )
