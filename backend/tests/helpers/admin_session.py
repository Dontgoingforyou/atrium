"""Кодирование/декодирование cookie ``admin_session`` (Starlette SessionMiddleware)."""

from __future__ import annotations

import json
from base64 import b64decode, b64encode
from typing import Any

import itsdangerous

ADMIN_SESSION_SECRET = "dev-secret-change-me"
ADMIN_SESSION_COOKIE = "admin_session"


def encode_admin_session(payload: dict[str, Any]) -> str:
    signer = itsdangerous.TimestampSigner(ADMIN_SESSION_SECRET)
    data = b64encode(json.dumps(payload).encode("utf-8"))
    return signer.sign(data).decode("utf-8")


def decode_admin_session_cookie(set_cookie_header: str) -> dict[str, object]:
    part = set_cookie_header.split(";", 1)[0]
    _, encoded = part.split("=", 1)
    signer = itsdangerous.TimestampSigner(ADMIN_SESSION_SECRET)
    raw = signer.unsign(encoded.strip().encode("utf-8"), max_age=14 * 24 * 60 * 60)
    return json.loads(b64decode(raw))
