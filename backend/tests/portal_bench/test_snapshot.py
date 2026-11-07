"""Снимок года: идемпотентный seed 2025 и запрет перезаписи frozen."""

from __future__ import annotations

import json

from app.infrastructure.db.models.portal_bench import PortalBenchYearSnapshot
from app.portal_bench.constants import committed_seed_json_path
from app.portal_bench.services._snapshot import (
    ensure_snapshots_and_load_records,
    upsert_year_snapshot,
)
from sqlalchemy.ext.asyncio import AsyncSession


def test_committed_seed_json_is_anonymized() -> None:
    for stem in ("year_2025", "year_2026"):
        payload = json.loads(committed_seed_json_path(stem).read_text(encoding="utf-8"))
        for row in payload.get("raw_data") or []:
            assert str(row.get("developer") or "").startswith("Разработчик")
            assert not row.get("comment")


async def test_ensure_snapshots_and_load_records_seeds_2025_once(sqlite_session: AsyncSession) -> None:
    first = await ensure_snapshots_and_load_records(sqlite_session)
    second = await ensure_snapshots_and_load_records(sqlite_session)
    assert first
    assert first == second
    years = {int(r.get("year") or 0) for r in first}
    assert 2025 in years
    assert 2026 in years
    row = await sqlite_session.get(PortalBenchYearSnapshot, 2025)
    assert row is not None
    assert row.frozen is True
    live = await sqlite_session.get(PortalBenchYearSnapshot, 2026)
    assert live is not None
    assert live.frozen is False


async def test_upsert_does_not_overwrite_frozen_2025(sqlite_session: AsyncSession) -> None:
    await ensure_snapshots_and_load_records(sqlite_session)
    original = await sqlite_session.get(PortalBenchYearSnapshot, 2025)
    assert original is not None
    original_len = len(original.records)

    await upsert_year_snapshot(
        sqlite_session,
        year=2025,
        records=[{"year": 2025, "developer": "не должен попасть"}],
        source="sheets",
        frozen=False,
    )
    row = await sqlite_session.get(PortalBenchYearSnapshot, 2025)
    assert row is not None
    assert row.frozen is True
    assert len(row.records) == original_len
    assert row.source == "seed"


async def test_load_reclassifies_spec_hidden_inside_first_name(
    sqlite_session: AsyncSession,
) -> None:
    await upsert_year_snapshot(
        sqlite_session,
        year=2026,
        records=[
            {
                "year": 2026,
                "developer": "Александр Анфимов DA",
                "specialization": "SA",
                "cv_sent": 0,
                "offer": 0,
                "project_start": 1,
            }
        ],
        source="sheets",
        frozen=False,
    )
    records = await ensure_snapshots_and_load_records(sqlite_session)
    anfimov = next(row for row in records if row.get("developer") == "Александр Анфимов DA")
    assert anfimov["specialization"] == "DA"


async def test_upsert_writes_live_year(sqlite_session: AsyncSession) -> None:
    await upsert_year_snapshot(
        sqlite_session,
        year=2026,
        records=[{"year": 2026, "developer": "Новый", "specialization": "iOS"}],
        source="sheets",
        frozen=False,
    )
    merged = await ensure_snapshots_and_load_records(sqlite_session)
    years = {int(r.get("year") or 0) for r in merged}
    assert 2025 in years
    assert 2026 in years
    live = await sqlite_session.get(PortalBenchYearSnapshot, 2026)
    assert live is not None
    assert live.frozen is False
    assert live.source == "sheets"
