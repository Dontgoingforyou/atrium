"""Лимиты списков и полей модуля специалистов (не пагинация SPA)."""

from __future__ import annotations

from app.core.portal_search_constants import EMBEDDING_TEXT_MAX_CHARS

# Совпадает с лимитом текста эмбеддинга (portal_search).
SPECIALIST_NOTE_BODY_MAX_LENGTH: int = EMBEDDING_TEXT_MAX_CHARS

# Safety cap SQL: контракт остаётся list[T], без PagedResponse (SPA).
SPECIALIST_BOARD_LIST_CAP: int = 2000
SPECIALIST_NOTES_LIST_CAP: int = 500
SPECIALIST_LINKS_LIST_CAP: int = 200
