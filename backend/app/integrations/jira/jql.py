"""Экранирование пользовательского ввода для JQL."""

from __future__ import annotations

import re

_JQL_ESCAPE_RE = re.compile(r'([\\"\'])')


def escape_jql_text(value: str) -> str:
    """Экранировать строку для вставки в JQL в двойных кавычках."""
    trimmed = "".join(ch for ch in value.strip() if ch.isprintable())
    if not trimmed:
        return ""
    return _JQL_ESCAPE_RE.sub(r"\\\1", trimmed)
