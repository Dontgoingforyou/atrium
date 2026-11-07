"""Чтение и запись снимков дашборда бенч."""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_bench import PortalBenchSyncState, PortalBenchYearSnapshot
from app.portal_bench.constants import (
    FROZEN_YEAR,
    LOCAL_SEED_YEAR,
    SEED_SOURCE,
    STALE_MESSAGE,
    SYNC_STATE_ID,
    seed_json_path,
)
from app.portal_bench.services._ingest import BenchRecord, apply_current_specialization
from app.portal_bench.services._metrics import (
    DashboardPayload,
    build_dashboard,
    filter_catalog,
    filter_records,
)

logger = logging.getLogger(__name__)


async def _seed_year_from_json(
    session: AsyncSession,
    *,
    year: int,
    path: Path,
    frozen: bool,
) -> PortalBenchYearSnapshot | None:
    existing = await session.get(PortalBenchYearSnapshot, year)
    if existing is not None:
        return existing
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("raw_data") or []
    row = PortalBenchYearSnapshot(
        year=year,
        source=SEED_SOURCE,
        frozen=frozen,
        records=records,
        updated_at=now_utc(),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    logger.info("Сидирован снимок бенч за %s (%s строк, frozen=%s)", year, len(records), frozen)
    return row


async def _ensure_year_snapshots_seeded(session: AsyncSession) -> None:
    await _seed_year_from_json(session, year=FROZEN_YEAR, path=seed_json_path("year_2025"), frozen=True)
    await _seed_year_from_json(session, year=LOCAL_SEED_YEAR, path=seed_json_path("year_2026"), frozen=False)


async def ensure_snapshots_and_load_records(session: AsyncSession) -> list[BenchRecord]:
    await _ensure_year_snapshots_seeded(session)
    result = await session.execute(select(PortalBenchYearSnapshot))
    records: list[BenchRecord] = []
    for row in result.scalars().all():
        records.extend(apply_current_specialization(record) for record in (row.records or []))
    return records


async def upsert_year_snapshot(
    session: AsyncSession,
    *,
    year: int,
    records: list[dict[str, Any]],
    source: str,
    frozen: bool = False,
) -> PortalBenchYearSnapshot | None:
    """Пишет снимок года. Замороженный год не перезаписывается."""
    existing = await session.get(PortalBenchYearSnapshot, year)
    if existing is not None and existing.frozen:
        logger.info("Пропуск записи снимка бенч: год %s заморожен", year)
        return existing
    if existing is None:
        existing = PortalBenchYearSnapshot(year=year, source=source, frozen=frozen, records=records)
        session.add(existing)
    else:
        existing.source = source
        existing.frozen = frozen
        existing.records = records
    existing.updated_at = now_utc()
    await session.commit()
    await session.refresh(existing)
    return existing


async def load_sync_state(session: AsyncSession) -> PortalBenchSyncState | None:
    return await session.get(PortalBenchSyncState, SYNC_STATE_ID)


async def load_dashboard(
    session: AsyncSession,
    *,
    year: int | None = None,
    specialization: str | list[str] | None = None,
    month: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> DashboardPayload:
    all_records = await ensure_snapshots_and_load_records(session)
    catalog = filter_catalog(all_records)
    records = filter_records(
        all_records,
        year=year,
        specialization=specialization,
        month=month,
        date_from=date_from,
        date_to=date_to,
    )
    payload = build_dashboard(records)
    payload["years"] = catalog["years"]
    payload["specializations"] = catalog["specializations"]
    settings = get_settings()
    state = await load_sync_state(session)
    last_success_at = state.last_success_at if state is not None else None
    if not settings.google_sheets_enabled:
        is_stale = False
    else:
        stale_after = settings.google_sheets_stale_after_seconds
        is_stale = last_success_at is None or now_utc() - last_success_at > timedelta(seconds=stale_after)
    payload["last_success_at"] = last_success_at.isoformat() if last_success_at is not None else None
    payload["is_stale"] = is_stale
    payload["stale_message"] = STALE_MESSAGE if is_stale else None
    return payload
