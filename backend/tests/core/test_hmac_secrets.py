"""Сравнение секретов (`hmac_secrets_equal`) — fail-closed на пустых и разной длине."""

from __future__ import annotations

from app.core.utils import hmac_secrets_equal


def test_hmac_secrets_equal_fail_closed() -> None:
    assert hmac_secrets_equal("short", "much-longer-secret") is False
    assert hmac_secrets_equal(None, "secret") is False
    assert hmac_secrets_equal("", "secret") is False
    assert hmac_secrets_equal("", "") is False
    assert hmac_secrets_equal("wh-secret", "wh-secreX") is False
    assert hmac_secrets_equal("secret", "secret") is True
