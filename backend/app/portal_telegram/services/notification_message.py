from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from sqlalchemy import inspect as sa_inspect

from app.core.config import Settings
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.email.reminder_format import format_reminder_when
from app.portal_telegram.services.calendar_meeting_url import calendar_meeting_http_url
from app.portal_telegram.services.telegram_text_preview import (
    plain_text_from_html,
    split_leading_portal_mention,
    strip_isolated_at_signs,
    telegram_plain_preview,
)

_MENTION_TYPES = frozenset({"task_mention", "document_mention"})


def _header_emoji_for_portal_notification(notif_type: str) -> str:
    if notif_type == "task_assigned":
        return "📋"
    if notif_type in {"task_due_soon", "task_overdue"}:
        return "⏰"
    if notif_type == "task_comment":
        return "💬"
    if notif_type == "document_trashed":
        return "🗑"
    if notif_type in _MENTION_TYPES:
        return "📌"
    if notif_type.startswith("calendar_"):
        return "📅"
    return "🔔"


def _header_text_for_portal_notification(notif_type: str) -> str:
    if notif_type.startswith("calendar_"):
        return "Событие!"
    return "Новое уведомление на портале"


def format_portal_notification_telegram(
    notif: PortalNotification,
    settings: Settings,
    *,
    mention_labels_longest_first: list[str] | None = None,
) -> tuple[str, str]:
    """Текст сообщения и полный URL для кнопки или для HTML-ссылки в тексте (при http)."""
    base = settings.portal_public_url.strip().rstrip("/")
    title, path = _title_and_path(notif)
    link = f"{base}{path}" if path else base

    lines: list[str] = []
    lines.append(
        f"{_header_emoji_for_portal_notification(notif.type)} {_header_text_for_portal_notification(notif.type)}"
    )
    lines.append("")
    lines.append(title)

    comment_raw = _comment_body_for_notification(notif)
    comment_plain = plain_text_from_html(comment_raw) if comment_raw else ""
    if comment_plain and notif.type in _MENTION_TYPES:
        labels = mention_labels_longest_first or []
        mentioned_label, remainder = split_leading_portal_mention(comment_plain, labels)
        if mentioned_label:
            if remainder.strip():
                lines.append("")
                lines.append(f"«{telegram_plain_preview(remainder)}»")
        else:
            cleaned = strip_isolated_at_signs(comment_plain)
            lines.append("")
            lines.append(f"«{telegram_plain_preview(cleaned)}»")
    elif comment_plain:
        lines.append("")
        lines.append(f"«{telegram_plain_preview(comment_plain)}»")
    elif notif.type == "task_assigned":
        task = None if "task" in sa_inspect(notif).unloaded else notif.task
        if task is not None:
            desc = (task.description or "").strip()
            if desc:
                lines.append("")
                lines.append(f"«{telegram_plain_preview(desc)}»")

    return ("\n".join(lines), link)


def _comment_body_for_notification(notif: PortalNotification) -> str:
    t = notif.type
    unloaded = sa_inspect(notif).unloaded
    if t in {"task_mention", "task_comment"} and "comment" not in unloaded and notif.comment is not None:
        return (notif.comment.body or "").strip()
    if t == "document_mention" and "document_comment" not in unloaded and notif.document_comment is not None:
        return (notif.document_comment.body or "").strip()
    return ""


def _loaded_rel_title(obj: object | None, *, fallback: str) -> str:
    """Заголовок связанной сущности без lazy-load (избегает MissingGreenlet в sync-форматтере)."""
    if obj is None:
        return fallback
    title = getattr(obj, "title", None)
    if isinstance(title, str) and title.strip():
        return title
    return fallback


def _calendar_event_body_lines(
    *,
    title: str,
    starts_at: datetime | None,
    location: str | None,
    description: str | None,
    timezone: str,
) -> list[str]:
    """Тело TG без подписей: «название», время, место; URL из описания — одной строкой."""
    lines = [f"«{title}»"]
    if starts_at is not None:
        lines.append(format_reminder_when(starts_at, timezone=timezone))
    loc = location.strip() if location and location.strip() else ""
    if loc:
        lines.append(loc)
    meeting = calendar_meeting_http_url(location=location, description=description)
    if meeting and meeting not in loc:
        lines.append(meeting)
    return lines


