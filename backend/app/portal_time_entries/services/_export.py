from __future__ import annotations

import asyncio
import csv
import io
import logging
import os
import re
from datetime import date
from functools import partial
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, ValidationError
from app.infrastructure.db.models.portal_time_entry import PortalTimeEntry
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_time_entries.services._time_entry_reports import (
    effective_user_sub_filter,
    ensure_timesheets_access,
    month_date_range,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

ExportFormat = Literal["csv", "xlsx", "pdf"]

_CONTENT_TYPES: dict[ExportFormat, str] = {
    "csv": "text/csv; charset=utf-8-sig",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}

_EXTENSIONS: dict[ExportFormat, str] = {
    "csv": "csv",
    "xlsx": "xlsx",
    "pdf": "pdf",
}

_HEADERS = ["Дата", "Задача", "Минуты", "Часы", "Примечание"]

# Cap выгрузки без пагинации — как _EXPORT_TASK_LIMIT у задач.
_EXPORT_ENTRY_LIMIT = 5000

_FORMULA_PREFIXES = frozenset({"=", "+", "-", "@", "\t", "\r"})

# Пути поиска Unicode-шрифта (Cyrillic) для PDF.
# Docker-образ: fonts-dejavu-core → /usr/share/fonts/truetype/dejavu/
# Fedora/RHEL: /usr/share/fonts/dejavu-sans-fonts/
# Arch/Manjaro: /usr/share/fonts/TTF/
# macOS (Homebrew): /opt/homebrew/share/fonts/, ~/Library/Fonts/
_FONT_SEARCH_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/opt/homebrew/share/fonts/DejaVuSans.ttf",
    os.path.expanduser("~/Library/Fonts/DejaVuSans.ttf"),
]


def _find_unicode_font() -> str | None:
    for p in _FONT_SEARCH_PATHS:
        if os.path.exists(p):
            return p
    return None


# ---------------------------------------------------------------------------
# Синхронные генераторы файлов (вызываются через run_in_executor)
# ---------------------------------------------------------------------------


def _sanitize_spreadsheet_text(value: str) -> str:
    """Нейтрализует CSV/Excel formula injection: ведущие = + - @ и управляющие."""
    if value and value[0] in _FORMULA_PREFIXES:
        return f"'{value}"
    return value


