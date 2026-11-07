"""Склейка полнотекста и семантики для GET /portal/search/semantic."""

from __future__ import annotations

from typing import Any

from app.portal_search.schemas.search import (
    PortalSearchHitCalendarEvent,
    PortalSearchHitChatMessage,
    PortalSearchHitDocument,
    PortalSearchHitResponseUnion,
    PortalSearchHitSpecialist,
    PortalSearchHitTask,
)


def _key(hit: dict[str, Any]) -> tuple[str, str]:
    return (str(hit["entity_type"]), str(hit["entity_id"]))


def fulltext_hit_to_lexical_dict(
    hit: PortalSearchHitResponseUnion,
) -> dict[str, Any] | None:
    """Плоский semantic-hit; score появится при склейке, если вектор есть."""
    if isinstance(hit, PortalSearchHitDocument):
        return {
            "entity_type": "document",
            "entity_id": str(hit.document.id),
            "text_content": hit.document.title,
            "similarity_score": None,
            "meta": {},
        }
    if isinstance(hit, PortalSearchHitTask):
        title = hit.task.title
        extra = hit.task.description_excerpt
        text = f"{title} {extra}".strip() if extra else title
        return {
            "entity_type": "task",
            "entity_id": str(hit.task.id),
            "text_content": text,
            "similarity_score": None,
            "meta": {},
        }
    if isinstance(hit, PortalSearchHitChatMessage):
        return {
            "entity_type": "chat_message",
            "entity_id": str(hit.message.id),
            "text_content": hit.message.body_excerpt,
            "similarity_score": None,
            "meta": {"chat_id": str(hit.chat.id)},
        }
    if isinstance(hit, PortalSearchHitSpecialist):
        spec = hit.specialist
        return {
            "entity_type": "specialist",
            "entity_id": spec.sub,
            "text_content": spec.full_name or spec.email or spec.sub,
            "similarity_score": None,
            "meta": {"specialist_sub": spec.sub},
        }
    if isinstance(hit, PortalSearchHitCalendarEvent):
        ev = hit.calendar_event
        return {
            "entity_type": "calendar_event",
            "entity_id": str(ev.id),
            "text_content": ev.title,
            "similarity_score": None,
            "meta": {},
        }
    return None


def merge_lexical_first(
    lexical_hits: list[dict[str, Any]],
    semantic_hits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Полнотекст первым (слово «бенч» в тексте), затем семантика без дублей.

    Если тот же ключ есть в семантике — берём её score и excerpt.
    """
    sem_by_key = {_key(h): h for h in semantic_hits}
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for hit in lexical_hits:
        key = _key(hit)
        if key in seen:
            continue
        seen.add(key)
        out.append(sem_by_key.get(key, hit))
    for hit in semantic_hits:
        key = _key(hit)
        if key in seen:
            continue
        seen.add(key)
        out.append(hit)
    return out
