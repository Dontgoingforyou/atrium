"""Импорт таймшитов из CSV-выгрузки Jira (Tempo worklog).

Используются только колонки «Тема задачи», «Дата работы» и «Часов» — остальные
колонки выгрузки (ключ задачи, проект, эпик и т.п.) не читаются и не сохраняются.
"""

from __future__ import annotations

import csv
import io
import logging
import math
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_time_entry import PortalTimeEntry
from app.portal_time_entries.schemas.time_entry import TIME_ENTRY_TASK_NAME_MAX_LENGTH
from app.portal_time_entries.services._time_entry_reports import (
    ensure_timesheets_access as _ensure_timesheets_access,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

_COL_TASK_NAME = "Тема задачи"
_COL_WORKED_ON = "Дата работы"
_COL_HOURS = "Часов"
_REQUIRED_HEADERS = (_COL_TASK_NAME, _COL_WORKED_ON, _COL_HOURS)

_MAX_IMPORT_ROWS = 1000


@dataclass(frozen=True)
class ParsedImportRow:
    task_name: str
    worked_on: date
    minutes: int


@dataclass(frozen=True)
class ImportRowError:
    row: int
    message: str


def _parse_worked_on(raw: str) -> date:
    value = raw.strip()
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M").date()
    except ValueError:
        pass
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise ValueError(f"Не удалось разобрать дату «{raw}»") from exc


def _parse_hours_to_minutes(raw: str) -> int:
    value = raw.strip().replace(",", ".")
    try:
        hours = float(value)
    except ValueError as exc:
        raise ValueError(f"Не удалось разобрать число часов «{raw}»") from exc
    if not math.isfinite(hours):
        raise ValueError(f"Не удалось разобрать число часов «{raw}»")
    minutes = round(hours * 60)
    if minutes <= 0:
        raise ValueError("Часы должны быть больше 0")
    if minutes > 1440:
        raise ValueError("Часы за одну запись не могут превышать 24ч")
    return minutes


def parse_jira_worklog_csv(file_bytes: bytes) -> tuple[list[ParsedImportRow], list[ImportRowError]]:
    """Разбирает CSV-выгрузку Jira Tempo. Не обращается к БД — чистая функция.

    Построчная валидация: некорректная строка не прерывает разбор остальных
    (её номер и причина попадают в список ошибок).
    """
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("Файл должен быть в кодировке UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise ValidationError("Пустой CSV-файл")
    missing = [h for h in _REQUIRED_HEADERS if h not in reader.fieldnames]
    if missing:
        raise ValidationError(f"В файле отсутствуют колонки: {', '.join(missing)}")

    rows: list[ParsedImportRow] = []
    errors: list[ImportRowError] = []
    # Строка 1 — заголовок, поэтому данные нумеруем начиная со 2.
    for row_num, raw_row in enumerate(reader, start=2):
        if row_num - 1 > _MAX_IMPORT_ROWS:
            raise ValidationError(f"Слишком много строк в файле (максимум {_MAX_IMPORT_ROWS})")

        task_name = (raw_row.get(_COL_TASK_NAME) or "").strip()
        if not task_name:
            errors.append(ImportRowError(row=row_num, message="Не указана тема задачи"))
            continue
        if len(task_name) > TIME_ENTRY_TASK_NAME_MAX_LENGTH:
            errors.append(
                ImportRowError(
                    row=row_num,
                    message=f"Тема задачи длиннее {TIME_ENTRY_TASK_NAME_MAX_LENGTH} символов",
                )
            )
            continue

        try:
            worked_on = _parse_worked_on(raw_row.get(_COL_WORKED_ON) or "")
        except ValueError as exc:
            errors.append(ImportRowError(row=row_num, message=str(exc)))
            continue

        try:
            minutes = _parse_hours_to_minutes(raw_row.get(_COL_HOURS) or "")
        except ValueError as exc:
            errors.append(ImportRowError(row=row_num, message=str(exc)))
            continue

        rows.append(ParsedImportRow(task_name=task_name, worked_on=worked_on, minutes=minutes))

    return rows, errors


async def import_jira_worklog_csv(
    session: AsyncSession,
    user: UserPublic,
    file_bytes: bytes,
) -> tuple[list[PortalTimeEntry], list[ImportRowError]]:
    """Импортирует записи таймшита из CSV-выгрузки Jira от имени текущего пользователя.

    Каждая валидная строка CSV становится отдельной записью `PortalTimeEntry`
    (без привязки к `task_id` — только свободный текст `task_name`).
    """
    _ensure_timesheets_access(user, log_denial=True)

    parsed_rows, errors = parse_jira_worklog_csv(file_bytes)

    timestamp = now_utc()
    entries = [
        PortalTimeEntry(
            user_sub=user.sub,
            task_id=None,
            task_name=row.task_name,
            worked_on=row.worked_on,
            minutes=row.minutes,
            note=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        for row in parsed_rows
    ]
    session.add_all(entries)
    await session.commit()

    if errors:
        logger.warning(
            "Импорт таймшитов из Jira CSV: user_sub=%s создано=%d пропущено=%d",
            user.sub,
            len(entries),
            len(errors),
        )

    return entries, errors
