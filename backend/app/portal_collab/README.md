# `portal_collab` — договорённости и коллаборатив (задачи, канбан, комментарии)

> **Статус UI договорённостей:** временно заморожен (пункт меню и SPA-маршрут `/agreements` скрыты). Задачи и уведомления активны; API agreements сохранён.

## Назначение

Пакет объединяет **договорённости** (agreements) с привязкой к документам, задачам, чатам, и **задачи** портала: канбан-колонки, ссылки, файлы и комментарии, сценарии для главной страницы. **Не** дублирует REST других модулей: ссылки на документы/чат идут по ID; выборка и права согласуются с `portal_documents`, `portal_chat`, `rbac`.

**Сквозная политика** (rate limiting) — в [../MODULES.md](../MODULES.md). Проверка «менеджер или admin» — **`app.core.permissions.is_manager_or_admin`** (см. MODULES.md).

## HTTP

Роутер: [`router.py`](router.py), **без** собственного prefix на уровне `APIRouter` — вложенные `routes/*.py` используют **`/portal`**. Подготовьте путь: `/api/v1/portal/...` (см. [../api/v1/router.py](../api/v1/router.py), [../main.py](../main.py)).

HTTP-роуты подключены с **`NON_DEVELOPER_ROUTE_DEPENDENCIES`**. WS-роутеры аутентифицируются **тикетом** (тикет выдаёт HTTP-эндпоинт, уже закрытый этой зависимостью).

**OpenAPI теги:** `Задачи`, `Договорённости`, `Уведомления`, `Rich-text медиа`.

- Договорённости: `.../agreements` (list, create, get, update — **DELETE не реализован**).
- Задачи: CRUD, reorder, история, `GET .../tasks/by-number/{number}`, `POST .../tasks/{id}/rich-media`, `POST .../tasks/jira/backfill` — [`routes/tasks.py`](routes/tasks.py).
- Комментарии: CRUD + `POST .../comments/rich-media` + **WS** `POST .../comments/ws-ticket` и `WS .../comments/ws` — [`routes/task_comments.py`](routes/task_comments.py).
- Файлы: [`routes/task_files.py`](routes/task_files.py). Ссылки: [`routes/task_links.py`](routes/task_links.py) (только `http`/`https`).
- Колонки, TXT-export `GET .../task-columns/{id}/export`, Jira column sync, `GET/PUT .../me/task-board-pref` — [`routes/task_columns.py`](routes/task_columns.py).
- Доска (invalidate-only): `POST .../tasks/board/ws-ticket` + `WS .../tasks/board/ws` — [`routes/task_board_ws.py`](routes/task_board_ws.py).
- Presign rich-media: `GET .../rich-media/{id}` — [`routes/rich_media.py`](routes/rich_media.py).
- Уведомления: [`routes/notifications.py`](routes/notifications.py). Список обогащается названиями задач/документов и **`author_display_name` / `author_avatar_url`**.

### Права на вторичные операции задачи

- **Просмотр** (`get_task`): автор, исполнитель, участник связанного чата / source-сообщения, менеджер или admin.
- **Комментарии, файлы, ссылки** — то же право, что просмотр (наблюдатель чата может обсуждать).
- **Поля задачи и rich-media описания** — `user_can_edit_task` (автор, исполнитель, portal_admin).
- **Удаление задачи** — portal_admin; менеджер — только свои (`creator_sub`); автор учебной (`is_tour_demo`) задачи.

## Карта пакета

| Путь | Содержимое |
|------|------------|
| `routes/agreements.py` | list/create/get/update договорённостей |
| `routes/notifications.py` | Список/прочитано/удаление; батч-обогащение в роутере |
| `routes/tasks.py` | CRUD задач, reorder, история, rich-media описания, Jira backfill |
| `routes/task_comments.py` | Комментарии + WS треда |
| `routes/task_files.py` | Вложения задачи |
| `routes/task_links.py` | Внешние ссылки |
| `routes/task_columns.py` | Колонки, export, board-pref, Jira mapping |
| `routes/task_board_ws.py` | WS доски задач |
| `routes/rich_media.py` | GET presign изображения |
| `services/agreement.py` | Договорённости; RBAC документа/чата/задачи |
| `services/task.py` | Фасад: CRUD, списки, история, `user_can_view_task` / `user_can_edit_task` |
| `services/task_home.py` | Превью и счётчики для `/portal/home` |
| `services/task_column.py` | Колонки канбана — единый глобальный скоуп |
| `services/task_comment.py` | Комментарии к задачам |
| `services/task_file.py` | Файлы задачи (MIME + magic bytes) |
| `services/task_link.py` | Ссылки |
| `services/notification.py` | Создание уведомлений; @mention не восстанавливает менеджера по `gid_number` из `portal_user_profile` (поля нет в кэше профиля) |
| `services/task_jira_*.py` | Outbound AUTASKS |
| `schemas/*.py` | Pydantic для задач и договорённостей |
| `admin/agreements.py`, `admin/tasks.py` | SQLAdmin: договорённости, задачи |
| `admin/formatters.py` | Подформаттеры user_sub и автора |
| `admin/timesheets.py` | Таймшиты в SQLAdmin (`PortalTimeEntry` из `portal_time_entries`) |

## Зачем разнесены `task.py` / `task_home` / `task_column`

- **`task.py`** — CRUD, списки, кто чьи задачи видит.
- **`task_home.py`** — только сценарии **главной**.
- **`task_column.py`** — колонки как отдельные сущности, единый глобальный скоуп.

## Зависимости

- **`app.services.rbac`**, `app.infrastructure.db.models` (`portal_task`, `portal_agreement`, `portal_document`, `portal_chat`, …)
- **`app.portal_documents.services.portal_document`**, **`app.portal_chat.services.chat`** — в сценариях договорённостей
- **`app.portal_home`** не импортируется обратно из `task` — главная **зовёт** `task_home` и `is_manager_or_admin` (см. [../MODULES.md](../MODULES.md))

## Тесты

[`../../tests/portal_collab/`](../../tests/portal_collab/).

## См. также

- [../MODULES.md](../MODULES.md) — разбивка сервисов задач и раздел **«Механизм проверки „роль руководителя"»**.
