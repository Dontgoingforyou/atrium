"""JWT service account для Google OAuth2 (без google-auth)."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def parse_service_account_json(raw: str) -> dict[str, Any]:
    """Разбирает JSON ключ SA. При ошибке не возвращает сырой текст."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("невалидный JSON service account") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON service account должен быть объектом")
    email = payload.get("client_email")
    key = payload.get("private_key")
    if not isinstance(email, str) or not email or not isinstance(key, str) or not key:
        raise ValueError("в JSON service account нет client_email или private_key")
    return {"client_email": email, "private_key": key}


def build_service_account_jwt(account: dict[str, Any], *, now: datetime | None = None) -> str:
    issued = now or datetime.now(UTC)
    iat = int(issued.timestamp())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": account["client_email"],
        "scope": SHEETS_READONLY_SCOPE,
        "aud": GOOGLE_TOKEN_URL,
        "iat": iat,
        "exp": iat + 3600,
    }
    signing_input = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode('utf-8'))}."
        f"{_b64url(json.dumps(claims, separators=(',', ':')).encode('utf-8'))}"
    )
    loaded_key = serialization.load_pem_private_key(
        account["private_key"].encode("utf-8"),
        password=None,
    )
    if not isinstance(loaded_key, RSAPrivateKey):
        raise ValueError("ключ service account должен быть RSA")
    signature = loaded_key.sign(
        signing_input.encode("ascii"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return f"{signing_input}.{_b64url(signature)}"
