from __future__ import annotations

from pydantic import BaseModel, Field

from app.portal_collab.schemas.task import PortalTaskRead
from app.portal_favorites.schemas.favorite import PortalFavoriteRead
from app.portal_time_entries.schemas.time_entry import (
    PortalTimeEntryReportBucket,
    PortalTimeEntrySummaryRead,
)


class TaskOpenByPriorityRead(BaseModel):
    """Число открытых задач (todo + in_progress) по приоритету."""

    low: int = Field(ge=0, default=0)
    medium: int = Field(ge=0, default=0)
    high: int = Field(ge=0, default=0)


class TaskByStatusRead(BaseModel):
    """Число открытых задач с разбивкой по статусам."""

    todo: int = Field(ge=0, default=0)
    in_progress: int = Field(ge=0, default=0)


class TeamAssigneeLoad(BaseModel):
    """Нагрузка одного исполнителя: открытые и просроченные задачи."""

    assignee_sub: str
    open_count: int = Field(ge=0)
    overdue_count: int = Field(ge=0)
    display_name: str | None = Field(
        default=None,
        description="Отображаемое имя (full_name → email → username → sub); None только если JOIN не нашёл профиль",
    )
    avatar_url: str | None = None
    avatar_focal_x: float | None = None
    avatar_focal_y: float | None = None


class PortalHomeSearchHint(BaseModel):
    """Указание для клиента: полнотекстовый поиск выполняется отдельным запросом."""

    get_path: str = Field(
        default="/api/v1/portal/search",
        description="GET; параметр `q` обязателен, `types` — опционально (несколько значений)",
    )


class ManagerHomeBlock(BaseModel):
    """Зарезервированная панель руководителя. Бэкенд поле не заполняет (всегда ``null``)."""

    section_open_count: int = Field(description="Открытые задачи с привязкой к доступному разделу")
    section_overdue_count: int = Field(description="Из них с просроченным сроком")
    section_tasks_preview: list[PortalTaskRead]
    section_open_by_priority: TaskOpenByPriorityRead = Field(
        description="Открытые задачи по приоритету в доступных разделах",
    )
    section_done_this_month: int = Field(
        default=0,
        ge=0,
        description="Задачи в разделах, закрытые (done/cancelled) с 1-го числа текущего месяца",
    )
    section_no_assignee_count: int = Field(
        default=0,
        ge=0,
        description="Открытые задачи в разделах без назначенного исполнителя",
    )
    section_by_status: TaskByStatusRead = Field(
        default_factory=TaskByStatusRead,
        description="Открытые задачи по статусам (todo / in_progress)",
    )
    timesheet_current_month: PortalTimeEntrySummaryRead = Field(
        description="Сводка таймшитов с 1-го числа текущего месяца по сегодня (только записи пользователя)",
    )
    timesheet_weekly_buckets: list[PortalTimeEntryReportBucket] = Field(
        default_factory=list,
        description="Таймшиты по неделям (последние 4 недели)",
    )


class AdminHomeBlock(BaseModel):
    """Дашборд администратора портала: задачи команды."""

    team_open_count: int = Field(description="Открытые задачи команды (как список задач без mine_only)")
    team_overdue_count: int = Field(description="Из них с просроченным сроком")
    team_tasks_preview: list[PortalTaskRead]
    team_open_by_priority: TaskOpenByPriorityRead = Field(
        description="Открытые задачи команды по приоритету",
    )
    team_done_this_month: int = Field(
        default=0,
        ge=0,
        description="Задачи команды, закрытые (done/cancelled) с 1-го числа текущего месяца",
    )
    team_no_assignee_count: int = Field(
        default=0,
        ge=0,
        description="Открытые задачи команды без назначенного исполнителя",
    )
    team_by_status: TaskByStatusRead = Field(
        default_factory=TaskByStatusRead,
        description="Открытые задачи по статусам (todo / in_progress)",
    )
    team_assignee_load: list[TeamAssigneeLoad] = Field(
        default_factory=list,
        description="Топ исполнителей по числу открытых задач (только назначенные; до 20 строк)",
    )


class AssigneeHomeDrilldown(BaseModel):
    """Drill-down по исполнителю на главной: только задачи, без таймшитов."""

    assignee_sub: str
    display_name: str | None = None
    avatar_url: str | None = None
    avatar_focal_x: float | None = None
    avatar_focal_y: float | None = None
    open_count: int = Field(ge=0, default=0)
    overdue_count: int = Field(ge=0, default=0)
    open_tasks_preview: list[PortalTaskRead] = Field(default_factory=list)
    overdue_tasks_preview: list[PortalTaskRead] = Field(default_factory=list)
    open_by_priority: TaskOpenByPriorityRead = Field(
        default_factory=TaskOpenByPriorityRead,
        description="Открытые задачи исполнителя по приоритету",
    )


class PortalHomeRead(BaseModel):
    """Агрегат данных для главной страницы портала."""

    my_tasks_preview: list[PortalTaskRead]
    my_tasks_open_count: int
    my_tasks_overdue_count: int
    favorites_preview: list[PortalFavoriteRead]
    search: PortalHomeSearchHint = Field(default_factory=PortalHomeSearchHint)
    admin: AdminHomeBlock | None = Field(
        default=None,
        description="Только администратор портала",
    )
    manager: ManagerHomeBlock | None = Field(
        default=None,
        description="Зарезервировано: панель руководителя не реализована, всегда null",
    )
    assignee_drilldown: AssigneeHomeDrilldown | None = Field(
        default=None,
        description="При запросе с assignee_sub — сводка и превью задач исполнителя (без таймшитов)",
    )
