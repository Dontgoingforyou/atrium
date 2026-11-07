"""Выгрузка текущего среза дашборда бенч (csv / xlsx)."""

from __future__ import annotations

import asyncio
import csv
import io
from functools import partial
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.portal_bench.services._ingest import BenchRecord
from app.portal_bench.services._metrics import filter_records
from app.portal_bench.services._snapshot import ensure_snapshots_and_load_records

ExportFormat = Literal["csv", "xlsx"]

_CONTENT_TYPES: dict[ExportFormat, str] = {
    "csv": "text/csv; charset=utf-8-sig",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
_EXTENSIONS: dict[ExportFormat, str] = {"csv": "csv", "xlsx": "xlsx"}
_HEADERS = [
    "Год",
    "Месяц",
    "Разработчик",
    "Специализация",
    "CV",
    "Скрининг",
    "Внутреннее",
    "Тех. этап 1",
    "Финал",
    "Отказ",
    "Оффер",
    "Выход",
    "Ставка",
    "Дата выхода",
    "Дата запроса",
    "Комментарий",
]
_FORMULA_PREFIXES = frozenset({"=", "+", "-", "@", "\t", "\r"})


def _sanitize_spreadsheet_text(value: str) -> str:
    """Нейтрализует CSV/Excel formula injection: ведущие = + - @ и управляющие."""
    if value and value[0] in _FORMULA_PREFIXES:
        return f"'{value}"
    return value


def _cell(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return _sanitize_spreadsheet_text(str(value))


def _rows(records: list[BenchRecord]) -> list[list[object]]:
    result: list[list[object]] = []
    for record in records:
        result.append(
            [
                _cell(record.get("year")),
                _cell(record.get("month")),
                _cell(record.get("developer")),
                _cell(record.get("specialization")),
                _cell(record.get("cv_sent") or 0),
                _cell(record.get("screening") or 0),
                _cell(record.get("internal_interview") or 0),
                _cell(record.get("tech_stage_1") or 0),
                _cell(record.get("final_stage") or 0),
                _cell(record.get("rejection") or 0),
                _cell(record.get("offer") or 0),
                _cell(record.get("project_start") or 0),
                _cell(record.get("rate")),
                _cell(record.get("start_date")),
                _cell(record.get("request_date")),
                _cell(record.get("comment")),
            ]
        )
    return result


def _to_csv(records: list[BenchRecord]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, dialect="excel")
    writer.writerow(_HEADERS)
    for row in _rows(records):
        writer.writerow(row)
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def _to_xlsx(records: list[BenchRecord]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Бенч"
    for col_idx, header in enumerate(_HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = Font(bold=True)
    for row_idx, row in enumerate(_rows(records), start=2):
        for col_idx, val in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=val)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def export_bench_slice(
    session: AsyncSession,
    *,
    export_format: ExportFormat,
    year: int | None = None,
    specialization: str | list[str] | None = None,
    month: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[bytes, str, str]:
    if export_format not in _CONTENT_TYPES:
        raise ValidationError("Поддерживаются форматы csv и xlsx")
    records = filter_records(
        await ensure_snapshots_and_load_records(session),
        year=year,
        specialization=specialization,
        month=month,
        date_from=date_from,
        date_to=date_to,
    )
    loop = asyncio.get_running_loop()
    builder = _to_csv if export_format == "csv" else _to_xlsx
    file_bytes = await loop.run_in_executor(None, partial(builder, records))
    filename = f"bench_dashboard.{_EXTENSIONS[export_format]}"
    return file_bytes, filename, _CONTENT_TYPES[export_format]
