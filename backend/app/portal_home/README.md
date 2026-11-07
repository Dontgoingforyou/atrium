# `portal_home` — главная страница портала

## Назначение

Агрегирующий пакет: собирает данные для **главной страницы** из нескольких доменов (задачи, избранное) и возвращает единый ответ. Не хранит собственных таблиц — только логика сборки и сервисные вызовы к соседним модулям.

**Ролевые блоки:**
- `admin` (поле `PortalHomeRead`) — только для `is_portal_admin`: дашборд задач команды; сводки таймшитов и список студентов — вне главной (`/analytics/timesheets`, `/specialists`, `GET /portal/users/specialists`).
- `manager` — зарезервировано: API всегда отдаёт `null`, `_build_manager_block` нет.
- Запросы к БД на одной `AsyncSession` — **последовательно** (не `asyncio.gather`). Для админа с drill-down — много COUNT; сжимать SQL в `task_home` — отдельный рефакторинг.

**Сквозная политика** — [../MODULES.md](../MODULES.md). Разграничение ролей «admin vs manager» подробно — там же, в разделе **«Два механизма проверки „роль руководителя"»**.

---

## HTTP-эндпоинты

Роутер: [`router.py`](router.py) → [`routes/home.py`](routes/home.py); префикс **`/portal`**.  
База API: `/api/v1/portal/...` (см. [../api/v1/router.py](../api/v1/router.py), [../main.py](../main.py)).

**OpenAPI тег:** `Главная`

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/portal/home` | Данные для главной страницы: превью задач, избранное, поисковая подсказка; опционально блок `admin`. Поле `manager` всегда `null` |

---

## Карта пакета

| Путь | Содержимое |
|------|------------|
| `routes/home.py` | Единственный эндпоинт `GET /portal/home`; делегирует в сервис |
| `services/home.py` | `build_portal_home` — оркестрирует вызовы к `task_home_svc`, `favorite_svc`; превью задач через `tasks_to_reads`. Разбит на приватные `_build_admin_block` и `_build_assignee_drilldown`. Возврат Pydantic-агрегата напрямую — задокументированное исключение из «сервис возвращает ORM» (services.mdc), см. docstring |
| `schemas/home.py` | Pydantic DTO: `PortalHomeRead`, `AdminHomeBlock`, `ManagerHomeBlock`, `PortalHomeSearchHint`, вспомогательные |

---

## Константы

Определены в `services/home.py` во избежание магических чисел:

| Константа | Значение | Назначение |
|-----------|---------|------------|
| `HOME_TASKS_PREVIEW_LIMIT` | 8 | Число задач в превью «Мои задачи» |
| `HOME_FAVORITES_PREVIEW_LIMIT` | 8 | Число избранных объектов на главной |
| `HOME_ADMIN_TEAM_TASKS_PREVIEW_LIMIT` | 8 | Число задач команды в блоке админа |
| `HOME_ASSIGNEE_PREVIEW_LIMIT` | 8 | Число задач в превью drill-down по исполнителю |

---

## Зависимости

- **`app.portal_collab.services.task_home`** — превью и счётчики задач (мои / команды); `get_assignee_display_info` — display_name/avatar исполнителя для drill-down (независимо от admin-агрегата `team_assignee_load`, доступен и менеджеру)
- **`app.portal_favorites.services.favorite`** — список избранного
- **`app.portal_collab.services.task.tasks_to_reads`** — тот же маппер `PortalTaskRead` / `assignee_subs`, что у `/portal/tasks`
- **`app.schemas.auth.UserPublic`** — данные текущего пользователя и флаги ролей (`is_portal_admin`)

`time_entry_svc` на главную не подключён (блок `manager` не реализован).

Обратных импортов из перечисленных модулей в `portal_home` нет (однонаправленная зависимость).

---

## Тесты

[`../../tests/portal_home/`](../../tests/portal_home/).

---

## См. также

- [../MODULES.md](../MODULES.md) — индекс модулей, список пакетов, сервисный граф.
- [../portal_collab/README.md](../portal_collab/README.md) — `task_home.py` и разделение `task.py` / `task_home.py`.
- [../api/v1/routes/portal_users.py](../api/v1/routes/portal_users.py) — `GET /portal/users/specialists` (список студентов для раздела «Специалисты»).
