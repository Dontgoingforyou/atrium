from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Literal

import redis.asyncio as aioredis
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.infrastructure.db.session import async_session_factory
from app.infrastructure.ws.inbox_manager import INBOX_CHANNEL_PREFIX, inbox_channel_pattern
from app.portal_chat.services.chat import get_batch_unread_counts
from app.portal_chat.services.inbox_publish import EVENT_DM_INBOX_UPDATE, EVENT_PORTAL_NOTIFICATION_UPDATE
from app.portal_telegram.bot.instance import get_bot
from app.portal_telegram.constants import TELEGRAM_CHAT_INBOX_SUPPRESS_UNREAD_THRESHOLD
from app.portal_telegram.services.binding import get_binding, unlink_by_chat_id
from app.portal_telegram.services.calendar_meeting_url import calendar_meeting_url_for_notification
from app.portal_telegram.services.chat_inbox_telegram import (
    format_chat_inbox_telegram,
    source_message_visible_for_recipient,
)
from app.portal_telegram.services.notification_fetch import (
    fetch_mention_display_labels_longest_first,
    fetch_notification_for_recipient,
    mention_subs_from_notification,
)
from app.portal_telegram.services.notification_message import format_portal_notification_telegram
from app.portal_telegram.services.telegram_url_markup import (
    body_with_fallback_link,
    inline_url_keyboard,
    notification_url_keyboard,
)

logger = logging.getLogger(__name__)

_MAX_SEND_ATTEMPTS = 4
_INITIAL_BACKOFF = 0.4

TelegramInboxDelivery = Literal["sent", "skipped", "failed"]


def _channel_user_sub(channel: str | bytes) -> str | None:
    raw = channel.decode("utf-8") if isinstance(channel, bytes) else channel
    prefix = INBOX_CHANNEL_PREFIX
    if not raw.startswith(prefix):
        return None
    return raw[len(prefix) :]


