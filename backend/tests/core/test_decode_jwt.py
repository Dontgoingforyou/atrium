"""decode_jwt_payload_unverified — вспомогательный разбор, не auth."""

from __future__ import annotations

import base64
import json

from app.core.utils import decode_jwt_payload_unverified


def _unsigned(payload: dict[str, object]) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"hdr.{body}.sig"


def test_decode_jwt_payload_unverified_returns_claims() -> None:
    token = _unsigned({"sub": "u1", "exp": 1})
    assert decode_jwt_payload_unverified(token) == {"sub": "u1", "exp": 1}


def test_decode_jwt_payload_unverified_rejects_garbage() -> None:
    assert decode_jwt_payload_unverified("not-a-jwt") is None
    assert decode_jwt_payload_unverified("onlyonepart") is None
    assert decode_jwt_payload_unverified("") is None
    assert decode_jwt_payload_unverified("a.!!!notb64!!!.c") is None
