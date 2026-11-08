# Доменные модули в `app/`

Крупные области продукта выносятся в подпакеты `app/<домен>/`, чтобы сузить связность и упростить навигацию по коду.

## Текущие модули

| Пакет | Содержимое |
|-------|------------|
| **`portal_chat`** | Чаты, сообщения, Web Push (`routes/messages.py`, `routes/push.py`). Структура: `routes/chats.py`, `routes/inbox.py`, `services/chat.py`. WS-тикеты — `infrastructure/ws/tickets.py`. |
| **`portal_collab`** | Договорённости, задачи; SQLAdmin-вьюхи в `admin/`. **UI договорённостей временно заморожен** (меню/роуты скрыты; API сохранён). |
| **`portal_finance`** | Контрагенты, договоры, счета/акты, платежи, закупочные заявки; SQLAdmin-вьюхи в `admin/`. **UI временно заморожен**. |
| **`portal_documents`** | Документы с тегами, история изменений. |
| **`portal_navigation`** | Дерево навигации над `portal_document` (без своей таблицы/CRUD/admin-вьюхи). |
| **`portal_search`** | Глобальный поиск (document/chat_message/task/specialist/`calendar_event` + RBAC). |
| **`portal_favorites`** | Избранное по документам (`navigation_node` в API не поддерживается). |
| **`portal_home`** | Главная страница (задачи, избранное; блок `manager` в API зарезервирован, пока `null`). |
| **`portal_time_entries`** | Таймшиты (CRUD + summary + отчёты). |
| **`portal_bench`** | Дашборд отчётов и бенч (снимок воронки АУ, sync Google Таблицы, выгрузка). Только `portal_admin`. |
| **`portal_learning`** | Обучение — материалы, чек-листы, квизы. **UI временно заморожен**. |
| **`portal_specialists`** | Раздел «Мои специалисты»: Kanban-воронка, профиль/ссылки специалиста, интеграция Jira (см. [`integrations/README.md`](integrations/README.md)). |
| **`integrations`** | Внешние системы: Jira (read + webhook BASE, `write_client` для outbound TASKS), сервис профилей (фото), Google Sheets (дашборд воронки) и выгрузка документа «Бенч» для RAG (`GET /integrations/bench`). Доменная логика — в `portal_specialists` / `portal_collab` / `portal_user_*` / `portal_bench` / `portal_documents`. |
| **`portal_telegram`** | Привязка Telegram к аккаунту портала, доставка уведомлений и событий инбокса чатов в бот. |
| **`portal_calendar`** | Календарь: события, RRULE, участники, peer-view + cross-create, legacy invite/share-token, напоминания (in-app / Telegram / email). |
| **`portal_mcp`** | HTTP MCP `/api/v1/mcp` для админа и менеджера. Тулы зовут публичные фасады доменов, права не копируют. |

**Расширенные README** (карта пакета, зона ответственности сервисов; сквозные политики — **в этом файле** выше и ниже): [portal_finance](portal_finance/README.md) · [portal_collab](portal_collab/README.md) · [portal_documents](portal_documents/README.md) · [portal_favorites](portal_favorites/README.md) · [portal_learning](portal_learning/README.md) · [portal_chat](portal_chat/README.md) · [portal_search](portal_search/README.md) · [portal_telegram](portal_telegram/README.md) · [portal_specialists](portal_specialists/README.md) · [portal_navigation](portal_navigation/README.md) · [portal_home](portal_home/README.md) · [portal_time_entries](portal_time_entries/README.md) · [portal_calendar](portal_calendar/README.md) · [integrations](integrations/README.md)

## Политика доступа: документы, договоры, счета, обучение

Легаси-концепция «узлов навигации» (`portal_nav_node`, `nav_node_id`, RBAC по IdP-группам на узел) **полностью удалена** (модели и колонки). `app.services.rbac` содержит только живые функции `user_can_access_documents` / `user_can_access_developer_docs`. Левое меню — виртуальное дерево над `portal_document` (см. `portal_navigation`), без отдельной таблицы узлов и без ACL по дереву.

