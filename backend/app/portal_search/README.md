# `portal_search` — глобальный полнотекстовый и семантический поиск

## Назначение

Пакет даёт **глобальный поиск по порталу**:

1. **Полнотекст** (`GET /portal/search`) — объединение результатов по типам `document`, `chat_message`, `task`, `specialist`, `calendar_event` (договорённости в глобальный полнотекст не входят); сортировка по дате при нескольких типах (календарь — по `starts_at`); делегирование фильтрации прав доменным сервисам. Документы сужаются тем же `readable_document_ids_for_user`, что и `GET /portal/documents`. Мультитиповой merge берёт с каждого источника не больше `merge_cap` (≤500) строк — глубокая пагинация приблизительная.
2. **Семантический поиск** (`GET /portal/search/semantic`) — ближайшие векторы в таблице `portal_embedding` (pgvector). Без `OPENAI_API_KEY` вектор считается локально по словам; с ключом — через API эмбеддингов.
3. **Переиндексация** (`POST /portal/admin/search/reindex`) — только администраторы портала; bulk-обновление эмбеддингов в фоне.

Тексты для индексации и поля `meta` формируются в [`services/entity_text.py`](services/entity_text.py). Запись эмбеддингов при изменении сущностей выполняется из модулей документов, чата, collab и обучения; снятие — `delete_embedding` / `delete_embeddings_batch` в [`services/embedding.py`](services/embedding.py) (в т.ч. при purge документов и удалении чата). См. [политику удаления](../MODULES.md#политика-удаления-данных-сквозная).

**Сквозные политики RBAC** — [../MODULES.md](../MODULES.md); legacy-концепция «узлов навигации» (`nav_node_id`) полностью удалена, изоляция по разделам не применяется — документы и учебные материалы видны всем читателям домена.

## HTTP

Роутер: [`routes/search.py`](routes/search.py), префикс **`/portal`** (итоговые пути после `/api/v1`).

**OpenAPI тег:** `Поиск`

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/portal/search` | Полнотекст: `q`, опционально `types` (`document`, `chat_message`, `task`, `specialist`, `calendar_event`), `tag_slug`, `skip`, `limit` (≤500) |
| GET | `/portal/search/semantic` | Семантика: `q`, `types` (дефолт без agreement, как SPA; явный `agreement` допустим), `tag_slug`, `status_ids`, `skip`, `limit` (≤100). `total_found` — после фильтров в пределах `top_k`, не полный count. Rate limit — middleware. Без ключа модели порог похожести ниже (`LOCAL_SEMANTIC_MIN_SCORE`) |
| POST | `/portal/admin/search/reindex` | Фоновая переиндексация; опционально `entity_types`. Ответ `202` |

Реэкспорт: [`router.py`](router.py). Подключение в [../api/v1/router.py](../api/v1/router.py).

### Настройки (`Settings`)

Семантика и эмбеддинги (см. [`../core/config.py`](../core/config.py)): `openai_api_key`, `openai_base_url`, `embedding_model_name`, `embedding_dimension`, `embedding_batch_size`, `semantic_search_min_score` (порог 0–1), `semantic_search_top_k`, `semantic_search_rate_limit`.

**Конфиденциальность:** если задан `OPENAI_API_KEY`, строка запроса `q` уходит провайдеру эмбеддингов (`openai_base_url` или api.openai.com). Пустой ключ оставляет и запрос, и индекс на портале.

Ограничения длины и допустимые значения `types` — [`../core/portal_search_constants.py`](../core/portal_search_constants.py).

## Карта пакета

| Путь | Содержимое |
|------|------------|
| `routes/search.py` | Эндпоинты поиска и переиндексации |
| `services/search.py` | `merge_cap`, `merge_and_slice`, `semantic_search` |
| `services/search_filters.py` | Пост-фильтры семантики по тегу документа |
| `services/embedding.py` | Генерация эмбеддингов, upsert/delete, bulk reindex (реэкспорт публичного API) |
| `services/_embedding_sql.py` | Общий `UPSERT_EMBEDDING_SQL`/`vec_literal` — единый источник, не копировать в другие `_embedding_*.py` |
| `services/_embedding_chunk.py` | Чанковая выборка и upsert для bulk-reindex |
| `services/entity_text.py` | Текст и метаданные сущностей для индекса |
| `schemas/search.py` | Ответы полнотекста и семантики |

## Зависимости

- **`app.portal_documents.services.portal_document`** — поиск документов.
- **`app.portal_chat.services.chat`** — поиск сообщений (DM и групповые инбокс-чаты участника).
- **`app.portal_collab.services.agreement`**, **`task`** — поиск договорённостей и задач.
- Запись в `portal_embedding`: [`../portal_documents/routes/documents.py`](../portal_documents/routes/documents.py), [`../portal_chat/routes/messages.py`](../portal_chat/routes/messages.py), маршруты collab и [`../portal_learning/`](../portal_learning/).

Таблица БД: `portal_embedding` (pgvector).

## Безопасность (кратко)

- Полнотекст не обходит доменные правила: те же сервисы, что и списки/поиск по доменам.
- Семантика: **документы** — `readable_document_ids_for_user` (timesheet-only — только developer-docs); **обучение** — как `list_materials` (`ACTIVE` + IdP-группы; admin видит все статусы); сообщения чатов — DM и групповые инбокс-чаты, где пользователь участник (как полнотекст); **задачи** — как в списке задач (в т.ч. `portal_task_assignee`); **договорённости** — как в `search_agreements_for_user` для не-админов; **специалисты / заметки** — не-менеджеры не видят, менеджер только своих (`manager_sub`), admin — всех.
- Переиндексация — только `PortalAdminUser`; от параллельного запуска защищена Redis-lock'ом (`try_acquire_reindex_lock`), не rate limit.
- Rate limiting на уровне приложения (`ApiRateLimitMiddleware`, `middleware/rate_limit.py`, см. MODULES) применён только к `GET /portal/search/semantic` (per-token + потолок per-IP). `GET /portal/search` (полнотекст) не лимитируется отдельно — ограничение частоты для него, как и для остального публичного API без явного middleware-правила, остаётся на периметре (ingress/WAF).

## Тесты

[`../../tests/portal_search/`](../../tests/portal_search/).

## Фронтенд (UI)

- **Полнотекст:** [`../../../frontend/src/api/searchApi.ts`](../../../frontend/src/api/searchApi.ts) (`searchPortal`), шапка [`GlobalSearchField.tsx`](../../../frontend/src/components/search/GlobalSearchField.tsx), страница [`SearchPage.tsx`](../../../frontend/src/pages/SearchPage.tsx) (режим «По тексту»).
- **Семантика:** `searchPortalSemantic` → `GET /portal/search/semantic`; на `/search` переключатель «По смыслу» (`?mode=semantic`), нормализация [`normalizeSemanticHit.ts`](../../../frontend/src/utils/normalizeSemanticHit.ts).
- **Кэш React Query:** после мутаций, меняющих индекс, вызывается [`invalidatePortalSearchQueries`](../../../frontend/src/utils/invalidatePortalSearch.ts) (создание/правка/удаление сущностей, WS `message_*` в чатах).
- Фильтры `tag_slug` и `status_id` (направления) на [`SearchPage.tsx`](../../../frontend/src/pages/SearchPage.tsx); в шапке — переключатель «По тексту / По смыслу» в [`GlobalSearchField.tsx`](../../../frontend/src/components/search/GlobalSearchField.tsx).

Минимальная длина строки `q` после trim (`PORTAL_SEARCH_MIN_QUERY_LEN`): источник правды — [`../core/portal_search_constants.py`](../core/portal_search_constants.py); на фронте зеркало в [`../../../frontend/src/constants/search.ts`](../../../frontend/src/constants/search.ts), совпадение проверяет Vitest [`../../../frontend/tests/search/portalSearchMinQueryLenSync.test.ts`](../../../frontend/tests/search/portalSearchMinQueryLenSync.test.ts).

## См. также

- [../MODULES.md](../MODULES.md) — раздел `portal_search` и политика доступа.
- [../core/portal_search_constants.py](../core/portal_search_constants.py) — константы типов и длины запроса.
