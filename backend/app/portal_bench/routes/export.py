"""Выгрузка среза дашборда бенч."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.deps import DbSession
from app.api.deps_auth import PortalManagerOrAdminUser
from app.portal_bench.services._export import ExportFormat, export_bench_slice

router = APIRouter(prefix="/portal/bench", tags=["Портал · Бенч"])


@router.get(
    "/export",
    summary="Выгрузка текущего среза дашборда бенч",
    description="CSV или XLSX тех же отфильтрованных строк, что на экране. Менеджер или администратор портала.",
    response_class=Response,
)
async def export_bench(
    _user: PortalManagerOrAdminUser,
    db: DbSession,
    format: ExportFormat = Query(..., description="Формат файла: csv или xlsx"),
    year: int | None = Query(default=None, ge=2000, le=2100),
    specialization: list[str] | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> Response:
    file_bytes, filename, content_type = await export_bench_slice(
        db,
        export_format=format,
        year=year,
        specialization=specialization,
        month=month,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
    )
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