Документы, договоры, счета и учебные материалы **глобально видимы на чтение** всем авторизованным пользователям портала (с учётом отдельных deny-правил по IdP, например отсутствие доступа к документам у группы students — см. `user_can_access_documents` / `user_can_access_developer_docs` в `app.services.rbac`). Политика видимости по доменам (чаты, задачи, договорённости и т.д.) остаётся на соответствующих сервисах и отдельных проверках по ролям, **не** на автоматической «решётке» по дереву меню. **Административная ответственность:** не размещать в этих доменах сведения, которые должны быть скрыты от части авторизованных пользователей средствами портала — изоляция по разделам не реализована.

**Чаты:** `list_chats` и поиск — только членство. `portal_admin` без членства может **читать** чужой чат по UUID (история, галерея, download, pinned, readers/reactors, WS-слушатель). Мутации (сообщения, pin, реакции, upload, transcribe, состав, удаление чата, ephemeral WS) — только участник.

### Ограничение частоты запросов (rate limiting)

В приложении: `AuthRateLimitMiddleware` и `ApiRateLimitMiddleware` ([`middleware/rate_limit.py`](middleware/rate_limit.py)) — auth/beacon по IP, mutating `/api/v1/*` и `GET /portal/search/semantic` (per-token + потолок per-IP, чтобы уникальный Bearer не обходил лимит), `GET /health` и `GET /integrations/bench` по IP. Пороги — `Settings`. При недоступном Redis — in-memory fallback в процессе (с потолком числа ключей). Дополнительно рекомендуется ingress / WAF. Полнотекст `GET /portal/search` и прочие GET без явного правила — на периметре.

## Политика удаления данных (сквозная)

| Домен | Пользовательское «удалить» | БД | MinIO | `portal_embedding` | Автоочистка |
|-------|---------------------------|-----|-------|-------------------|-------------|
| Документы | soft → корзина 90 дней → purge | hard после TTL/purge | — | снимается при soft/purge | nightly `document_trash_nightly` |
| Чат: сообщение | «у всех» / «у меня» | soft / hidden | MinIO при «у всех» | при «у всех» | — |
| Чат: весь чат | DELETE чата | CASCADE | да | batch по сообщениям | — |
| Чат: orphan-вложения | — | hard | да | — | nightly `chat_orphan_attachments_nightly` |
| Задачи, комментарии, теги, обучение, … | hard | CASCADE | по домену | где индексируется | — |
| Специалисты (purge) | hard (только admin, студент без чатов) | CASCADE профиль/доска/заметки/ссылки; `portal_telegram_binding` того же `user_sub` | — | `specialist` + `specialist_note` | — |
| Telegram-привязка | DELETE `/telegram/bind`, `/unlink` в боте, блок бота | hard `portal_telegram_binding` | — | — | вместе с purge специалиста |
| Финансы / договорённости | soft cancelled | строка остаётся | — | — | вне активной разработки |

Подробности по чату и документам — README соответствующих пакетов. Аудит осиротевших записей: [`tests/audit/test_orphan_data_audit.py`](../tests/audit/test_orphan_data_audit.py).

## `portal_navigation`

Структура:
```
app/portal_navigation/
  router.py              # portal_router (/portal)
  routes/
    navigation.py        # GET /portal/navigation-tree
  services/navigation.py # get_navigation_tree (дерево документов по parent_document_id)
  schemas/navigation.py  # PortalNavNodeTree, NavDocumentBrief
```

Своей ORM-модели/таблицы нет: дерево — виртуальное, строится из `PortalDocument` (`parent_document_id`), без отдельного CRUD узлов и без SQLAdmin-вьюхи. Подробнее — [`portal_navigation/README.md`](portal_navigation/README.md).

## `portal_documents`