def _calendar_event_message(
    notif: PortalNotification,
    *,
    rel_event: object | None,
) -> tuple[str, str]:
    title = _loaded_rel_title(rel_event, fallback="событие")
    eid = notif.calendar_event_id
    path = f"/calendar?event={eid}" if eid else "/calendar"
    starts_at = notif.calendar_occurrence_starts_at
    location: str | None = None
    description: str | None = None
    timezone = "UTC"
    if rel_event is not None:
        if starts_at is None:
            starts_at = getattr(rel_event, "starts_at", None)
        location = getattr(rel_event, "location", None)
        description = getattr(rel_event, "description", None)
        tz_raw = getattr(rel_event, "timezone", None)
        if isinstance(tz_raw, str) and tz_raw.strip():
            timezone = tz_raw
    body = "\n".join(
        _calendar_event_body_lines(
            title=title,
            starts_at=starts_at if isinstance(starts_at, datetime) else None,
            location=location if isinstance(location, str) else None,
            description=description if isinstance(description, str) else None,
            timezone=timezone,
        )
    )
    return (body, path)


def _title_and_path(notif: PortalNotification) -> tuple[str, str]:
    t = notif.type
    state = sa_inspect(notif)
    unloaded = state.unloaded

    def _rel(name: str) -> object | None:
        if name in unloaded:
            return None
        return getattr(notif, name, None)

    if t == "task_assigned":
        task_title = _loaded_rel_title(_rel("task"), fallback="задача")
        tid = notif.task_id
        path = f"/tasks?task={tid}" if tid else ""
        return (f"Вам назначена задача: «{task_title}»", path)
    if t == "task_due_soon":
        task_title = _loaded_rel_title(_rel("task"), fallback="задача")
        tid = notif.task_id
        path = f"/tasks?task={tid}" if tid else ""
        return (f"Срок задачи через 2 дня: «{task_title}»", path)
    if t == "task_overdue":
        task_title = _loaded_rel_title(_rel("task"), fallback="задача")
        tid = notif.task_id
        path = f"/tasks?task={tid}" if tid else ""
        return (f"Задача просрочена: «{task_title}»", path)
    if t == "task_mention":
        task_title = _loaded_rel_title(_rel("task"), fallback="задача")
        tid = notif.task_id
        path = f"/tasks?task={tid}" if tid else ""
        return (f"Вас упомянули в задаче: «{task_title}»", path)
    if t == "task_comment":
        task_title = _loaded_rel_title(_rel("task"), fallback="задача")
        tid = notif.task_id
        path = f"/tasks?task={tid}" if tid else ""
        return (f"Новый комментарий в задаче: «{task_title}»", path)
    if t == "document_mention":
        doc_title = _loaded_rel_title(_rel("document"), fallback="документ")
        did = notif.document_id
        path = f"/documents/{quote(str(did), safe='')}" if did else ""
        line = f"Вас упомянули в комментарии к документу: «{doc_title}»"
        return (line, path)
    if t == "document_trashed":
        doc_title = _loaded_rel_title(_rel("document"), fallback="документ")
        return (f"Документ «{doc_title}» перемещён в корзину", "/p/trash")
    if t in {"calendar_invite", "calendar_reminder", "calendar_event_updated"}:
        return _calendar_event_message(notif, rel_event=_rel("calendar_event"))
    if t == "calendar_share":
        title = _loaded_rel_title(_rel("calendar"), fallback=notif.context_title or "календарь")
        cid = notif.calendar_id
        path = f"/calendar?calendar={cid}" if cid else "/calendar"
        return (f"«{title}»", path)
    if t == "calendar_event_cancelled":
        title = _loaded_rel_title(
            _rel("calendar_event"),
            fallback=notif.context_title or "событие",
        )
        return (f"«{title}»", "/calendar")
    if t == "calendar_share_revoked":
        title = _loaded_rel_title(_rel("calendar"), fallback=notif.context_title or "календарь")
        return (f"«{title}»", "/calendar")
    return ("Новое уведомление", "")
