# `portal_documents` — документы, теги, история изменений

## Назначение

Пакет отвечает за **регламенты/документы** портала: чтение и **список** (доступ по домену, см. `app.services.rbac`), **теги**, **историю** правок, **админ-**маршруты API (`/admin/...`) для создания/редактирования/удаления (доступ — `PortalManagerOrAdminUser`; безвозвратное удаление — только `PortalAdminUser`). Эндпоинт «связанные сущности» (`.../related`) возвращает **задачи** по `document_id`; чаты к документу не привязываются, поле `chats` в ответе — пустой список.

**Сквозные правила** (rate limiting и т.п.) — [../MODULES.md](../MODULES.md). **Разбивка фасада** `portal_document` на `*_queries` / `*_mutations` / trash / duplicate; теги — [`app/services/portal_tags.py`](../services/portal_tags.py). Подробно в [../MODULES.md](../MODULES.md) (раздел *«Сервисный слой — разбивка крупных файлов»*); ниже — краткая карта **без** повторения той таблицы.

## HTTP

Два роутера: [`routes/documents_portal.py`](routes/documents_portal.py) (чтение) и [`routes/documents_admin.py`](routes/documents_admin.py) (мутации, корзина); [`routes/documents.py`](routes/documents.py) — просто реэкспорт (`admin_router`, `portal_router`) без собственной логики.

| Роутер | Префикс | OpenAPI тег | Примеры путей (после `/api/v1`) |
|--------|---------|-------------|----------------------------------|
| `portal_router` | `/portal` | `Документы` | `GET /portal/documents`, `GET /portal/documents/{id}` (теги — `GET /portal/tags` в отдельном роутере) |
| `admin_router` | `/admin` | `Администрирование` | `POST/PATCH /admin/portal-documents`, `DELETE /admin/portal-documents/{id}` (в корзину), `DELETE .../purge`, `POST .../restore`, `GET .../trash`, `PATCH .../reorder` (теги — `/portal/tags`) |

Дополнительные WebSocket-маршруты в [`routes/document_realtime.py`](routes/document_realtime.py) (входят в `portal_router`):

| Путь | Описание |
|------|---------|
| `POST /portal/navigation-tree-ws-ticket` | Одноразовый тикет для глобального WS дерева навигации |
| `WS /portal/navigation-tree-ws?ticket=...` | Broadcast-канал: событие `document_updated`; тикет только у тех, кто проходит `user_can_access_developer_docs` |
| `POST /portal/documents/{id}/content-ws-ticket` | Одноразовый тикет для WS конкретной карточки документа |
| `WS /portal/documents/{id}/content-ws?ticket=...` | Канал одной карточки: событие `document_updated` при изменении документа или его дочерних списков |

Поле **`sort_order`** задаёт порядок среди документов с одинаковым `parent_document_id`; новые документы получают порядок «выше» существующих. Soft-delete: **`deleted_at`** и метаданные удалившего; срок хранения в корзине **90 дней** (`DOCUMENT_TRASH_TTL_DAYS` в `portal_document_trash.py`). Избранное при soft-delete не снимается (список скрывает документ в корзине, restore возвращает звёзды). Просроченные корни удаляются фоновым циклом [`jobs/document_trash_nightly.py`](../jobs/document_trash_nightly.py) (`DOCUMENT_TRASH_PURGE_ENABLED`, час UTC — `DOCUMENT_TRASH_PURGE_HOUR_UTC`). Безвозвратный purge снимает строки БД, избранное и эмбеддинги поиска (`portal_embedding`).

Реэкспорт: [`router.py`](router.py). Подключение в [../api/v1/router.py](../api/v1/router.py) (два `include_router`), базовый префикс API — `/api/v1` ([`main.py`](../main.py)).

## Карта пакета

