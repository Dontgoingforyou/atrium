"""Тесты сборки REDIS_URL с паролем."""

from __future__ import annotations

from app.core.redis_url import build_redis_url_with_password


def test_empty_url_stays_empty() -> None:
    assert build_redis_url_with_password("", "pw") == ""


def test_no_password_unchanged() -> None:
    assert build_redis_url_with_password("redis://redis:6379/0", "") == "redis://redis:6379/0"


def test_injects_password() -> None:
    url = build_redis_url_with_password("redis://redis:6379/0", "s3cret!")
    assert url == "redis://:s3cret%21@redis:6379/0"


def test_does_not_override_existing_password() -> None:
    url = build_redis_url_with_password("redis://:old@redis:6379/0", "new")
    assert url == "redis://:old@redis:6379/0"


def test_special_chars_encoded() -> None:
    url = build_redis_url_with_password("redis://redis:6379/0", "p@ss/word")
    assert "@redis" in url
    assert "p%40ss" in url


def test_preserves_username() -> None:
    url = build_redis_url_with_password("redis://alice@redis:6379/0", "s3cret")
    assert url == "redis://alice:s3cret@redis:6379/0"


def test_ipv6_brackets_preserved() -> None:
    url = build_redis_url_with_password("redis://[::1]:6379/0", "pw")
    assert url == "redis://:pw@[::1]:6379/0"
    from urllib.parse import urlparse

    parsed = urlparse(url)
    assert parsed.hostname == "::1"
    assert parsed.password == "pw"
