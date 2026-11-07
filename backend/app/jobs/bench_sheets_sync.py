"""Фоновая синхронизация дашборда бенч из Google Таблицы."""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.core.config import Settings
from app.infrastructure.db.session import async_session_factory
from app.portal_bench.services._sync import sync_bench_from_sheets

logger = logging.getLogger(__name__)


async def run_bench_sheets_sync_loop(stop_event: asyncio.Event, settings: Settings) -> None:
    if not settings.google_sheets_sync_enabled:
        return
    interval = max(60, settings.google_sheets_sync_interval_seconds)
    logger.info(
        "Фоновая синхронизация бенч из Google Таблицы: сразу и каждые %s с "
        "(GOOGLE_SHEETS_SYNC_ENABLED=false — отключить)",
        interval,
    )
    while not stop_event.is_set():
        timeout = settings.google_sheets_timeout_seconds
        async with async_session_factory() as session:
            try:
                async with httpx.AsyncClient(timeout=timeout, trust_env=False) as http:
                    await sync_bench_from_sheets(session, settings, http)
            except Exception:
                logger.exception("Ошибка фоновой синхронизации бенч из Google Таблицы")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=float(interval))
            return
        except TimeoutError:
            pass
