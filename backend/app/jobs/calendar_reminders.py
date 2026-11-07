"""Фоновая отправка напоминаний календаря (каждую минуту)."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import Settings
from app.infrastructure.db.session import async_session_factory
from app.portal_calendar.services._reminders import process_due_reminders

logger = logging.getLogger(__name__)


async def run_calendar_reminders_loop(stop_event: asyncio.Event, settings: Settings) -> None:
    if not settings.calendar_reminders_enabled:
        return
    interval = max(15, settings.calendar_reminders_interval_seconds)
    logger.info(
        "Фоновые напоминания календаря: каждые %s с (CALENDAR_REMINDERS_ENABLED=false — отключить)",
        interval,
    )
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=float(interval))
            return
        except TimeoutError:
            pass
        if stop_event.is_set():
            return
        async with async_session_factory() as session:
            try:
                n = await process_due_reminders(session)
                if n:
                    logger.info("Календарь: отправлено напоминаний: %s", n)
            except Exception:
                logger.exception("Ошибка фоновой отправки напоминаний календаря")
