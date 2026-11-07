# `portal_navigation` — навигация и дерево документов

## Назначение

Пакет отвечает за **левое меню** портала: возвращает иерархическое дерево документов для навигации. Дерево строится из таблицы `portal_document` по полю `parent_document_id` — без отдельной таблицы узлов.

Скрытые (soft-deleted) документы исключаются автоматически (`deleted_at IS NULL`). Сортировка — по `sort_order`, затем по `created_at DESC`, затем по `id`. Нарезка секций считает поддерево developer-docs с `include_deleted=True`: корзина контейнера не выталкивает живых детей в «Документы».

Потолок выборки — `_MAX_NAV_TREE_DOCS` (2000) в SQL. При упирании в кап пишется `warning`; лишние страницы не попадают в меню, дети отброшенных родителей могут стать корнями. Это capped snapshot, не пагинированный list.

Сид [`app/data/portal_navigation_seed.py`](../data/portal_navigation_seed.py) кормит только историческую миграцию `0003_portal_nav_tree` — **не** текущее меню.

**Сквозная политика** — [../MODULES.md](../MODULES.md).

---

## HTTP-эндпоинты

Роутер: [`router.py`](router.py) → [`routes/navigation.py`](routes/navigation.py); префикс **`/portal`**.  
База API: `/api/v1/portal/...` (см. [../api/v1/router.py](../api/v1/router.py), [../main.py](../main.py)).

**OpenAPI тег:** `Навигация`

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/portal/navigation-tree` | Дерево документов для левого меню (`list[PortalNavNodeTree]`) |

RBAC: полный доступ — две виртуальные секции; timesheet-only — только «Документы для разработчиков» (`rbac.user_can_access_developer_docs`).

**Realtime-обновление дерева** — отдельный WS-канал, реализован **не в этом пакете**, а в
[`portal_documents/routes/document_realtime.py`](../portal_documents/routes/document_realtime.py)
(тикет `POST /portal/navigation-tree-ws-ticket`, канал `WS /portal/navigation-tree-ws`, событие
`document_updated` для всех авторизованных пользователей). Причина: рассылка триггерится
мутациями документов, которые и так живут в `portal_documents` — см.
[`portal_documents/README.md`](../portal_documents/README.md).

---

## Структура ответа

Два виртуальных корня (не строки `portal_document`):

| Slug | Название | Содержимое |
|------|----------|------------|
| `__documents__` | Документы | корни вне поддерева developer-docs |
| `__developer_docs__` | Документы для разработчиков | прямые дети контейнера `DEVELOPER_DOCS_ROOT_ID` |

Константы — [`portal_documents/constants.py`](../portal_documents/constants.py).  
Каждый узел секции: `id`, `slug`, `title`, `sort_order`, `document_count_subtree` (число **корней секции**, не всех потомков), `documents`, `children` (всегда пусто).

У документа в `documents`: `id`, `title`, `icon_emoji`, `children` (вложенные страницы), `shortcuts` (ярлыки `documentLink` без смены `parent_document_id`). Для полного доступа ярлык может указывать на документ другой секции; timesheet-only видит только цели внутри developer-docs.

---

## Карта пакета

| Путь | Содержимое |
|------|------------|
| `routes/navigation.py` | `GET /portal/navigation-tree`; делегирует в сервис |
| `services/navigation.py` | `get_navigation_tree` — две секции, сборка из `PortalDocument` |
| `schemas/navigation.py` | Pydantic DTO: `PortalNavNodeTree`, `NavDocumentBrief` |

---

## Зависимости

- **`app.infrastructure.db.models.portal_document.PortalDocument`**, **`PortalDocumentShortcut`**
- **`app.portal_documents.constants`**, **`document_subtree_ids`**
- **`app.services.rbac`**, **`app.schemas.auth.UserPublic`**

---

## Тесты

[`../../tests/portal_navigation/`](../../tests/portal_navigation/).

---

## См. также

- [../MODULES.md](../MODULES.md) — индекс модулей.
- [../portal_documents/README.md](../portal_documents/README.md) — модель `PortalDocument`, RBAC developer-docs.
