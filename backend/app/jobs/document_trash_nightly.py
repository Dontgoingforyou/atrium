"""Фоновая очистка корзины документов по TTL (ночной запуск по UTC)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.infrastructure.db.session import async_session_factory
from app.portal_documents.services.portal_document_trash import (
    purge_expired_document_trash,
)

logger = logging.getLogger(__name__)


def seconds_until_next_run_utc(now: datetime, hour_utc: int) -> float:
    """Секунды до ближайшего ``hour_utc``:00 UTC (ровно в час — 0)."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    else:
        now = now.astimezone(UTC)
    target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if target < now:
        target += timedelta(days=1)
    return max(0.0, (target - now).total_seconds())


async def run_document_trash_purge_loop(
    stop_event: asyncio.Event,
    settings: Settings,
) -> None:
    """Ждёт очередного окна UTC, purge; стоп по ``stop_event``."""
    if not settings.document_trash_purge_enabled:
        return
    hour = settings.document_trash_purge_hour_utc
    logger.info(
        "Фоновая очистка корзины документов: %02d:00 UTC (DOCUMENT_TRASH_PURGE_ENABLED=false — отключить)",
        hour,
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
                await purge_expired_document_trash(session)
                logger.info(
                    "Очистка корзины документов по TTL (фон) выполнена",
                )
            except Exception:
                logger.exception(
                    "Ошибка фоновой очистки корзины документов по TTL",
                )
