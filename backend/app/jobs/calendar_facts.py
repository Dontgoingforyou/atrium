"""Читатель фактов календаря из Kafka."""

from __future__ import annotations

import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from app.core.config import Settings
from app.infrastructure.db.session import async_session_factory
from app.portal_calendar.services._facts import apply_calendar_fact
from app.portal_chat.services.inbox_publish import publish_portal_notification_updates

logger = logging.getLogger(__name__)

_RETRY_SECONDS = 5


async def run_calendar_facts_loop(stop_event: asyncio.Event, settings: Settings) -> None:
    if not settings.calendar_facts_enabled:
        return
    servers = settings.calendar_kafka_bootstrap_servers.strip()
    if not servers:
        logger.info("Факты календаря: CALENDAR_KAFKA_BOOTSTRAP_SERVERS пуст, читатель не запущен")
        return
    logger.info("Факты календаря: топик %s, группа %s", settings.calendar_kafka_topic, settings.calendar_kafka_group)
    while not stop_event.is_set():
        try:
            await _consume(stop_event, settings, servers)
        except Exception:
            logger.exception("Факты календаря: читатель остановился, повтор через %s с", _RETRY_SECONDS)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=_RETRY_SECONDS)
                return
            except TimeoutError:
                continue


async def _consume(stop_event: asyncio.Event, settings: Settings, servers: str) -> None:
    consumer = AIOKafkaConsumer(
        settings.calendar_kafka_topic,
        bootstrap_servers=servers,
        group_id=settings.calendar_kafka_group,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        while not stop_event.is_set():
            batch = await consumer.getmany(timeout_ms=1000, max_records=20)
            if not batch:
                continue
            for messages in batch.values():
                for message in messages:
                    await _apply_message(message.value)
            await consumer.commit()
    finally:
        await consumer.stop()


async def _apply_message(raw: bytes | None) -> None:
    if not raw:
        return
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Факт календаря не JSON")
        return
    if not isinstance(body, dict):
        logger.warning("Факт календаря не объект")
        return
    async with async_session_factory() as session:
        notified = await apply_calendar_fact(session, body)
        await session.commit()
    if not notified:
        return
    try:
        await publish_portal_notification_updates(list(notified), notification_ids_by_sub=notified)
    except Exception:
        logger.exception("Факт календаря применён, сигнал колокола не ушёл")
