"""Извлечение текстового представления сущностей портала для векторизации."""

from __future__ import annotations

from app.core.portal_search_constants import EMBEDDING_TEXT_MAX_CHARS

_MAX_CHARS = EMBEDDING_TEXT_MAX_CHARS


def _trim(text: str | None) -> str:
    return (text or "").strip()


def _cap(text: str) -> str:
    """Ограничивает длину текста перед отправкой в API эмбеддингов."""
    return text[:_MAX_CHARS] if len(text) > _MAX_CHARS else text


# ─── Извлечение текста ───────────────────────────────────────────────────────


def document_to_text(title: str, body: str | None) -> str:
    """Документ: заголовок + тело."""
    parts = [_trim(title)]
    body_stripped = _trim(body)
    if body_stripped:
        parts.append(body_stripped)
    return _cap("\n\n".join(parts))


def task_to_text(title: str, description: str | None) -> str:
    """Задача: заголовок + описание."""
    parts = [_trim(title)]
    desc = _trim(description)
    if desc:
        parts.append(desc)
    return _cap("\n\n".join(parts))


def chat_message_to_text(body: str) -> str:
    """Сообщение чата: тело."""
    return _cap(_trim(body))


def agreement_to_text(body: str) -> str:
    """Договорённость: тело."""
    return _cap(_trim(body))


def learning_material_to_text(title: str, body: str | None) -> str:
    """Учебный материал: заголовок + тело."""
    parts = [_trim(title)]
    body_stripped = _trim(body)
    if body_stripped:
        parts.append(body_stripped)
    return _cap("\n\n".join(parts))


def calendar_event_to_text(title: str, description: str | None, location: str | None) -> str:
    """Событие календаря: заголовок + описание + место."""
    parts = [_trim(title)]
    desc = _trim(description)
    if desc:
        parts.append(desc)
    loc = _trim(location)
    if loc:
        parts.append(loc)
    return _cap("\n\n".join(parts))


def calendar_event_meta(*, calendar_id: str, organizer_sub: str) -> dict[str, str]:
    return {"calendar_id": calendar_id, "organizer_sub": organizer_sub}


# ─── Метаданные для фильтрации ───────────────────────────────────────────────


def document_meta(
    author_sub: str,
) -> dict[str, str]:
    return {
        "author_sub": author_sub,
    }


def task_meta(
    creator_sub: str,
    assignee_sub: str | None,
    status: str,
) -> dict[str, str]:
    meta: dict[str, str] = {
        "creator_sub": creator_sub,
        "status": status,
    }
    if assignee_sub:
        meta["assignee_sub"] = assignee_sub
    return meta


def chat_message_meta(
    chat_id: str,
    author_sub: str,
) -> dict[str, str]:
    return {
        "chat_id": chat_id,
        "author_sub": author_sub,
    }


def agreement_meta(
    created_by_sub: str,
    status: str,
) -> dict[str, str]:
    return {
        "created_by_sub": created_by_sub,
        "status": status,
    }


def learning_material_meta(
    created_by_sub: str,
    status: str,
    material_type: str,
) -> dict[str, str]:
    return {
        "created_by_sub": created_by_sub,
        "status": status,
        "material_type": material_type,
    }


# ─── Специалисты ─────────────────────────────────────────────────────────────


def specialist_to_text(
    full_name: str | None,
    email: str | None,
    location: str | None,
    telegram: str | None,
) -> str:
    """Специалист: имя + email + локация + telegram для семантической индексации."""
    parts = [_trim(full_name), _trim(email), _trim(location), _trim(telegram)]
    return _cap(" ".join(p for p in parts if p))


def specialist_note_to_text(body: str) -> str:
    """Заметка о специалисте: тело заметки."""
    return _cap(_trim(body))


def specialist_meta(specialist_sub: str) -> dict[str, str]:
    return {"specialist_sub": specialist_sub}


def specialist_note_meta(specialist_sub: str, author_sub: str) -> dict[str, str]:
    return {"specialist_sub": specialist_sub, "author_sub": author_sub}
