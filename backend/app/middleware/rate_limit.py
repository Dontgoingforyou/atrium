"""Rate limiter на основе Redis sliding window (sorted set).

Алгоритм: для каждого запроса добавляем метку времени в sorted set,
удаляем устаревшие записи и считаем оставшиеся — всё в одном pipeline.
Это истинное скользящее окно: «20 запросов за любые последние 60 секунд»,
а не «20 запросов с начала текущей минуты» (fixed window).

При недоступном Redis — in-memory fallback (см. ``rate_limit_check``).
"""

from __future__ import annotations

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import Settings, get_settings
from app.core.exceptions import RateLimitError, build_error_payload
from app.infrastructure.cache.rate_limit import rate_limit_check, rate_limit_client_key

logger = logging.getLogger(__name__)

_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_API_V1_PREFIX = "/api/v1/"
_HEALTH_PATH = "/api/v1/health"
_SEMANTIC_SEARCH_PATH = "/api/v1/portal/search/semantic"
_BENCH_EXPORT_PATH = "/api/v1/integrations/bench"

# Пути с собственными лимитами в AuthRateLimitMiddleware — не дублировать в ApiRateLimitMiddleware.
# Пороги — из Settings (auth_*_rate_limit / presence_beacon_rate_limit).
AUTH_RATE_LIMITED_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/auth/login",
        "/api/v1/auth/token",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout-beacon",
        "/api/v1/auth/authorization-url",
        # sendBeacon при каждом закрытии вкладки — отдельный лимит чтобы не попасть
        # под общий ApiRateLimitMiddleware для mutating-методов.
        "/api/v1/portal/users/me/presence-beacon",
    }
)


def _client_ip(request: Request) -> str:
    """Получить IP клиента (с учётом ProxyHeadersMiddleware)."""
    return request.client.host if request.client else "unknown"


def _auth_rate_rule(path: str, settings: Settings) -> tuple[int, int] | None:
    """Лимит и окно для auth/beacon-пути; ``None`` если путь не лимитируется здесь."""
    if path not in AUTH_RATE_LIMITED_PATHS:
        return None
    window = settings.auth_rate_window_seconds
    limits: dict[str, int] = {
        "/api/v1/auth/login": settings.auth_login_rate_limit,
        "/api/v1/auth/token": settings.auth_token_rate_limit,
        "/api/v1/auth/refresh": settings.auth_refresh_rate_limit,
        "/api/v1/auth/logout-beacon": settings.auth_logout_beacon_rate_limit,
        "/api/v1/auth/authorization-url": settings.auth_authorization_url_rate_limit,
        "/api/v1/portal/users/me/presence-beacon": settings.presence_beacon_rate_limit,
    }
    return limits[path], window


def _too_many_requests_response(window: int) -> JSONResponse:
    """Тело/статус — по единому контракту `AppError` (`RateLimitError`), хоть и без raise.

    Чистый ASGI-middleware не прогоняет исключение через `exception_handler` FastAPI
    (): ``raise RateLimitError`` здесь дал бы необработанный 500.
    Формат ответа должен совпадать с тем, что отдаёт `app_error_handler` для `RateLimitError`.
    """
    err = RateLimitError()
    return JSONResponse(
        status_code=err.status_code,
        content=build_error_payload(code=err.code, message=err.message),
        headers={"Retry-After": str(window)},
    )


async def _allowed_by_client_and_ip(
    *,
    client_key: str,
    ip: str,
    client_prefix: str,
    ip_prefix: str,
    client_limit: int,
    ip_limit: int,
    window: int,
) -> bool:
    """False, если превышен per-token/per-IP клиентский лимит или потолок IP.

    Per-token ключ не проверять в одиночку: любой уникальный Bearer — новое ведро.
    IP-потолок закрывает этот обход; клиентский лимит оставляет isolation между пользователями.
    """
    ip_allowed = await rate_limit_check(f"{ip_prefix}:{ip}", ip_limit, window)
    if not ip_allowed:
        return False
    return await rate_limit_check(f"{client_prefix}:{client_key}", client_limit, window)