Структура:
```
app/portal_documents/
  router.py              # два роутера: portal_router (/portal) + admin_router (/admin)
  constants.py            # UUID/title корня developer-docs, виртуальные slug секций навигации
  routes/
    documents.py          # реэкспорт admin_router/portal_router из documents_admin.py/documents_portal.py
    documents_portal.py   # чтение: список, карточка, история, .../related, rich-media, дочерние документы
    documents_admin.py    # мутации: create/update/reorder/restore/duplicate/purge, корзина, quick-create
    document_comments.py  # REST + WS комментариев к документу
    document_realtime.py  # WebSocket: глобальный nav-tree-ws (broadcast) + content-ws на карточку; тикеты
  services/
    portal_document.py           # фасад: queries + mutations + trash + reorder + duplicate
    portal_document_queries.py   # get_document, списки (sort_order, без удалённых), search, readable_document_ids_for_user, history, document_subtree_ids
    portal_document_mutations.py # create/update + write_document_history
    portal_document_diff.py      # построение diff для истории изменений
    portal_document_trash.py     # soft-delete, restore, purge (+ эмбеддинги), TTL 90 дней, nightly job
    portal_document_duplicate.py # копирование поддерева (теги, ярлыки, история)
    portal_document_reorder.py   # порядок среди сиблингов
    portal_document_shortcuts.py # ярлыки documentLink: парсинг body + синхронизация PortalDocumentShortcut
    portal_document_realtime.py  # publish_document_mutation: рассылка после commit (карточка + родитель + nav-tree broadcast)
    document_comment.py          # CRUD комментариев к документу
  schemas/
    document.py            # PortalDocumentCreate/Update/Read/ListItem; теги — `schemas/tags.py`
    document_comment.py    # DocumentCommentCreate/Update/Read
```

ORM-модели: [`infrastructure/db/models/portal_document.py`](infrastructure/db/models/portal_document.py)

## `portal_search`

Подробнее: [`portal_search/README.md`](portal_search/README.md).

Структура:
```
app/portal_search/
  router.py
  routes/search.py            # GET /portal/search, GET /portal/search/semantic, POST /portal/admin/search/reindex
  services/search_orchestrator.py  # оркестрация fulltext/semantic из роутера
  services/search.py          # merge_cap, merge_and_slice, semantic_search (pgvector)
  services/_search_format.py  # форматирование hit'ов
  services/search_filters.py  # пост-фильтры: document_ids_for_tag_slugs, specialist_subs_for_status_ids
  services/embedding.py       # OpenAI embeddings, upsert/delete, bulk reindex (реэкспорт публичного API пакета)
  services/_embedding_generate.py
  services/_embedding_chunk.py  # чанки SELECT + zip(..., strict=True) для bulk upsert
  services/_embedding_bulk_reindex.py
  services/_embedding_specialists.py
  services/_embedding_background.py
  services/_embedding_sql.py  # общий UPSERT_EMBEDDING_SQL / vec_literal — не дублировать по файлам
  services/entity_text.py
  schemas/search.py           # PortalSearchHit*, семантические ответы
```

Допустимые значения `?types=` для **полнотекста** (GET /portal/search): `document`, `chat_message`, `task`, `specialist`, `calendar_event` — `PORTAL_SEARCH_ENTITY_TYPES`. Тип `agreement` **не** в полнотекстовом API (422). **Семантика** (`GET /portal/search/semantic`): дефолт без `?types=` — `PORTAL_SEMANTIC_DEFAULT_TYPES` (как SPA, без `agreement`); явный `types=agreement` валиден. Полный набор API: `document`, `chat_message`, `task`, `learning_material`, `specialist`, `specialist_note`, `calendar_event`, `agreement` (`PORTAL_SEMANTIC_ENTITY_TYPES`). Фильтр `status_ids` — для specialist/specialist_note. Reindex без `entity_types` берёт все типы из `PORTAL_SEMANTIC_ENTITY_TYPES`.

## `portal_specialists`

Подробнее: [`portal_specialists/README.md`](portal_specialists/README.md).

