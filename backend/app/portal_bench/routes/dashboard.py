"""Чтение дашборда бенч."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import PortalManagerOrAdminUser
from app.portal_bench.schemas.dashboard import BenchDashboardRead
from app.portal_bench.services._snapshot import load_dashboard

router = APIRouter(prefix="/portal/bench", tags=["Портал · Бенч"])


@router.get(
    "/dashboard",
    summary="Сводка дашборда отчётов и бенч",
    description="Агрегат карточек, графиков и таблиц по снимку. Менеджер или администратор портала.",
)
async def get_bench_dashboard(
    _user: PortalManagerOrAdminUser,
    db: DbSession,
    year: int | None = Query(default=None, ge=2000, le=2100),
    specialization: list[str] | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> BenchDashboardRead:
    payload = await load_dashboard(
        db,
        year=year,
        specialization=specialization,
        month=month,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
    )
    return BenchDashboardRead.model_validate(payload)
