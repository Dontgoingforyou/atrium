from __future__ import annotations

import re

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def validate_tag_color_hex(hex_color: str) -> str:
    """Проверяет формат #RRGGBB. Theme-aware ограничения — на фронте."""
    if not _HEX_RE.match(hex_color):
        raise ValueError("color должен быть в формате #RRGGBB")
    return hex_color.upper()
