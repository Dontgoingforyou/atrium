"""Синхронизация снимка бенч из Google Таблицы."""

from __future__ import annotations

import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_bench import PortalBenchSyncState
from app.integrations.google_sheets.client import GoogleSheetsClient
from app.portal_bench.constants import FROZEN_YEAR, SHEETS_SOURCE, SYNC_STATE_ID
from app.portal_bench.services._ingest import ingest_sheet_values
from app.portal_bench.services._snapshot import upsert_year_snapshot

logger = logging.getLogger(__name__)


async def record_sync_result(
    session: AsyncSession,
    *,
    success: bool,
    error: str | None = None,
) -> None:
    state = await session.get(PortalBenchSyncState, SYNC_STATE_ID)
    if state is None:
        state = PortalBenchSyncState(id=SYNC_STATE_ID)
        session.add(state)
    now = now_utc()
    state.last_attempt_at = now
    if success:
        state.last_success_at = now
        state.last_error = None
    else:
        state.last_error = error
    await session.commit()


async def sync_bench_from_sheets(
    session: AsyncSession,
    settings: Settings,
    http: httpx.AsyncClient,
) -> bool:
    """Тянет листы, пишет живые годы. Замороженный 2025 не трогает. Ошибка Google не чистит снимок."""
    if not settings.google_sheets_enabled:
        return False
    try:
        client = GoogleSheetsClient(settings, http)
        sheets = await client.fetch_dashboard_sheets()
        records, year, _rates = ingest_sheet_values(sheets)
        if year == FROZEN_YEAR:
            logger.info("Пропуск upsert бенч: год %s заморожен", year)
        else:
            await upsert_year_snapshot(
                session,
                year=year,
                records=records,
                source=SHEETS_SOURCE,
                frozen=False,
            )
        await record_sync_result(session, success=True)
        logger.info("Синхронизация бенч из Google Таблицы: год=%s строк=%s", year, len(records))
        return True
    except ServiceUnavailableError:
        logger.warning("Google Sheets недоступна, снимок бенч не очищен")
        await record_sync_result(session, success=False, error="Google Sheets недоступна")
        return False
