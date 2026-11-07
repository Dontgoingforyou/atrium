from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import Response

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.core.exceptions import PayloadTooLargeError, ValidationError
from app.portal_time_entries.schemas.time_entry import (
    PortalSpecialistMonthlySummary,
    PortalTimeEntryBulkCreate,
    PortalTimeEntryCreate,
    PortalTimeEntryImportResult,
    PortalTimeEntryImportRowError,
    PortalTimeEntryRead,
    PortalTimeEntryReportBucket,
    PortalTimeEntrySummaryRead,
    PortalTimeEntryUpdate,
)
from app.portal_time_entries.services import time_entry as svc
from app.portal_time_entries.services._export import ExportFormat, export_specialist_time_entries
from app.portal_time_entries.services.time_entry import month_date_range
from app.schemas.pagination import PagedResponse

router = APIRouter(prefix="/portal", tags=["Таймшиты"])

_MONTH_PATTERN = r"^\d{4}-\d{2}$"

_ALLOWED_CSV_CONTENT_TYPES = frozenset(
    {"text/csv", "application/vnd.ms-excel", "application/csv", "application/octet-stream"}
)
_MAX_CSV_SIZE_BYTES = 5 * 1024 * 1024
_CSV_CHUNK_SIZE = 65536


async def _read_upload_bounded(file: UploadFile, max_bytes: int) -> bytes:
    """Читает файл по чанкам с ранним отказом при превышении лимита.

    Не буферизует файл целиком до проверки размера — иначе загрузка большого
    файла (в т.ч. параллельная) была бы вектором DoS по памяти.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CSV_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise PayloadTooLargeError(f"Файл превышает лимит {max_bytes // (1024 * 1024)} МБ")
        chunks.append(chunk)
    return b"".join(chunks)


@router.get(
    "/time-entries/export",
    summary="Выгрузка таймшитов специалиста за месяц",
    description=(
        "Возвращает файл с записями рабочего времени в формате CSV, XLSX или PDF. "
        "RBAC: developer — только свои данные; менеджер — может указать user_sub; "
        "admin — любой или без фильтра. "
        "Выгрузка без пагинации: весь месяц = обоснованный admin-export, "
        "не более 5000 строк (иначе 422)."
    ),
    response_class=Response,
)
async def export_time_entries(
    user: CurrentUser,
    db: DbSession,
    format: ExportFormat = Query(..., description="Формат файла: csv, xlsx, pdf"),
    month: str = Query(..., pattern=_MONTH_PATTERN, description="Месяц YYYY-MM (обязательный)"),
    user_sub: str | None = Query(default=None, description="Фильтр по автору (для менеджера/администратора)"),
) -> Response:
    file_bytes, filename, content_type = await export_specialist_time_entries(
        db,
        user,
        export_format=format,
        month=month,
        user_sub=user_sub,
    )
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/time-entries/summary",
    summary="Сводка по записям таймшита",
    description=(
        "Сумма минут и число записей в заданных границах. Видимость как у списка: "
        "разработчик — только свои записи; менеджер — может фильтровать по `user_sub`; "
        "администратор — все или фильтр `user_sub`."
    ),
    response_model=PortalTimeEntrySummaryRead,
)
async def summarize_time_entries(
    user: CurrentUser,
    db: DbSession,
    user_sub: str | None = Query(default=None, description="Фильтр по автору (для менеджера/администратора)"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None, pattern=_MONTH_PATTERN, description="Месяц YYYY-MM"),
    task_id: uuid.UUID | None = Query(default=None),
) -> PortalTimeEntrySummaryRead:
    date_from, date_to = _resolve_date_range(month, date_from, date_to)
    return await svc.summarize_time_entries(
        db,
        user,
        filter_user_sub=user_sub,
        date_from=date_from,
        date_to=date_to,
        task_id=task_id,
    )


@router.get(
    "/time-entries/report",
    summary="Периодический отчёт по таймшитам",
    description=(
        "Группировка записей по неделям (`group_by=week`) или месяцам (`group_by=month`). "
        "Возвращает список бакетов с суммой минут и числом записей за каждый период. "
        "RBAC: разработчик видит только свои данные; менеджер/администратор — все или фильтр `user_sub`."
    ),
    response_model=list[PortalTimeEntryReportBucket],
)
async def report_time_entries(
    user: CurrentUser,
    db: DbSession,
    group_by: Literal["week", "month"] = Query(default="week", description="Период группировки"),
    user_sub: str | None = Query(default=None, description="Фильтр по автору (для менеджера/администратора)"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None, pattern=_MONTH_PATTERN, description="Месяц YYYY-MM"),
    task_id: uuid.UUID | None = Query(default=None),
) -> list[PortalTimeEntryReportBucket]:
    date_from, date_to = _resolve_date_range(month, date_from, date_to)
    return await svc.get_time_entries_report(
        db,
        user,
        group_by=group_by,
        filter_user_sub=user_sub,
        date_from=date_from,
        date_to=date_to,
        task_id=task_id,
    )


@router.get(
    "/time-entries/specialists",
    summary="Список специалистов с суммарными часами таймшитов за месяц",
    description=(
        "Все пользователи с записями таймшита в выбранном месяце: сумма минут и число записей. "
        "Доступ: менеджер АУ (gid_number=10000) или portal_admin."
    ),
    response_model=PagedResponse[PortalSpecialistMonthlySummary],
)
async def list_specialists_timesheets_monthly(
    user: CurrentUser,
    db: DbSession,
    month: str = Query(..., pattern=_MONTH_PATTERN, description="Месяц YYYY-MM"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PagedResponse[PortalSpecialistMonthlySummary]:
    items, total = await svc.list_specialists_monthly_summary(db, user, month=month, limit=limit, offset=offset)
    return PagedResponse(items=items, total=total, skip=offset, limit=limit)


@router.get(
    "/time-entries",
    summary="Список записей таймшита",
    description=(
        "Постраничный список. `limit` до 500 — исключение из типичного le=200: "
        "таблица месяца специалиста целиком на одной странице."
    ),
    response_model=PagedResponse[PortalTimeEntryRead],
)
async def list_time_entries(
    user: CurrentUser,
    db: DbSession,
    user_sub: str | None = Query(default=None, description="Фильтр по автору (для менеджера/администратора)"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None, pattern=_MONTH_PATTERN, description="Месяц YYYY-MM"),
    task_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PagedResponse[PortalTimeEntryRead]:
    date_from, date_to = _resolve_date_range(month, date_from, date_to)
    rows, total = await svc.list_time_entries(
        db,
        user,
        filter_user_sub=user_sub,
        date_from=date_from,
        date_to=date_to,
        task_id=task_id,
        limit=limit,
        offset=offset,
    )
    return PagedResponse(
        items=[PortalTimeEntryRead.model_validate(r) for r in rows],
        total=total,
        skip=offset,
        limit=limit,
    )


@router.post(
    "/time-entries",
    summary="Создать запись таймшита",
    response_model=PortalTimeEntryRead,
    status_code=201,
)
async def create_time_entry(
    user: CurrentUser,
    db: DbSession,
    body: PortalTimeEntryCreate,
) -> PortalTimeEntryRead:
    row = await svc.create_time_entry(db, user, body)
    return PortalTimeEntryRead.model_validate(row)


@router.post(
    "/time-entries/bulk",
    summary="Массовое создание повторяющихся записей таймшита",
    description=(
        "Создаёт по одной записи на каждую дату в диапазоне `date_from`–`date_to`, "
        "у которой день недели входит в `weekdays` (по умолчанию Пн–Пт). Удобно для "
        "дейликов и других повторяющихся задач. Лимит — 200 записей за один запрос."
    ),
    response_model=list[PortalTimeEntryRead],
    status_code=201,
)
async def create_time_entries_bulk(
    user: CurrentUser,
    db: DbSession,
    body: PortalTimeEntryBulkCreate,
) -> list[PortalTimeEntryRead]:
    rows = await svc.create_time_entries_bulk(db, user, body)
    return [PortalTimeEntryRead.model_validate(r) for r in rows]


@router.post(
    "/time-entries/import-jira-csv",
    summary="Импорт таймшитов из CSV-выгрузки Jira (Tempo worklog)",
    description=(
        "Принимает CSV-выгрузку Jira Tempo worklog и читает из неё только колонки "
        "«Тема задачи», «Дата работы» и «Часов». Создаёт по одной записи таймшита на "
        "каждую валидную строку от имени текущего пользователя (без привязки к задаче на "
        "доске — только свободный текст названия). Некорректные строки не прерывают импорт "
        "остальных — их номера и причины возвращаются в `errors`. "
        "Повторная загрузка того же файла создаёт дубликаты записей."
    ),
    response_model=PortalTimeEntryImportResult,
    status_code=201,
)
async def import_jira_csv(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> PortalTimeEntryImportResult:
    if not (file.filename or "").lower().endswith(".csv"):
        raise ValidationError("Ожидается файл с расширением .csv")
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in _ALLOWED_CSV_CONTENT_TYPES:
        raise ValidationError("Недопустимый тип файла — ожидается CSV")

    content = await _read_upload_bounded(file, _MAX_CSV_SIZE_BYTES)
    created, errors = await svc.import_jira_worklog_csv(db, user, content)
    return PortalTimeEntryImportResult(
        created=[PortalTimeEntryRead.model_validate(r) for r in created],
        created_count=len(created),
        skipped_count=len(errors),
        errors=[PortalTimeEntryImportRowError(row=e.row, message=e.message) for e in errors],
    )


@router.patch(
    "/time-entries/{entry_id}",
    summary="Обновить запись таймшита",
    response_model=PortalTimeEntryRead,
)
async def update_time_entry(
    entry_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalTimeEntryUpdate,
) -> PortalTimeEntryRead:
    row = await svc.update_time_entry(db, user, entry_id, body)
    return PortalTimeEntryRead.model_validate(row)


@router.delete(
    "/time-entries/{entry_id}",
    summary="Удалить запись таймшита",
    description="Безвозвратное удаление строки из БД. Доступно владельцу записи или администратору портала.",
    status_code=204,
)
async def delete_time_entry(
    entry_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await svc.delete_time_entry(db, user, entry_id)


# ---------------------------------------------------------------------------
# Вспомогательная функция
# ---------------------------------------------------------------------------


def _resolve_date_range(
    month: str | None,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date | None, date | None]:
    """Если передан ``month`` — возвращает диапазон дат этого месяца; иначе — переданные значения."""
    if month is not None:
        return month_date_range(month)
    return date_from, date_to