async def _send_telegram_message(
    chat_id: int,
    text: str,
    settings: Settings,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
) -> bool:
    bot = get_bot()
    delay = _INITIAL_BACKOFF
    last_err: BaseException | None = None
    for attempt in range(_MAX_SEND_ATTEMPTS):
        try:
            await bot.send_message(
                chat_id,
                text,
                disable_web_page_preview=True,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return True
        except TelegramForbiddenError:
            logger.info("Telegram: пользователь заблокировал бота, снимаем привязку chat_id=%s", chat_id)
            async with async_session_factory() as db:
                await unlink_by_chat_id(db, chat_id)
            return True
        except TelegramRetryAfter as exc:
            last_err = exc
            wait_s = float(getattr(exc, "retry_after", delay) or delay)
            logger.warning(
                "Telegram send_message RetryAfter %ss попытка %d/%d",
                wait_s,
                attempt + 1,
                _MAX_SEND_ATTEMPTS,
            )
            if attempt + 1 < _MAX_SEND_ATTEMPTS:
                await asyncio.sleep(wait_s)
            continue
        except TelegramBadRequest as exc:
            logger.warning("Telegram send_message отклонён (4xx), без повтора: %s", exc)
            return False
        except Exception as exc:
            last_err = exc
            logger.warning(
                "Telegram send_message попытка %d/%d: %s",
                attempt + 1,
                _MAX_SEND_ATTEMPTS,
                exc,
            )
            if attempt + 1 < _MAX_SEND_ATTEMPTS:
                await asyncio.sleep(delay)
                delay *= 2
    if last_err is not None:
        logger.error(
            "Telegram: не удалось доставить сообщение после повторов: %s",
            last_err,
            exc_info=last_err,
        )
    return False


async def _prepare_notification_send(
    db: AsyncSession,
    user_sub: str,
    payload: dict[str, Any],
    settings: Settings,
) -> tuple[str, str | None, InlineKeyboardMarkup | None] | None:
    notif_id_raw = payload.get("notification_id")
    if not notif_id_raw:
        logger.warning("Telegram listener: portal_notification_update без notification_id")
        return None
    try:
        notif_uuid = uuid.UUID(str(notif_id_raw))
    except (ValueError, TypeError):
        logger.warning("Telegram listener: некорректный notification_id в portal_notification_update")
        return None
    notif = await fetch_notification_for_recipient(db, user_sub, notification_id=notif_uuid)
    if notif is None:
        logger.debug("Telegram listener: нет уведомления для sub=%s…", user_sub[:16])
        return None
    mention_labels = await fetch_mention_display_labels_longest_first(
        db,
        mention_subs_from_notification(notif),
    )
    body, open_url = format_portal_notification_telegram(
        notif,
        settings,
        mention_labels_longest_first=mention_labels,
    )
    markup = notification_url_keyboard(
        open_url,
        meeting_url=calendar_meeting_url_for_notification(notif),
    )
    text_out, parse_mode = body_with_fallback_link(body, open_url, markup, fallback_anchor_text="Открыть в портале")
    return text_out, parse_mode, markup


async def _prepare_chat_inbox_send(
    db: AsyncSession,
    user_sub: str,
    payload: dict[str, Any],
    settings: Settings,
) -> tuple[str, str | None, InlineKeyboardMarkup | None] | None:
    raw_id = payload.get("chat_id")
    kind = str(payload.get("kind") or "dm")
    if not raw_id:
        return None
    try:
        cid = uuid.UUID(str(raw_id))
    except (ValueError, TypeError):
        logger.warning("Telegram listener: некорректный chat_id в dm_inbox_update")
        return None
    inbox_kind = kind if kind in ("dm", "group") else "dm"
    recipient_mentioned = bool(payload.get("recipient_mentioned"))
    raw_message_id = payload.get("message_id")
    if raw_message_id:
        try:
            message_uuid = uuid.UUID(str(raw_message_id))
        except (ValueError, TypeError):
            logger.warning("Telegram listener: некорректный message_id в dm_inbox_update")
            return None
        visible = await source_message_visible_for_recipient(
            db,
            chat_id=cid,
            message_id=message_uuid,
            recipient_sub=user_sub,
        )
        if not visible:
            logger.debug(
                "Telegram listener: пропуск push, сообщение уже недоступно sub=%s… message_id=%s",
                user_sub[:16],
                message_uuid,
            )
            return None
    unread_map = await get_batch_unread_counts(db, user_sub, [cid])
    unread_n = unread_map.get(cid, 0)
    if not recipient_mentioned and unread_n >= TELEGRAM_CHAT_INBOX_SUPPRESS_UNREAD_THRESHOLD:
        logger.debug(
            "Telegram listener: пропуск push чата sub=%s… chat_id=%s unread=%s kind=%s",
            user_sub[:16],
            cid,
            unread_n,
            inbox_kind,
        )
        return None
    dm_result = await format_chat_inbox_telegram(
        db,
        recipient_sub=user_sub,
        chat_id=cid,
        kind=inbox_kind,
        settings=settings,
    )
    if dm_result is None:
        return None
    dm_body, dm_url = dm_result
    dm_markup = inline_url_keyboard(dm_url, "Открыть чат")
    dm_text, dm_parse_mode = body_with_fallback_link(dm_body, dm_url, dm_markup, fallback_anchor_text="Открыть чат")
    return dm_text, dm_parse_mode, dm_markup


async def deliver_telegram_inbox_payload(
    user_sub: str, payload: dict[str, Any], settings: Settings
) -> TelegramInboxDelivery:
    """Собрать текст и отправить в Telegram без проверки окна доставки."""
    event = payload.get("event")
    tg_chat_id: int | None = None
    text_out: str | None = None
    parse_mode: str | None = None
    markup: InlineKeyboardMarkup | None = None

    async with async_session_factory() as db:
        binding = await get_binding(db, user_sub)
        if binding is None:
            return "skipped"
        tg_chat_id = int(binding.telegram_chat_id)

        if event == EVENT_PORTAL_NOTIFICATION_UPDATE:
            prepared = await _prepare_notification_send(db, user_sub, payload, settings)
            if prepared is None:
                return "skipped"
            text_out, parse_mode, markup = prepared
        elif event == EVENT_DM_INBOX_UPDATE:
            prepared_dm = await _prepare_chat_inbox_send(db, user_sub, payload, settings)
            if prepared_dm is None:
                return "skipped"
            text_out, parse_mode, markup = prepared_dm
        else:
            return "skipped"

    if tg_chat_id is None or text_out is None:
        return "skipped"
    sent = await _send_telegram_message(tg_chat_id, text_out, settings, reply_markup=markup, parse_mode=parse_mode)
    return "sent" if sent else "failed"


async def _handle_inbox_payload(user_sub: str, payload: dict[str, Any], settings: Settings) -> None:
    await deliver_telegram_inbox_payload(user_sub, payload, settings)


async def telegram_inbox_listener_loop(redis: aioredis.Redis) -> None:
    settings = get_settings()
    pattern = inbox_channel_pattern()
    while True:
        try:
            async with redis.pubsub() as pubsub:
                await pubsub.psubscribe(pattern)
                logger.info("Telegram listener: PSUBSCRIBE %s", pattern)
                async for msg in pubsub.listen():
                    if msg["type"] != "pmessage":
                        continue
                    channel = msg.get("channel")
                    data_raw = msg.get("data")
                    if channel is None or data_raw is None:
                        continue
                    user_sub = _channel_user_sub(channel)
                    if not user_sub:
                        continue
                    try:
                        data_str = data_raw.decode("utf-8") if isinstance(data_raw, bytes) else str(data_raw)
                        payload = json.loads(data_str)
                    except (json.JSONDecodeError, TypeError) as exc:
                        logger.warning("Telegram listener: некорректный JSON: %s", exc)
                        continue
                    if not isinstance(payload, dict):
                        continue
                    try:
                        await _handle_inbox_payload(user_sub, payload, settings)
                    except Exception:
                        logger.exception("Telegram listener: ошибка обработки inbox для %s", user_sub[:24])
        except asyncio.CancelledError:
            logger.info("Telegram listener: отмена")
            raise
        except Exception:
            logger.exception("Telegram listener: сбой подписки, переподключение через 3 с")
            await asyncio.sleep(3.0)