| Путь | Содержимое |
|------|------------|
| `constants.py` | UUID/title корня developer-docs и виртуальные slug секций навигации |
| `routes/documents.py` | Реэкспорт `admin_router`/`portal_router` из `documents_admin.py`/`documents_portal.py` |
| `routes/documents_portal.py` | HTTP-чтение: список, карточка, история, `.../related`, rich-media, дочерние документы |
| `routes/documents_admin.py` | HTTP-мутации: create/update/reorder/restore/duplicate/purge, корзина, quick-create |
| `routes/document_comments.py` | REST + WS комментариев к документу |
| `routes/document_realtime.py` | WebSocket-эндпоинты: глобальный канал дерева навигации + канал карточки документа; тикеты |
| `services/portal_document.py` | **Фасад**: queries + mutations + trash + reorder + duplicate + реэкспорт тегов |
| `services/portal_document_queries.py` | Read: `get_document`, фильтр не удалённых, списки с `sort_order`, поиск, история, `document_subtree_ids`, `escape` для `ILIKE` |
| `services/portal_document_mutations.py` | Create/update, `write_document_history` |
| `services/portal_document_diff.py` | Построение diff для истории изменений (create/update) |
| `services/portal_document_trash.py` | Корзина: soft-delete, restore, безвозвратный purge, список корзины, TTL |
| `services/portal_document_reorder.py` | Перестановка документа между соседями |
| `services/portal_document_duplicate.py` | Копирование документа с поддеревом (теги, ярлыки, история) |
| `services/portal_document_shortcuts.py` | Парсинг ярлыков `documentLink` из body и синхронизация `PortalDocumentShortcut` |
| `services/portal_document_realtime.py` | `publish_document_mutation`: рассылка WS-события после commit (карточка + родитель + глобальный nav-tree) |
| `services/document_comment.py` | CRUD комментариев к документу, RBAC через документ, rich-media |
| `app/services/portal_tags.py` | Теги и привязка к документу (`replace_document_tags`) |
| `schemas/document.py` | Pydantic: документ, список, история, связанные сущности |
| `schemas/document_comment.py` | Pydantic: комментарии к документу |

**SQLAdmin** для сущностей документа: классы в [`../admin/views/documents.py`](../admin/views/documents.py), регистрация в [`../main.py`](../main.py) (не в каталоге `portal_documents/`).

## Сущности и RBAC (сжато)

- Чтение одного документа — **`ensure_user_can_read_document`**: полный доступ через `rbac.user_can_access_documents`; timesheet-only (АУ/студенты) — только поддерево «Документы для разработчиков» (`user_can_access_developer_docs` + `is_document_in_developer_docs_subtree`). Константы корня — [`constants.py`](constants.py).
- Список и поиск — те же правила через `readable_document_ids_for_user` (`None` = все активные; timesheet-only — поддерево developer-docs).
- **Мутации документов** (`create`, `update`, `soft_delete`, `reorder`, `restore`, `list_trash`) — `PortalManagerOrAdminUser`; **безвозвратный purge** — только `PortalAdminUser`.
- **Комментарии** к доступному документу — чтение/запись для любого, кто проходит `AccessibleDocument` (в т.ч. timesheet-only в developer-docs).

## Уведомления о корзине (`document_trashed`)

После мягкого удаления документа (`soft_delete_document`) запускается фоновая задача **`notify_document_trashed_bg`** (`portal_collab/services/notification.py`), которая отправляет уведомление типа `document_trashed` всем администраторам портала с включённой настройкой `notify_document_trash = true`.

Настройка управляется через `GET/PATCH /api/v1/portal/account/preferences` (только администраторы могут менять своё значение `notify_document_trash`). По умолчанию для новых профилей — `true`.

## Зависимости

- **`app.services.rbac`**, **`app.infrastructure.db.models.portal_document`**
- **`app.portal_collab.services.task`** — список задач по `document_id` в `.../related`
- **`app.core.exceptions`**, **`app.schemas.auth`**
- `app.api.deps_rbac.AccessibleDocument` — зависимость роутера: документ + проверка RBAC (см. `routes/documents_portal.py`, `document_comments.py`, `document_realtime.py`)

## Тесты

[`../../tests/portal_documents/`](../../tests/portal_documents/).

## См. также

- [../MODULES.md](../MODULES.md) — дерево `app/portal_documents/`, **таблица** по файлам `portal_document_*.py` и RBAC.
- [../infrastructure/db/models/portal_document.py](../infrastructure/db/models/portal_document.py) — ORM-модели документа, тегов, истории.