Структура:
```
app/portal_specialists/
  router.py
  constants.py                 # лимит тела заметки (= embedding), SQL safety cap списков
  routes/
    board.py                   # колонки, доска, legacy statuses, reassign
    jira.py                    # search/link/sync/unlink, sync-from-jira
    specialist_detail.py       # профиль, ссылки, заметки, purge
    specialist_board_pref.py   # GET/PUT /me/specialist-board-pref
    specialist_board_ws.py     # тикет + WS доски (keepalive)
  services/
    board.py                   # фасад доски
    board_shared.py            # require_manager_or_admin, require_specialist_write_access
    board_entries.py           # записи, directory, reassign
    board_columns_statuses.py  # колонки; CRUD legacy-статусов
    specialist_detail.py       # карточка
    jira_import.py             # import, webhook, unlink
    jira_import_board.py       # колонка доски и ссылки последнего import
    jira_board_sync.py         # колонки из Jira
    specialist_board_pref.py
    search.py                  # fulltext specialists для portal_search
  schemas/
    board.py, jira.py, specialist_detail.py
  admin/
    board.py, profile.py
```

ORM: `portal_specialist_column`, `portal_manager_specialist`, `portal_specialist_profile`, `portal_specialist_link`, `portal_specialist_note`, `portal_specialist_status` (legacy), `portal_user_specialist_board_pref`.

**OpenAPI теги:** `Специалисты — доска`, `Специалисты — карточка`, `Специалисты — Jira`.

HTTP: `/api/v1/portal/specialists/...`. GET профиля/Jira — без INSERT. Мутации карточки — `require_specialist_write_access`. Jira webhook — `integrations/jira/routes.py`.

## API аккаунта (`/portal/account`)

Маршрут: [`api/v1/routes/portal_account.py`](api/v1/routes/portal_account.py). Схемы: [`schemas/portal_account.py`](schemas/portal_account.py).

| Метод | Путь | Доступ | Описание |
|-------|------|--------|----------|
| GET | `/portal/account/preferences` | Любой авторизованный | Получить настройки уведомлений текущего пользователя |
| PATCH | `/portal/account/preferences` | Любой авторизованный; поле `notify_document_trash` — только admin | Обновить настройки уведомлений |

Поле `notify_document_trash` управляет получением уведомлений типа `document_trashed` при мягком удалении документов. Изменить его может только администратор портала. `guided_tour_completed` может менять любой пользователь.

## Общие схемы (`app/schemas/`)

Кросс-доменные Pydantic-схемы, не привязанные к одному пакету `portal_*/` (в отличие от доменных `schemas/` внутри `portal_X/`, см. «Соглашение для новых модулей» ниже):

| Файл | Содержимое |
|------|------------|
| [`auth.py`](schemas/auth.py) | `PasswordLoginRequest`, `TokenExchangeRequest`, `RefreshTokenRequest/Response`, `UserPublic`, `TokenResponse`, `LogoutBeaconRequest` — контракты `/auth/*` |
| [`pagination.py`](schemas/pagination.py) | `PagedResponse[T]` — стандартная обёртка списков с пагинацией |
| [`portal_account.py`](schemas/portal_account.py) | `PortalAccountPreferencesRead/Update` — настройки аккаунта (см. «API аккаунта» выше) |
| [`portal_user.py`](schemas/portal_user.py) | `PortalUserRead`, `PortalUserPresenceRead` (используют `PresenceState` из `app.core.enums`), `PortalPresenceUpdate`, `PresenceBeaconBody`, `AvatarUploadRead` |
| [`rich_media.py`](schemas/rich_media.py) | `RichMediaRead` — изображения rich-text (задачи/документы), см. `app/services/rich_media.py` |
| [`tags.py`](schemas/tags.py) | `PortalTagRead/Create/Update` — единый источник для тегов документов и задач, см. `app/services/portal_tags.py` |

## Shared-сервисы (`app/services/`) и кэш

Кросс-доменный слой; доменная логика — в `app/portal_*/`. Детали —

