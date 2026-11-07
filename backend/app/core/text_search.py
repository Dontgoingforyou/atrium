"""Утилиты текстового поиска (SQL LIKE/ILIKE)."""

from __future__ import annotations


def escape_ilike_pattern(fragment: str) -> str:
    """Экранирование ``%``, ``_`` и ``\\`` для ``LIKE``/``ILIKE`` с ``escape='\\\\'``."""
    return fragment.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