class AuthRateLimitMiddleware:
    """Ограничение запросов на auth- и beacon-эндпоинты (лимиты — из Settings).

    По умолчанию (sliding window, один IP):
    - /auth/login: 10 / 60 с
    - /auth/token и /auth/refresh: 20 / 60 с
    - /auth/logout-beacon и presence-beacon: 60 / 60 с (sendBeacon при выгрузке вкладки)
    - /auth/authorization-url: 30 / 60 с
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        path = request.url.path
        s = get_settings()
        rule = _auth_rate_rule(path, s)
        if rule is None:
            await self.app(scope, receive, send)
            return

        limit, window = rule
        ip = _client_ip(request)
        key = f"rl:{path}:{ip}"

        allowed = await rate_limit_check(key, limit, window)
        if not allowed:
            logger.warning(
                "rate_limit: превышен лимит %d/%ds для %s ip=%s",
                limit,
                window,
                path,
                ip,
            )
            await _too_many_requests_response(window)(scope, receive, send)
            return

        await self.app(scope, receive, send)


class ApiRateLimitMiddleware:
    """Общий rate limit для API: health flood, semantic search и mutating /api/v1.

    - GET /api/v1/health — по IP (без auth)
    - GET /api/v1/integrations/bench — по IP (service Bearer не должен давать новое ведро)
    - GET /api/v1/portal/search/semantic — per-token/IP плюс потолок по IP
    - POST/PUT/PATCH/DELETE /api/v1/* — per-token/IP плюс потолок по IP

    Auth-эндпоинты с собственными лимитами пропускаются (см. AUTH_RATE_LIMITED_PATHS).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        path = request.url.path
        method = request.method.upper()
        s = get_settings()

        if path == _HEALTH_PATH and method == "GET":
            ip = _client_ip(request)
            key = f"rl:health:ip:{ip}"
            allowed = await rate_limit_check(key, s.health_rate_limit, s.health_rate_window_seconds)
            if not allowed:
                logger.warning("rate_limit: health flood ip=%s", ip)
                await _too_many_requests_response(s.health_rate_window_seconds)(scope, receive, send)
                return

        if path == _BENCH_EXPORT_PATH and method == "GET":
            ip = _client_ip(request)
            key = f"rl:bench-export:ip:{ip}"
            allowed = await rate_limit_check(key, s.bench_export_rate_limit, s.bench_export_rate_window_seconds)
            if not allowed:
                logger.warning("rate_limit: bench export flood ip=%s", ip)
                await _too_many_requests_response(s.bench_export_rate_window_seconds)(scope, receive, send)
                return

        if path == _SEMANTIC_SEARCH_PATH and method == "GET":
            ip = _client_ip(request)
            client_key = rate_limit_client_key(request)
            allowed = await _allowed_by_client_and_ip(
                client_key=client_key,
                ip=ip,
                client_prefix="rl:semantic",
                ip_prefix="rl:semantic-ip",
                client_limit=s.semantic_search_rate_limit,
                ip_limit=s.semantic_search_ip_rate_limit,
                window=s.semantic_search_rate_window_seconds,
            )
            if not allowed:
                logger.warning("rate_limit: semantic search flood key=%s ip=%s", client_key, ip)
                await _too_many_requests_response(s.semantic_search_rate_window_seconds)(scope, receive, send)
                return

        if method in _MUTATING_METHODS and path.startswith(_API_V1_PREFIX):
            if path in AUTH_RATE_LIMITED_PATHS:
                await self.app(scope, receive, send)
                return
            ip = _client_ip(request)
            client_key = rate_limit_client_key(request)
            allowed = await _allowed_by_client_and_ip(
                client_key=client_key,
                ip=ip,
                client_prefix="rl:api-mut",
                ip_prefix="rl:api-mut-ip",
                client_limit=s.api_mutation_rate_limit,
                ip_limit=s.api_mutation_ip_rate_limit,
                window=s.api_mutation_rate_window_seconds,
            )
            if not allowed:
                logger.warning(
                    "rate_limit: mutating API flood key=%s ip=%s path=%s method=%s",
                    client_key,
                    ip,
                    path,
                    method,
                )
                await _too_many_requests_response(s.api_mutation_rate_window_seconds)(scope, receive, send)
                return

        await self.app(scope, receive, send)