| Тема | Где | Замечание |
|------|-----|-----------|
| Кэш SSO userinfo | [`infrastructure/cache/token_cache.py`](infrastructure/cache/token_cache.py) | TTL 5 мин, без JWKS: смена групп в IdP действует с задержкой до истечения TTL (осознанная модель, не баг) |
| Rich-media upload | [`services/rich_media_upload.py`](services/rich_media_upload.py) | стрим в MinIO (`async_upload_stream_to_key`); лимит размера — `attachment_max_size_bytes`, не снижать «на будущее» |
| Аватары в списках | [`services/user_photo_meta_cache.py`](services/user_photo_meta_cache.py) | `get_cached_photo_meta_bulk` (Redis pipeline), не N+1 `GET` |
| SQLAdmin | [`admin/auth.py`](admin/auth.py) | на каждый запрос сверка `portal_user_profile.is_portal_admin`; снятие роли в IdP закрывает `/admin` до logout (после обновления кэша профиля) |
| Whisper | [`portal_chat/services/transcription.py`](portal_chat/services/transcription.py) | тот же `OPENAI_API_KEY` / `OPENAI_BASE_URL`, что у эмбеддингов; таймаут — `Settings.openai_whisper_timeout_seconds` |

## `portal_favorites`

Структура:
```
app/portal_favorites/
  router.py
  routes/favorites.py    # GET/POST/DELETE /portal/favorites
  services/favorite.py   # add_favorite (ensure_user_can_read_document), remove_favorite, remove_favorites_for_documents (purge/TTL), list_favorites (живые документы; роутер за NON_DEVELOPER)
  schemas/favorite.py    # PortalFavoriteCreate, PortalFavoriteRead
```

ORM-модель: [`infrastructure/db/models/portal_favorite.py`](infrastructure/db/models/portal_favorite.py) · README: [`portal_favorites/README.md`](portal_favorites/README.md)

## `portal_home`

Структура:
```
app/portal_home/
  router.py
  routes/home.py         # GET /portal/home
  services/home.py       # build_portal_home (агрегат: задачи, избранное, admin;
                          # manager зарезервирован, всегда null) —
                          # приватные _build_admin_block, _build_assignee_drilldown
  schemas/home.py        # PortalHomeRead, AdminHomeBlock, ManagerHomeBlock, PortalHomeSearchHint
```

## `portal_time_entries`

Структура:
```
app/portal_time_entries/
  router.py
  routes/time_entries.py           # CRUD + bulk + import-jira-csv + export + summary + report + specialists
  services/time_entry.py           # create/update/delete/list + summarize (реэкспортирует публичные функции _*.py)
  services/_time_entry_reports.py  # ensure_timesheets_access, effective_user_sub_filter, list_where_criteria,
                                    # get_time_entries_report, list_specialists_monthly_summary, month_date_range
  services/_jira_csv_import.py     # parse_jira_worklog_csv (чистая функция), import_jira_worklog_csv
  services/_export.py              # export_specialist_time_entries (CSV/XLSX/PDF, run_in_executor)
  schemas/time_entry.py            # PortalTimeEntryCreate/Update/Read + Bulk + Import + Summary + ReportBucket
```

ORM-модель: [`infrastructure/db/models/portal_time_entry.py`](infrastructure/db/models/portal_time_entry.py) · README: [portal_time_entries/README.md](portal_time_entries/README.md)

## `portal_finance`

Структура:
```
app/portal_finance/
  router.py              # include_router → api/v1/router.py (prefix /portal/finance)
  admin/                 # SQLAdmin-вьюхи (counterparty, contract, invoice, payment, procurement)
  routes/
    counterparties.py    # GET /counterparties, POST /counterparties, PATCH /{id}
    contracts.py         # CRUD + soft-delete
    invoices.py          # CRUD
    payments.py          # list/create/delete + GET /summary
    procurement.py       # закупочные заявки
  services/
    counterparty.py      # is_portal_admin-guard для записи
    contract.py          # глобально видим всем авторизованным (см. MODULES.md выше)
    invoice.py           # глобально видим всем авторизованным (см. MODULES.md выше)
    payment.py           # RBAC через видимые счета; GET /summary
  schemas/
    counterparty.py
    contract.py
    invoice.py
    payment.py           # + FinanceSummaryRead
```