def _escape_pdf_paragraph(value: str) -> str:
    """ReportLab Paragraph интерпретирует XML — экранируем пользовательский текст."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _rows_to_list(entries: list[PortalTimeEntry], *, spreadsheet: bool) -> list[list[object]]:
    result = []
    for e in entries:
        task_name = e.task_name or ""
        note = e.note or ""
        if spreadsheet:
            task_name = _sanitize_spreadsheet_text(task_name)
            note = _sanitize_spreadsheet_text(note)
        result.append(
            [
                e.worked_on.isoformat() if isinstance(e.worked_on, date) else str(e.worked_on),
                task_name,
                e.minutes,
                round(e.minutes / 60, 2),
                note,
            ]
        )
    return result


def _to_csv(entries: list[PortalTimeEntry], display_label: str, month: str) -> bytes:
    """Генерирует CSV с UTF-8 BOM (совместимость с Excel)."""
    buf = io.StringIO()
    writer = csv.writer(buf, dialect="excel")
    writer.writerow([f"Таймшиты: {display_label}", f"Месяц: {month}"])
    writer.writerow([])
    writer.writerow(_HEADERS)
    for row in _rows_to_list(entries, spreadsheet=True):
        writer.writerow(row)
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def _to_xlsx(entries: list[PortalTimeEntry], display_label: str, month: str) -> bytes:
    """Генерирует XLSX через openpyxl."""
    from openpyxl import Workbook  # noqa: PLC0415
    from openpyxl.styles import Font  # noqa: PLC0415

    wb = Workbook()
    ws = wb.active
    ws.title = "Таймшиты"

    ws["A1"] = f"Таймшиты: {display_label}"
    ws["B1"] = f"Месяц: {month}"

    header_row = 3
    for col_idx, header in enumerate(_HEADERS, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.font = Font(bold=True)

    for row_idx, row in enumerate(_rows_to_list(entries, spreadsheet=True), start=header_row + 1):
        for col_idx, val in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=val)

    # Ширина колонок
    col_widths = [12, 40, 8, 8, 50]
    for i, w in enumerate(col_widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _to_pdf(entries: list[PortalTimeEntry], display_label: str, month: str) -> bytes:
    """Генерирует PDF через reportlab.

    При наличии системного DejaVuSans используется он (поддержка кириллицы).
    В Docker-образе шрифт устанавливается через пакет fonts-dejavu-core.
    При отсутствии шрифта на диске используется стандартный Helvetica (без кириллицы).
    """
    from reportlab.lib import colors  # noqa: PLC0415
    from reportlab.lib.pagesizes import A4  # noqa: PLC0415
    from reportlab.lib.styles import ParagraphStyle  # noqa: PLC0415
    from reportlab.pdfbase import pdfmetrics  # noqa: PLC0415
    from reportlab.pdfbase.ttfonts import TTFont  # noqa: PLC0415
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: PLC0415

    font_path = _find_unicode_font()
    if font_path and not _is_font_registered("DejaVu"):
        try:
            pdfmetrics.registerFont(TTFont("DejaVu", font_path))
        except Exception as e:
            logger.warning("Не удалось загрузить шрифт DejaVu для PDF: %s", e)
            font_path = None

    font_name = "DejaVu" if font_path and _is_font_registered("DejaVu") else "Helvetica"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    # Создаём собственный стиль вместо мутации глобального getSampleStyleSheet().
    style_normal = ParagraphStyle(
        name="CosmoletNormal",
        fontName=font_name,
        fontSize=10,
        leading=14,
    )

    elements = []
    elements.append(Paragraph(f"Таймшиты: {_escape_pdf_paragraph(display_label)}", style_normal))
    elements.append(Paragraph(f"Месяц: {_escape_pdf_paragraph(month)}", style_normal))
    elements.append(Spacer(1, 12))

    table_data = [_HEADERS] + _rows_to_list(entries, spreadsheet=False)
    table = Table(
        table_data,
        colWidths=[70, 160, 45, 45, 150],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("ALIGN", (2, 0), (3, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(table)

    doc.build(elements)
    return buf.getvalue()


def _is_font_registered(name: str) -> bool:
    from reportlab.pdfbase import pdfmetrics  # noqa: PLC0415

    try:
        pdfmetrics.getFont(name)
        return True
    except KeyError:
        return False


# ---------------------------------------------------------------------------
# Публичная async-функция сервиса
# ---------------------------------------------------------------------------


async def export_specialist_time_entries(
    session: AsyncSession,
    user: UserPublic,
    export_format: ExportFormat,
    month: str,
    user_sub: str | None,
) -> tuple[bytes, str, str]:
    """Выгружает записи таймшита специалиста за месяц в указанном формате.

    Исключение из правила «сервис возвращает ORM»: специализированный read-сценарий,
    возвращает (bytes, filename, content_type).

    RBAC: те же правила, что у list_time_entries:
    - developer видит только свой sub;
    - менеджер может указать user_sub;
    - admin — любой.

    Выборка без пагинации обоснована: это admin-export конкретного месяца (fastapi-backend.mdc).
    """
    ensure_timesheets_access(user)

    effective_sub: str | None
    try:
        effective_sub = effective_user_sub_filter(user, user_sub)
    except ForbiddenError:
        logger.warning(
            "Отказ экспорта таймшитов: user_sub=%s requested_sub=%s",
            user.sub,
            user_sub,
        )
        raise

    date_from, date_to = month_date_range(month)

    stmt = select(PortalTimeEntry).order_by(PortalTimeEntry.worked_on, PortalTimeEntry.created_at)
    if effective_sub is not None:
        stmt = stmt.where(PortalTimeEntry.user_sub == effective_sub)
    stmt = stmt.where(
        PortalTimeEntry.worked_on >= date_from,
        PortalTimeEntry.worked_on <= date_to,
    )

    stmt = stmt.limit(_EXPORT_ENTRY_LIMIT + 1)
    entries = list((await session.scalars(stmt)).all())
    if len(entries) > _EXPORT_ENTRY_LIMIT:
        raise ValidationError(f"Слишком много записей для выгрузки (максимум {_EXPORT_ENTRY_LIMIT}). Уточните фильтр.")

    # Формируем читаемый заголовок и имя файла — используем профиль вместо сырого sub.
    if effective_sub:
        profile = await session.get(PortalUserProfile, effective_sub)
        display = (profile.full_name or profile.email or effective_sub) if profile else effective_sub
    else:
        display = "all"
    safe_name = re.sub(r"[^\w\-.]", "_", display)
    filename = f"timesheets_{safe_name}_{month}.{_EXTENSIONS[export_format]}"
    content_type = _CONTENT_TYPES[export_format]

    loop = asyncio.get_running_loop()
    if export_format == "csv":
        file_bytes = await loop.run_in_executor(None, partial(_to_csv, entries, display, month))
    elif export_format == "xlsx":
        file_bytes = await loop.run_in_executor(None, partial(_to_xlsx, entries, display, month))
    else:
        file_bytes = await loop.run_in_executor(None, partial(_to_pdf, entries, display, month))

    return file_bytes, filename, content_type
