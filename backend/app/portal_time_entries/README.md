# `portal_time_entries` — таймшиты (учёт времени)

## Назначение

Пакет реализует **учёт потраченного времени**: создание, редактирование, **удаление** записей таймшита, а также сводные и периодические отчёты. Формат строки: `дата | задача (текст) | минуты | описание`.

**RBAC** (`services/_time_entry_reports.py`: `ensure_timesheets_access`, `effective_user_sub_filter`; политика — `app.core.permissions.is_manager_or_admin`/`is_timesheet_only`, **не** копируется в модуле):

| Роль | Условие | Доступ |
|------|---------|--------|
| Разработчик / «только ТШ» | Keycloak-группа `students` **или** должность SSO (claim `position`) из `TIMESHEET_ONLY_POSITIONS` (`student`, `au_specialist`) | Только свои записи: создание, просмотр, редактирование, удаление |
| Менеджер | Основной отдел SSO «Аутстафф» (`gid_number=10000`), **и должность не входит** в `TIMESHEET_ONLY_POSITIONS` | Свои записи + просмотр чужих (фильтр `user_sub`); сводка часов по специалистам за месяц — `GET /portal/time-entries/specialists` |
| Администратор портала | `is_portal_admin` (роль `cosmolet_role_admin`) | Полный доступ: все записи, фильтр `user_sub`, удаление чужих записей |

Пользователи **без** одной из трёх ролей получают **403** при любом обращении к таймшитам.

**Важный нюанс:** должность SSO (`position`) приоритетнее отдела. Пользователь отдела Аутстафф с должностью `au_specialist`/`student` **не** получает менеджерские права (см. `is_manager_or_admin`/`is_timesheet_only` в `app/core/permissions.py`) — работает как обычный «только ТШ»-пользователь, видит и правит только свои записи. Группа Keycloak `outstaff` без `gid_number=10000` менеджера не даёт.

**Редактирование/удаление чужих записей:** доступно только администратору портала — менеджер видит чужие записи через фильтр `user_sub`, но не может их изменить или удалить (`PATCH`/`DELETE` вернут 403 не-владельцу, если он не admin).

**Привязка `task_id`:** всегда проверяется `user_can_view_task` (как вторичная операция). Менеджер/admin видят все задачи; разработчик и «только ТШ» — только доступные им. Существования UUID недостаточно.

**Удаление:** `DELETE /time-entries/{id}` безвозвратно удаляет строку из БД (доступ: владелец или администратор портала).

---

## HTTP-эндпоинты

Роутер: [`router.py`](router.py) → [`routes/time_entries.py`](routes/time_entries.py); префикс **`/portal`**.
База API: `/api/v1/portal/...` (см. [../api/v1/router.py](../api/v1/router.py), [../main.py](../main.py)).

**OpenAPI тег:** `Таймшиты`

| Метод | Путь | Назначение | Доступ |
|-------|------|------------|--------|
| GET | `/portal/time-entries/export` | Выгрузка записей за месяц в CSV/XLSX/PDF (`format=`, `month=`) — без пагинации, cap 5000 строк | students/outstaff/admin |
| GET | `/portal/time-entries/summary` | Сводка (сумма минут и число записей) за период | students/outstaff/admin |
| GET | `/portal/time-entries/report` | Периодический отчёт по неделям/месяцам (полная выборка дат/минут, без лимита 500) | students/outstaff/admin |
| GET | `/portal/time-entries/specialists` | Сводка часов по всем исполнителям за месяц (`month=YYYY-MM`) | outstaff/admin |
| GET | `/portal/time-entries` | Список записей с фильтрами, пагинация (`limit` до 500 — таблица месяца) | students/outstaff/admin |
| POST | `/portal/time-entries` | Создать запись таймшита | students/outstaff/admin |
| POST | `/portal/time-entries/bulk` | Массовое создание повторяющихся записей (диапазон дат + дни недели, лимит 200 за раз) | students/outstaff/admin |
| POST | `/portal/time-entries/import-jira-csv` | Импорт из CSV-выгрузки Jira Tempo worklog (лимит 1000 строк, до 5 МБ) — от имени текущего пользователя. Повтор той же выгрузки создаёт дубликаты | students/outstaff/admin |
| PATCH | `/portal/time-entries/{entry_id}` | Обновить запись (только свою, либо любую — администратор портала) | students/outstaff/admin |
| DELETE | `/portal/time-entries/{entry_id}` | Удалить запись безвозвратно (только свою, либо любую — администратор портала) | students/outstaff/admin |