ORM-модели: [`portal_finance.py`](infrastructure/db/models/portal_finance.py)

## Соглашение для новых модулей

- **`routes/`** — `APIRouter` с теми же префиксами, что ожидает клиент (`/portal/...` и т.д.).
- **`services/`** — бизнес-логика и доступ к данным через SQLAlchemy-сессию.
- **`schemas/`** — Pydantic-модели запросов/ответов API этого домена.
- Опционально: **`admin/`** (классы SQLAdmin для сущностей домена).
- **ORM-модели** по умолчанию остаются в `app/infrastructure/db/models/` и регистрируются в `app/infrastructure/db/models/__init__.py` для Alembic (`alembic/env.py` импортирует этот пакет).

Подключение HTTP: один агрегирующий `router.py` в пакете домена и `include_router` в [`app/api/v1/router.py`](api/v1/router.py).

Регистрация SQLAdmin: импорт классов из доменного модуля в [`app/main.py`](main.py).

Вся логика доступа к данным (SELECT/INSERT/UPDATE) остаётся в сервисах — `app/services/` и `<domain>/services/`. При необходимости выделять крупные сервисы в файлы `_queries.py` / `_mutations.py` рядом с сервисом ().

## Сервисный слой — разбивка крупных файлов

### `portal_documents/services/` и общий [`portal_tags.py`](services/portal_tags.py)

| Файл | Содержимое |
|------|------------|
| [`portal_tags.py`](services/portal_tags.py) | Теги: `list_tags`, `create_tag`, `update_tag`, `delete_tag`, `replace_document_tags`, `resolve_name_and_slug_for_admin_form`; HTTP — `GET` любой авторизованный, мутации — manager или admin |
| [`portal_document_queries.py`](portal_documents/services/portal_document_queries.py) | Read-операции: `get_document`, `ensure_user_can_read_document`, `list_documents`, `search_documents`, `list_document_history`, `document_subtree_ids` |
| [`portal_document_mutations.py`](portal_documents/services/portal_document_mutations.py) | Мутации: `create_document`, `update_document`, `write_document_history` |
| [`portal_document_diff.py`](portal_documents/services/portal_document_diff.py) | Построение diff для истории изменений (`compute_document_update_diff`, `compute_document_field_diff`) |
| [`portal_document_trash.py`](portal_documents/services/portal_document_trash.py) | Корзина: `soft_delete_document`, `restore_document`, `permanently_purge_document`, `list_trash_document_roots` |
| [`portal_document_reorder.py`](portal_documents/services/portal_document_reorder.py) | `reorder_document_among_siblings` |
| [`portal_document_duplicate.py`](portal_documents/services/portal_document_duplicate.py) | `duplicate_document_subtree` — копия поддерева с тегами, ярлыками и историей |
| [`portal_document_shortcuts.py`](portal_documents/services/portal_document_shortcuts.py) | `sync_document_shortcuts` — ярлыки `documentLink` из body, RBAC-фильтр target по автору |

Файл [`portal_document.py`](portal_documents/services/portal_document.py) — **фасад** для queries/mutations/trash/reorder/duplicate и реэкспорта операций со списком тегов из `app.services.portal_tags`. Функции, вызываемые за пределами своего файла-владельца в пакете (`write_document_history`, `replace_document_tags`) — **публичные** (без префикса `_`), даже если это внутренние хелперы, а не HTTP-контракт.

TODO (UX): пункт «Посмотреть историю изменений» на странице документа позже может переехать в общее меню разделов Атриума — см. обсуждение в задаче на документы.

### `portal_collab/services/task.py`

Разбит на два файла:

| Файл | Содержимое |
|------|------------|
| [`task.py`](portal_collab/services/task.py) | CRUD задач, проверки видимости, история (фасад над `_task_queries`, `_task_mutations`, …) |
| [`task_home.py`](portal_collab/services/task_home.py) | Функции главной: «мои» превью/счётчики; для админа — team preview/summary |

