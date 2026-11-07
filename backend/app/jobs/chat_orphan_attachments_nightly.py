"""Фоновая очистка осиротевших вложений чата (загрузили файл, не отправили сообщение)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from app.core.config import Settings
from app.infrastructure.db.session import async_session_factory
from app.jobs.document_trash_nightly import seconds_until_next_run_utc
from app.portal_chat.services import attachment as att_svc

logger = logging.getLogger(__name__)


async def run_chat_orphan_attachment_purge_loop(
    stop_event: asyncio.Event,
    settings: Settings,
) -> None:
    """Ждёт очередного окна UTC, purge; стоп по ``stop_event``."""
    if not settings.chat_orphan_attachment_purge_enabled:
        return
    hour = settings.chat_orphan_attachment_purge_hour_utc
    min_age = settings.chat_orphan_attachment_purge_min_age_hours
    logger.info(
        "Фоновая очистка осиротевших вложений чата: %02d:00 UTC, min_age_hours=%s "
        "(CHAT_ORPHAN_ATTACHMENT_PURGE_ENABLED=false — отключить)",
        hour,
        min_age,
    )
    while not stop_event.is_set():
        delay = seconds_until_next_run_utc(datetime.now(UTC), hour)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
            return
        except TimeoutError:
            pass
        if stop_event.is_set():
            return
        async with async_session_factory() as session:
            try:
                n = await att_svc.purge_orphan_attachments_older_than(session, min_age_hours=min_age)
                logger.info(
                    "Очистка осиротевших вложений чата (фон): удалено %d",
                    n,
                )
            except Exception:
                logger.exception(
                    "Ошибка фоновой очистки осиротевших вложений чата",
                )
