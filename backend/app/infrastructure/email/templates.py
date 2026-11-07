"""Тексты писем календаря."""

from __future__ import annotations

from datetime import datetime
from html import escape

from app.infrastructure.email.reminder_format import format_reminder_when


def event_invite_email(
    *,
    event_title: str,
    starts_at: datetime,
    location: str | None,
    invite_url: str,
    organizer_name: str,
) -> tuple[str, str, str]:
    subject = f"Приглашение: {event_title}"
    when = starts_at.strftime("%d.%m.%Y %H:%M UTC")
    loc = f"\nМесто: {location}" if location else ""
    text = f"{organizer_name} приглашает вас на «{event_title}».\nКогда: {when}{loc}\n\nПринять: {invite_url}\n"
    org_h = escape(organizer_name)
    title_h = escape(event_title)
    when_h = escape(when)
    url_h = escape(invite_url, quote=True)
    loc_html = f"<p>Место: {escape(location)}</p>" if location else ""
    html = (
        f"<p><strong>{org_h}</strong> приглашает вас на «{title_h}».</p>"
        f"<p>Когда: {when_h}</p>"
        f"{loc_html}"
        f'<p><a href="{url_h}">Принять приглашение</a></p>'
    )
    return subject, text, html


def calendar_share_email(
    *,
    calendar_title: str,
    role: str,
    invite_url: str,
    organizer_name: str,
) -> tuple[str, str, str]:
    subject = f"Доступ к календарю «{calendar_title}»"
    text = (
        f"{organizer_name} открыл(а) вам доступ к календарю «{calendar_title}» "
        f"(роль: {role}).\n\nПринять: {invite_url}\n"
    )
    html = (
        f"<p><strong>{escape(organizer_name)}</strong> открыл(а) вам доступ к календарю "
        f"«{escape(calendar_title)}» (роль: {escape(role)}).</p>"
        f'<p><a href="{escape(invite_url, quote=True)}">Принять доступ</a></p>'
    )
    return subject, text, html


def reminder_email(
    *,
    event_title: str,
    starts_at: datetime,
    location: str | None,
    timezone: str = "UTC",
) -> tuple[str, str, str]:
    subject = f"Напоминание: {event_title}"
    when = format_reminder_when(starts_at, timezone=timezone)
    text = f"Скоро начнётся «{event_title}» ({when})."
    if location:
        text += f"\nМесто: {location}"
    html = f"<p>Скоро начнётся «{escape(event_title)}» ({escape(when)}).</p>"
    if location:
        html += f"<p>Место: {escape(location)}</p>"
    return subject, text, html
