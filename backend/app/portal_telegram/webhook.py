from __future__ import annotations

import logging

from aiogram.types import Update
from fastapi import APIRouter, Request, Response, status

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError
from app.core.utils import hmac_secrets_equal
from app.portal_telegram.webhook_config import normalize_webhook_path, webhook_secret

logger = logging.getLogger(__name__)


def build_telegram_webhook_router() -> APIRouter:
    s = get_settings()
    path = normalize_webhook_path(s.telegram_webhook_path)
    router = APIRouter(tags=["Telegram webhook"])

    @router.post(path)
    async def telegram_webhook(request: Request) -> Response:
        expected = webhook_secret(get_settings())
        got = request.headers.get("X-Telegram-Bot-Api-Secret-Token") or ""
        if not hmac_secrets_equal(got, expected):
            logger.warning(
                "Telegram webhook: неверный secret token ip=%s",
                request.client.host if request.client else "?",
            )
            raise ForbiddenError("Forbidden")
        body = await request.body()
        try:
            update = Update.model_validate_json(body)
        except Exception as exc:
            logger.warning("Telegram webhook: невалидный JSON: %s", exc)
            raise BadRequestError("Bad JSON") from exc

        # Ленивый импорт: get_bot/get_dispatcher должны читаться на момент запроса,
        # а не при загрузке модуля — роутер вебхука строится при создании приложения,
        # до init_telegram_bot() в lifespan. Тесты также патчат
        # app.portal_telegram.bot.instance.get_bot/get_dispatcher напрямую через
        # monkeypatch.setattr; `from ... import ...` на уровне модуля закрепил бы
        # исходные объекты и не увидел бы подмену.
        from app.portal_telegram.bot.instance import get_bot, get_dispatcher  # noqa: PLC0415

        try:
            await get_dispatcher().feed_update(get_bot(), update)
        except Exception:
            logger.exception("Telegram webhook: ошибка обработки update")
        return Response(status_code=status.HTTP_200_OK, content="OK")

    return router
