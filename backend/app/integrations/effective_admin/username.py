"""Утилиты username для Effective Admin photo API."""

from __future__ import annotations

import re

_USERNAME_RE = re.compile(r"^[a-z0-9._+-]+$")


def username_from_email(email: str | None) -> str | None:
    """Local-part email в нижнем регистре без ``@`` — контракт EA ``{username}``."""
    if not email or "@" not in email:
        return None
    local = email.split("@", 1)[0].strip().lower()
    if not local or ".." in local or not _USERNAME_RE.fullmatch(local):
        return None
    return local
