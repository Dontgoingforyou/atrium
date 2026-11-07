from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

TIME_ENTRY_TASK_NAME_MAX_LENGTH = 500
TIME_ENTRY_NOTE_MAX_LENGTH = 4000


class PortalTimeEntryCreate(BaseModel):
    worked_on: date = Field(description="Календарный день, за который списано время")
    minutes: int = Field(ge=1, le=1440, description="Длительность в минутах (1–1440)")
    task_id: uuid.UUID | None = Field(default=None, description="Связанная задача (если есть)")
    task_name: str | None = Field(
        default=None, max_length=TIME_ENTRY_TASK_NAME_MAX_LENGTH, description="Название задачи (свободный текст)"
    )
    note: str | None = Field(
        default=None, max_length=TIME_ENTRY_NOTE_MAX_LENGTH, description="Описание выполненной работы"
    )
    is_tour_demo: bool = Field(
        default=False,
        description="Учебная запись guided tour (только create; удаление — автор записи)",
    )


class PortalTimeEntryBulkCreate(BaseModel):
    """Массовое создание повторяющихся записей: диапазон дат + фильтр по дням недели.

    Удобно для дейликов и других повторяющихся задач — не нужно добавлять запись
    за каждый день руками.
    """

    date_from: date = Field(description="Начало диапазона дат (включительно)")
    date_to: date = Field(description="Конец диапазона дат (включительно)")
    weekdays: list[int] = Field(
        default_factory=lambda: [0, 1, 2, 3, 4],
        description="Дни недели, за которые создавать записи: 0=Пн … 6=Вс. По умолчанию Пн–Пт",
    )
    minutes: int = Field(ge=1, le=1440, description="Длительность в минутах — одинаковая для всех записей")
    task_id: uuid.UUID | None = Field(default=None, description="Связанная задача (если есть)")
    task_name: str | None = Field(
        default=None, max_length=TIME_ENTRY_TASK_NAME_MAX_LENGTH, description="Название задачи (свободный текст)"
    )
    note: str | None = Field(
        default=None, max_length=TIME_ENTRY_NOTE_MAX_LENGTH, description="Описание выполненной работы"
    )

    @field_validator("weekdays")
    @classmethod
    def _validate_weekdays(cls, value: list[int]) -> list[int]:
        invalid = sorted({d for d in value if d < 0 or d > 6})
        if invalid:
            raise ValueError(f"Недопустимые значения дней недели: {invalid} (допустимо 0=Пн … 6=Вс)")
        return value


class PortalTimeEntryUpdate(BaseModel):
    expected_version: int = Field(..., ge=1, description="Версия записи, прочитанная клиентом (CAS)")
    worked_on: date | None = None
    minutes: int | None = Field(default=None, ge=1, le=1440)
    task_id: uuid.UUID | None = None
    task_name: str | None = Field(default=None, max_length=TIME_ENTRY_TASK_NAME_MAX_LENGTH)
    note: str | None = Field(default=None, max_length=TIME_ENTRY_NOTE_MAX_LENGTH)


class PortalTimeEntryRead(BaseModel):
    id: uuid.UUID
    user_sub: str
    task_id: uuid.UUID | None
    task_name: str | None
    worked_on: date
    minutes: int
    note: str | None
    is_tour_demo: bool = False
    version: int = Field(description="Версия для optimistic locking (CAS)")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PortalTimeEntrySummaryRead(BaseModel):
    """Сводка по отфильтрованным записям (тот же контур видимости, что у списка)."""

    total_minutes: int = Field(description="Сумма minutes по всем попавшим в выборку записям")
    entries_count: int


class PortalTimeEntryReportBucket(BaseModel):
    """Один бакет периодического отчёта (неделя или месяц)."""

    period_label: str = Field(description="Метка периода: '2026-W15' для недель или '2026-04' для месяцев")
    date_start: date
    date_end: date
    total_minutes: int
    entries_count: int


class PortalTimeEntryImportRowError(BaseModel):
    """Ошибка разбора одной строки CSV при импорте (строка не привела к созданию записи)."""

    row: int = Field(description="Номер строки в CSV (с учётом строки заголовка)")
    message: str = Field(description="Причина, по которой строка пропущена")


class PortalTimeEntryImportResult(BaseModel):
    """Результат импорта таймшитов из CSV-выгрузки Jira (Tempo worklog)."""

    created: list[PortalTimeEntryRead] = Field(description="Успешно созданные записи")
    created_count: int
    skipped_count: int
    errors: list[PortalTimeEntryImportRowError] = Field(
        default_factory=list, description="Построчные ошибки для пропущенных строк"
    )


class PortalSpecialistMonthlySummary(BaseModel):
    """Сводка по специалисту за выбранный месяц (для менеджерского дашборда)."""

    user_sub: str
    full_name: str | None
    email: str | None
    total_minutes: int
    entries_count: int
    month: str = Field(description="Месяц в формате YYYY-MM")