**Query-параметры списков:**
- `month=YYYY-MM` — удобный выбор месяца (заменяет `date_from`/`date_to`)

---

## Карта пакета

| Путь | Содержимое |
|------|------------|
| `routes/time_entries.py` | REST-эндпоинты: CRUD + bulk-создание + import-jira-csv + export + summary + report + specialists |
| `services/time_entry.py` | CRUD-часть (`create_time_entry`, `create_time_entries_bulk`, `list_time_entries`, `summarize_time_entries`, `update_time_entry`, `delete_time_entry`); реэкспортирует публичные функции остальных `services/_*.py` |
| `services/_time_entry_reports.py` | Общие хелперы ролей/фильтрации (`ensure_timesheets_access`, `effective_user_sub_filter`, `list_where_criteria`, `user_is_developer`, `month_date_range`) + отчёты (`get_time_entries_report` — полная агрегация по неделям/месяцам, `list_specialists_monthly_summary` — агрегат `GET /portal/time-entries/specialists`) |
| `services/_jira_csv_import.py` | Разбор и импорт CSV-выгрузки Jira Tempo worklog (`parse_jira_worklog_csv` — чистая функция без БД, `import_jira_worklog_csv`) |
| `services/_export.py` | Выгрузка записей за месяц в CSV/XLSX/PDF (`export_specialist_time_entries`; синхронные генераторы `_to_csv`/`_to_xlsx`/`_to_pdf` выполняются через `run_in_executor`) |
| `schemas/time_entry.py` | Pydantic DTO: `PortalTimeEntryCreate`, `PortalTimeEntryBulkCreate`, `PortalTimeEntryUpdate`, `PortalTimeEntryRead`, `PortalTimeEntrySummaryRead`, `PortalTimeEntryReportBucket`, `PortalTimeEntryImportResult`/`PortalTimeEntryImportRowError`, `PortalSpecialistMonthlySummary` |

---

## Зависимости

- **`app.infrastructure.db.models`** — модели `PortalTimeEntry`, `PortalUserProfile`
- **`app.core.permissions`** — `is_manager_or_admin`, `is_timesheet_only` (единый источник RBAC-политики — не копировать в модуле, см. **dry.mdc**)
- **`app.core.auth_constants`** — `IDP_GROUP_DEVELOPER`, `TIMESHEET_ONLY_POSITIONS` (должности SSO `student`/`au_specialist`)
- **`app.schemas.auth.UserPublic`** — флаги ролей (`is_portal_admin`, `idp_groups`, `position`)
- **`app.schemas.pagination.PagedResponse`** — постраничный ответ для списка записей и агрегата по специалистам (`/time-entries`, `/time-entries/specialists`)
- **`app.portal_collab.services.task`** (`user_can_view_task`) — проверка доступа к задаче при привязке `task_id` (защита от IDOR при вторичной операции)
- **`openpyxl`**, **`reportlab`** — генерация XLSX/PDF в `services/_export.py` (шрифт DejaVuSans для кириллицы в PDF — путь ищется среди системных, при отсутствии — Helvetica без кириллицы)
- Список **студентов** для раздела «Специалисты» (`GET /portal/users/specialists`) — в [`api/v1/routes/portal_users.py`](../api/v1/routes/portal_users.py), сервис [`services/portal_user.py`](../services/portal_user.py)
- Вызывается из **SQLAdmin** `portal_collab/admin/timesheets.py` для вьюхи в панели администратора

---

## Тесты

[`../../tests/portal_time_entries/`](../../tests/portal_time_entries/)

Покрытые сценарии: CRUD, RBAC (включая должности SSO `student`/`au_specialist`), удаление, фильтр `month`, `GET /portal/time-entries/specialists`, массовое создание (`test_time_entry_bulk_create.py`), импорт CSV Jira — разбор и API (`test_jira_csv_import_parsing.py`, `test_jira_csv_import_api.py`), экспорт CSV/XLSX/PDF (`test_time_entries_export.py`).

---

## См. также

- [../MODULES.md](../MODULES.md) — индекс модулей
- [../portal_collab/README.md](../portal_collab/README.md) — SQLAdmin вьюха таймшитов (`admin/timesheets.py`)
- [../portal_home/README.md](../portal_home/README.md) — агрегат главной (поле `manager` зарезервировано, таймшиты на главную не подключены)