`portal_home/services/home.py` использует `task_home_svc`. Проверка «менеджер или admin» — **`app.core.permissions.is_manager_or_admin`**.

`task_home_svc.get_assignee_display_info(session, assignee_sub)` — display_name/avatar исполнителя самостоятельным запросом `portal_user_profile`, независимо от `team_assignee_load` (последний строится только для `is_portal_admin`); используется в `_build_assignee_drilldown` (home.py) — так drill-down получает имя/аватар и для менеджера, не только для админа.

Задача поддерживает **несколько исполнителей** через таблицу `portal_task_assignee` (поле `assignee_subs` в API). Основное поле `assignee_sub` (legacy, один исполнитель) сохраняется для совместимости; при создании/обновлении предпочтительно передавать `assignee_subs`.

## Механизм проверки «роль руководителя» (`portal_collab` и главная)

Единый источник: **`app.core.permissions.is_manager_or_admin(user)`** — основной отдел SSO «Аутстафф» (`gid_number == 10000`, константа `SSO_GID_OUTSTAFF`) или `portal_admin`. Группа Keycloak `outstaff` сама по себе менеджера не даёт. Используется в задачах, главной, таймшитах, специалистах и т.д. Deprecated re-export из `portal_collab/services/task.py` удалён.

Кэш `portal_user_profile` **не** хранит `gid_number` / `position`. Батч @mention (`batch_task_access_check`) поэтому не может восстановить «менеджер по отделу» для получателя — только `is_portal_admin`, автор, исполнитель, чат и source-сообщение. Расширение профиля — отдельное решение, не часть доменной логики collab.

---

## Структура тестов `tests/`

Тесты зеркалируют структуру `app/` — каждый домен имеет собственную подпапку.

```
tests/
├── conftest.py              # общие фикстуры (сессия БД, HTTP-клиент, SSO-моки)
├── helpers/portal_test_users.py  # типовые UserPublic (используется всеми доменами)
├── core/                    # конфиг, health, lifespan, docs, exception handlers, model_converter
├── auth/                    # SSO/OIDC, токены, deps_auth, groups, user_profile
├── admin/                   # SQLAdmin роуты
├── portal_navigation/
├── portal_documents/
├── portal_chat/             # conftest.py — фикстуры чата, участников, сообщений
├── portal_collab/           # задачи + договорённости
├── portal_search/
├── portal_home/
├── portal_favorites/
├── portal_finance/          # conftest.py — фикстуры контрагентов, договоров, счетов
├── portal_learning/
├── portal_time_entries/
├── portal_specialists/
├── portal_telegram/
├── portal_calendar/
└── concurrency/
```

Правило: специфичные для домена фикстуры — в `tests/<domain>/conftest.py`; общие — только в корневом `conftest.py`. Запрещено объявлять фикстуры внутри `test_*.py`.

## Техдолг (конвенции)

- [`core/config.py`](core/config.py) — ~450 строк; SSO/Jira можно вынести в mixin при следующем рефакторинге.
- Сервисный слой finance (`counterparty.py`, `contract.py`, `invoice.py`, `procurement.py`) — CRUD-функции возвращают Pydantic `*Read` напрямую вместо ORM. `portal_home/services/home.py` — не техдолг: `build_portal_home` — задокументированный агрегат-исключение (комментарий в docstring, как у `payment.get_finance_summary`/`quiz.submit_attempt`). Аналогично `portal_navigation/services/navigation.py` — `get_navigation_tree` возвращает Pydantic-дерево из двух виртуальных секций без единого ORM-объекта, с обоснованием в docstring — не техдолг.
- **Пагинация `list[T]`** для чатов, задач, избранного, уведомлений, договорённостей и части финансов — **исключение контракта SPA**, не техдолг. Переводить на `PagedResponse` только когда UI получит `total` / постраничную навигацию, по одному эндпоинту.
