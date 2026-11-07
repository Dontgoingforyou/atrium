from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.infrastructure.cache.token_cache import get_redis_client
from app.portal_telegram.bot.instance import get_bot_username
from app.portal_telegram.schemas.telegram import BindInitResponse, BindStatusResponse
from app.portal_telegram.services.binding import generate_bind_code, get_binding, unlink

router = APIRouter()


@router.post(
    "/bind/init",
    summary="Начать привязку Telegram",
    response_model=BindInitResponse,
)
async def post_bind_init(user: CurrentUser) -> BindInitResponse:
    s = get_settings()
    if not s.telegram_bot_token.strip():
        raise ServiceUnavailableError("Telegram-бот не настроен в этой среде")
    redis = get_redis_client()
    if redis is None:
        raise ServiceUnavailableError("Redis недоступен — привязка временно невозможна")
    username = get_bot_username()
    if not username:
        raise ServiceUnavailableError("Имя бота ещё не получено, повторите запрос через минуту")
    code = await generate_bind_code(redis, user.sub)
    bot_url = f"https://t.me/{username}?start={code}"
    return BindInitResponse(code=code, bot_url=bot_url)


@router.get(
    "/bind/status",
    summary="Статус привязки Telegram",
    response_model=BindStatusResponse,
)
async def get_bind_status(user: CurrentUser, db: DbSession) -> BindStatusResponse:
    row = await get_binding(db, user.sub)
    if row is None:
        return BindStatusResponse(bound=False, created_at=None)
    return BindStatusResponse(bound=True, created_at=row.created_at)


@router.delete(
    "/bind",
    summary="Отвязать Telegram",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_bind(user: CurrentUser, db: DbSession) -> Response:
    await unlink(db, user.sub)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
