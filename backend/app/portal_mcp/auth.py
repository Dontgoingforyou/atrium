"""Пользователь MCP: Bearer SSO и отказ чужой роли."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from contextlib import aclosing, asynccontextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any, cast

import httpx
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError as RequestValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.deps_auth import extract_bearer_token, require_portal_admin, verify_access_token
from app.core.auth_constants import SSO_POSITION_STUDENT
from app.core.exceptions import AppError, UnauthorizedError
from app.core.permissions import require_manager_or_admin
from app.core.utils import decode_jwt_payload_unverified
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.infrastructure.db.session import async_session_factory, get_db_session
from app.portal_collab.services._notification_access import idp_groups_from_profile
from app.schemas.auth import UserPublic
from app.services.sso.login_allowlist import ensure_portal_login_allowed

logger = logging.getLogger(__name__)

_authorization: ContextVar[str | None] = ContextVar("portal_mcp_authorization", default=None)


def set_authorization(value: str | None) -> Token[str | None]:
    return _authorization.set(value)


def reset_authorization(token: Token[str | None]) -> None:
    _authorization.reset(token)


def current_authorization() -> str | None:
    return _authorization.get()


@dataclass(frozen=True, slots=True)
class McpCall:
    user: UserPublic
    session: AsyncSession
    http: httpx.AsyncClient


class McpBearerGate:
    """Без Bearer запрос не доходит до JSON-RPC. Роль проверяет каждый тул."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path") or ""
        if path == "":
            scope = dict(scope)
            scope["path"] = "/"
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw = headers.get(b"authorization")
        authorization = raw.decode("latin-1") if raw else None
        if extract_bearer_token(authorization) is None:
            body = json.dumps(
                {"code": "unauthorized", "message": "Требуется заголовок Authorization: Bearer"},
                ensure_ascii=False,
            ).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [(b"content-type", b"application/json; charset=utf-8")],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        token = set_authorization(authorization)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_authorization(token)


def _user_from_profile(profile: PortalUserProfile) -> UserPublic:
    """Профиль уже сохранён входом в портал. Неверифицированный JWT даёт только email для поиска."""
    position = SSO_POSITION_STUDENT if profile.is_developer and not profile.is_portal_admin else None
    return UserPublic(
        sub=profile.sub,
        email=profile.email or "",
        username=profile.username or "",
        full_name=profile.full_name or "",
        idp_groups=idp_groups_from_profile(profile),
        is_portal_admin=profile.is_portal_admin,
        position=position,
        gid_number=profile.gid_number,
    )


async def _user_by_token_email(session: AsyncSession, token: str) -> UserPublic | None:
    payload = decode_jwt_payload_unverified(token)
    if not payload:
        return None
    email = str(payload.get("email") or "").strip()
    if not email:
        return None
    profile = (
        await session.execute(select(PortalUserProfile).where(PortalUserProfile.email == email))
    ).scalar_one_or_none()
    if profile is None:
        return None
    return _user_from_profile(profile)


async def resolve_mcp_user(session: AsyncSession, http: httpx.AsyncClient) -> UserPublic:
    authorization = _authorization.get()
    token = extract_bearer_token(authorization)
    if token is None:
        raise UnauthorizedError("Требуется заголовок Authorization: Bearer")
    try:
        return await verify_access_token(token, session, http)
    except UnauthorizedError:
        # Hub может прислать JWT, который userinfo портала не принимает.
        # Личность берём из уже сохранённого профиля, не из claims токена.
        user = await _user_by_token_email(session, token)
        if user is None:
            raise
        from app.api import deps_auth

        loader = getattr(deps_auth, "get_settings")
        ensure_portal_login_allowed(user, loader())
        return user


@asynccontextmanager
async def _session() -> AsyncIterator[AsyncSession]:
    from app.main import app

    override: Callable[[], AsyncIterator[AsyncSession]] | None = app.dependency_overrides.get(get_db_session)
    if override is not None:
        agen = cast(AsyncGenerator[AsyncSession, None], override())
        async with aclosing(agen):
            session = await anext(agen)
            yield session
        return
    async with async_session_factory() as session:
        yield session


@asynccontextmanager
async def _http_client() -> AsyncIterator[httpx.AsyncClient]:
    from app.core.config import get_settings
    from app.main import app

    shared: httpx.AsyncClient | None = getattr(app.state, "http_client", None)
    if shared is not None:
        yield shared
        return
    async with httpx.AsyncClient(timeout=get_settings().http_client_timeout_seconds, trust_env=False) as client:
        yield client


@asynccontextmanager
async def mcp_call(resource: str) -> AsyncIterator[McpCall]:
    """Открыть сессию, узнать пользователя и пустить только менеджера или админа."""
    user_sub = "-"
    try:
        async with _session() as session, _http_client() as http:
            user = await resolve_mcp_user(session, http)
            user_sub = user.sub
            require_manager_or_admin(user)
            yield McpCall(user=user, session=session, http=http)
    except AppError as exc:
        if exc.status_code == 403:
            logger.warning("Отказ MCP: user_sub=%s resource=%s", user_sub, resource)
        raise ToolError(exc.message) from exc
    except RequestValidationError as exc:
        parts = [str(err.get("msg") or err) for err in exc.errors()]
        raise ToolError("; ".join(parts) or "Некорректные аргументы") from exc


async def require_admin(call: McpCall, resource: str) -> UserPublic:
    """Тот же заслон, что ``PortalAdminUser``, если сервис сам админа не проверяет."""
    try:
        return await require_portal_admin(call.user)
    except AppError as exc:
        if exc.status_code == 403:
            logger.warning("Отказ MCP: user_sub=%s resource=%s", call.user.sub, resource)
        raise ToolError(exc.message) from exc


def clamp_limit(limit: int) -> int:
    from app.core.exceptions import ValidationError
    from app.portal_mcp.constants import LIST_LIMIT_MAX

    if limit < 1:
        raise ValidationError("limit должен быть не меньше 1")
    return min(limit, LIST_LIMIT_MAX)


def dump(value: Any) -> Any:
    from pydantic import BaseModel

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [dump(item) for item in value]
    return value


def dump_dict(value: Any) -> dict[str, object]:
    raw = dump(value)
    if not isinstance(raw, dict):
        from app.core.exceptions import ValidationError

        raise ValidationError("Ожидался объект")
    return cast(dict[str, object], raw)


def dump_list(value: Any) -> list[dict[str, object]]:
    raw = dump(value)
    if not isinstance(raw, list):
        from app.core.exceptions import ValidationError

        raise ValidationError("Ожидался список")
    return cast(list[dict[str, object]], raw)
