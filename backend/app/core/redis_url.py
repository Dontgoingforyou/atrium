"""Сборка REDIS_URL с паролем."""

from __future__ import annotations

from urllib.parse import quote, urlparse, urlunparse


def build_redis_url_with_password(redis_url: str, redis_password: str) -> str:
    """Подставить пароль в URL, если задан ``redis_password`` и в URL его ещё нет.

    ``REDIS_URL`` остаётся ``redis://redis:6379/0`` в compose; секрет — в ``REDIS_PASSWORD``.
    Пароль URL-кодируется (спецсимволы в пароле допустимы).
    Сохраняет username и IPv6-скобки hostname.
    """
    url = redis_url.strip()
    if not url:
        return ""
    password = redis_password.strip()
    if not password:
        return url

    parsed = urlparse(url)
    if parsed.password:
        return url

    hostname = parsed.hostname
    if not hostname:
        return url

    # urlparse.hostname для IPv6 без скобок; в netloc скобки обязательны.
    if ":" in hostname and not hostname.startswith("["):
        host_for_netloc = f"[{hostname}]"
    else:
        host_for_netloc = hostname

    port = parsed.port
    user = parsed.username
    encoded_pw = quote(password, safe="")
    if user:
        userinfo = f"{quote(user, safe='')}:{encoded_pw}@"
    else:
        userinfo = f":{encoded_pw}@"
    hostpart = f"{host_for_netloc}:{port}" if port is not None else host_for_netloc
    netloc = f"{userinfo}{hostpart}"
    return urlunparse(parsed._replace(netloc=netloc))
