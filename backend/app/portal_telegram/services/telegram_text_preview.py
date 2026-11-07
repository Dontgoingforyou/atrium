from __future__ import annotations

import html
import re

from app.infrastructure.db.models.portal_user_profile import PortalUserProfile

TG_BODY_PREVIEW_MAX = 400
_HTML_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)

# В обычном тексте Telegram обрывает «упоминание» на пробеле (@Имя Фамилия → только @Имя).
_TG_AT_SAFE_REPLACE = "\uff20"  # FULLWIDTH COMMERCIAL AT (＠), без авто-линка


def profile_display(
    profile: PortalUserProfile | None,
    *,
    fallback_sub: str = "",
) -> str:
    """Читаемое имя из профиля или fallback по sub."""
    if profile is not None:
        d = (profile.full_name or profile.email or profile.username or profile.sub or "").strip()
        if d:
            return d
    return fallback_sub.strip()


def snippet(text: str, max_chars: int = TG_BODY_PREVIEW_MAX) -> str:
    """Один пробел между словами, усечение с многоточием."""
    t = (text or "").strip()
    t = re.sub(r"\s+", " ", t)
    if len(t) <= max_chars:
        return t
    return t[:max_chars].rstrip() + "…"


def plain_text_from_html(raw: str) -> str:
    """Убирает теги и раскодирует сущности (описания задач и комментарии из редактора)."""
    t = html.unescape(raw or "")
    t = _HTML_TAG_RE.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


def telegram_plain_preview(text: str, max_chars: int = TG_BODY_PREVIEW_MAX) -> str:
    """Текст для Telegram: без HTML и без обрыва «@имени» на пробеле."""
    base = plain_text_from_html(text)
    return snippet(base.replace("@", _TG_AT_SAFE_REPLACE), max_chars=max_chars)


def attachment_preview_label(count: int) -> str:
    if count <= 0:
        return ""
    if count == 1:
        return "Вложение"
    if 2 <= count <= 4:
        return f"{count} вложения"
    return f"{count} вложений"


def split_leading_portal_mention(
    body: str,
    labels_longest_first: list[str],
) -> tuple[str | None, str]:
    """Если тело начинается с @label из списка — вернуть (label, остаток). Иначе (None, исходное)."""
    s = body.strip()
    if not s:
        return None, ""
    for label in labels_longest_first:
        lab = label.strip()
        if not lab:
            continue
        prefix = "@" + lab
        if s.startswith(prefix):
            rest = s[len(prefix) :].lstrip()
            return lab, rest
    return None, body


def strip_isolated_at_signs(text: str) -> str:
    """Убирает «собаку» перед упоминаниями; email вида user@host не затрагивает."""
    return re.sub(r"(?<!\w)@(?=\S)", "", text or "")
