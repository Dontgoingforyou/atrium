from __future__ import annotations

from typing import Any

from markupsafe import Markup, escape


def _resolve_user(
    profile: Any,
    fallback_sub: str | None,
    fallback_name: str | None = None,
    fallback_email: str | None = None,
) -> str:
    """Вернуть читаемое имя пользователя.

    Приоритет: профиль Keycloak > fallback из денормализованных полей > sub.
    """
    name = (profile.full_name if profile else None) or fallback_name
    email = (profile.email if profile else None) or fallback_email
    if name and email:
        return f"{name} ({email})"
    if name:
        return name
    if email:
        return email
    return str(fallback_sub) if fallback_sub else "—"


def fmt_created_by(model: Any, attr: str) -> str:
    return _resolve_user(getattr(model, "created_by_profile", None), getattr(model, "created_by_sub", None))


def fmt_author_sub(model: Any, attr: str) -> str:
    return _resolve_user(getattr(model, "author_profile", None), getattr(model, "author_sub", None))


def fmt_user_sub(model: Any, attr: str) -> str:
    return _resolve_user(getattr(model, "user_profile", None), getattr(model, "user_sub", None))


def fmt_creator_sub(model: Any, attr: str) -> str:
    return _resolve_user(getattr(model, "creator_profile", None), getattr(model, "creator_sub", None))


def fmt_assignee_sub(model: Any, attr: str) -> str:
    profile = getattr(model, "assignee_profile", None)
    sub = getattr(model, "assignee_sub", None)
    if not sub:
        return "—"
    return _resolve_user(profile, sub)


def fmt_owner_sub(model: Any, attr: str) -> str:
    return _resolve_user(getattr(model, "owner_profile", None), getattr(model, "owner_sub", None))


def fmt_organizer_sub(model: Any, attr: str) -> str:
    return _resolve_user(getattr(model, "organizer_profile", None), getattr(model, "organizer_sub", None))


def fmt_recipient_sub(model: Any, attr: str) -> str:
    return _resolve_user(getattr(model, "recipient_profile", None), getattr(model, "recipient_sub", None))


def fmt_calendar_reminder_recipient(model: Any, attr: str) -> str:
    """Получатель из recipient_key (`sub:` / `email:`) — имя профиля или email."""
    key = str(getattr(model, attr, "") or "")
    if key.startswith("email:"):
        return key.removeprefix("email:") or "—"
    if key.startswith("sub:"):
        sub = key.removeprefix("sub:")
        return _resolve_user(getattr(model, "recipient_profile", None), sub)
    return key or "—"


def fmt_changed_by(model: Any, attr: str) -> str:
    return _resolve_user(getattr(model, "changed_by_profile", None), getattr(model, "changed_by_sub", None))


def fmt_comment_mentions(model: Any, attr: str) -> Markup:
    """Форматировать упоминания в комментарии: список имён/email или сокращённых sub."""
    mentions: list[str] = getattr(model, attr, []) or []
    if not mentions:
        return Markup("—")
    parts: list[str] = []
    for sub in mentions:
        mentioned_profiles = getattr(model, "_mentioned_profiles_cache", None)
        if mentioned_profiles:
            profile = next((p for p in mentioned_profiles if p.sub == sub), None)
            label = _resolve_user(profile, sub)
        else:
            label = sub[:12] + "…" if len(sub) > 12 else sub
        parts.append(
            f'<span style="display:inline-block;background:#e3f0ff;border-radius:4px;'
            f'padding:1px 6px;margin:2px 2px 2px 0;font-size:0.85em">@{escape(label)}</span>'
        )
    return Markup(" ".join(parts))


def fmt_mentioned_names(model: Any, attr: str) -> Markup:
    """Форматировать resolved-имена упоминаний (строка из column_property mentioned_names)."""
    names_str: str | None = getattr(model, attr, None)
    if not names_str:
        return Markup("—")
    parts = [
        f'<span style="display:inline-block;background:#e3f0ff;border-radius:4px;'
        f'padding:1px 6px;margin:2px 2px 2px 0;font-size:0.85em">@{escape(name.strip())}</span>'
        for name in names_str.split(", ")
        if name.strip()
    ]
    return Markup(" ".join(parts)) if parts else Markup("—")


def fmt_comment_parent_id(model: Any, attr: str) -> str:
    """Форматировать parent_id: показывает «—» если нет родителя, иначе укороченный ID."""
    parent_id = getattr(model, attr, None)
    if parent_id is None:
        return "—"
    return f"Ответ на комментарий ({str(parent_id)[:8]}…)"
