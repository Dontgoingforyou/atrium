# `integrations` — внешние интеграции портала

Пакет для HTTP-клиентов, нормализации данных и webhook-эндпоинтов сторонних систем.  
Доменная бизнес-логика (привязка к карточке специалиста, RBAC, запись в БД) остаётся в **`portal_specialists`**; здесь — транспорт и общие константы Jira.

Сейчас: **Jira** (BASE специалисты + write для outbound задач TASKS), **сервис профилей** (фото сотрудников и сверка почт), **Google Sheets** (снимок дашборда воронки) и **выгрузка документа «Бенч»** для сценария RAG.

| Пакет | Назначение |
|-------|------------|
| `integrations/jira/` | REST/Agile клиент, fields/normalize, webhook BASE |
| `integrations/jira/write_client.py` | create/update/transition/comment/attachment |
| `integrations/profile_directory/` | photo API (meta/get/upload/delete) и `POST /api/v1/emails/check` |
| `integrations/google_sheets/` | Sheets API v4 (httpx + JWT service account), только чтение |
| `integrations/bench/` | Read-only CSV документа «Бенч» для RAG (`GET /api/v1/integrations/bench`) |

Outbound задач портала (домен): `portal_collab/services/task_jira_*.py`, флаг `JIRA_TASKS_SYNC_ENABLED` (только prod).
Комментарий и вложение задачи уходят в TASKS после **view**-доступа (`get_task`), не `user_can_edit_task` — как у коллаба в портале; write в Jira от сервисного PAT. Менять gate — отдельное продуктовое решение.

---

## Jira — назначение

Связь карточки специалиста Atrium с issue Jira (`BASE-xxxx`):

- поиск и привязка issue по ФИО (`summary`);
- импорт полей в профиль, ссылки и колонку воронки;
- read-only секция «Jira» в модалке специалиста (поля, не продублированные в портале);
- синхронизация колонок воронки с конфигурацией доски Jira (admin);
- webhook для автообновления при изменении issue (Phase 2).

**Источник правды по направлению, городу, Telegram и CV-ссылкам — Jira.**  
В Atrium они отображаются в профиле/«Ссылки»; в секции Jira не дублируются (кроме **ФИО** — показывается явно с подписью «ФИО», а не «Тема» из локали Jira).

---

## Структура `integrations/jira/`

| Файл | Ответственность |
|------|-----------------|
| `client.py` | `JiraClient`: REST API v2 (`search`, `get_issue`), Agile API (`board/.../configuration`); Bearer PAT |
| `fields.py` | ID custom fields проекта BASE, порядок полей UI, `JIRA_NATIVE_UI_FIELD_IDS`, `JIRA_LINK_FIELDS` |
| `normalize.py` | `normalize_issue_fields`, `filter_jira_groups_for_display`, `extract_jira_field_text`, парсинг ссылок/дат |
| `jql.py` | `escape_jql_text` — экранирование для JQL |
| `routes.py` | `POST /integrations/jira/webhook` (секрет в заголовке) |

**Не дублировать** константы полей и нормализацию в `portal_specialists` — импортировать из `app.integrations.jira.*`.

---

## Доменный слой (`portal_specialists`)

| Путь | Содержимое |
|------|------------|
| `routes/jira.py` | API карточки: search, get, link, sync, unlink; sync columns |
| `services/jira_import.py` | `apply_jira_import`, link/sync/unlink, webhook handler, rate limit поиска |
| `services/jira_import_board.py` | колонка доски по статусу и ссылки последнего импорта |
| `services/jira_board_sync.py` | `sync_columns_from_jira` — upsert `portal_specialist_column` + `jira_status_id` |
| `schemas/jira.py` | `SpecialistJiraRead`, `JiraSearchHit`, … |

Подключение роутеров: [`portal_specialists/router.py`](../portal_specialists/router.py), webhook — [`api/v1/router.py`](../api/v1/router.py).

---

## HTTP API (портал)

Префикс после `/api/v1`. OpenAPI-тег: **«Специалисты — Jira»**.

| Метод | Путь | RBAC | Описание |
|-------|------|------|----------|
| GET | `/portal/specialists/jira/search?q=` | менеджер / admin | Поиск issue в проекте BASE (JQL по `summary`), rate limit Redis |
| GET | `/portal/specialists/{sub}/jira` | менеджер / admin | Состояние привязки + группы полей для UI |
| POST | `/portal/specialists/{sub}/jira/link` | менеджер / admin + write на специалиста | Привязка + импорт |
| POST | `/portal/specialists/{sub}/jira/sync` | то же | Повторный импорт из Jira |
| DELETE | `/portal/specialists/{sub}/jira/link` | то же | Отвязка (очистка `jira_*`, не трогает импортированный профиль) |
| POST | `/portal/specialists/columns/sync-from-jira` | **portal_admin** | Синхронизация колонок воронки |

Webhook (без JWT, секрет обязателен):

| Метод | Путь | Auth |
|-------|------|------|
| POST | `/integrations/jira/webhook` | заголовок `X-Jira-Webhook-Secret` |

---

## Маппинг полей Jira → Atrium

| Jira (custom field / native) | Куда в портале |
|------------------------------|----------------|
| `summary` | ФИО в секции Jira; в профиле — из SSO/`portal_user_profile` |
| `customfield_10005` (Направление) | `portal_specialist_profile.direction` |
| `customfield_10002` (Город) | `portal_specialist_profile.location` |
| `customfield_10001` (Telegram) | `portal_specialist_profile.telegram` |
| `customfield_10003` (Дата рождения) | `birthdate`, только если в портале ещё пусто |
| CV / дополнительное CV / информация с собеседования | upsert в `portal_specialist_link` |
| `status` | колонка воронки всех закреплений специалиста (`jira_status_id` → `column_key`) |
| остальные поля из `JIRA_FIELD_SPECS` | JSON-снимок `portal_specialist_profile.jira_fields` для секции Jira |

Поля из `JIRA_NATIVE_UI_FIELD_IDS` **не попадают** в снимок и в API секции Jira (кроме `summary` — показывается с портальной подписью «ФИО»).

Полный список ID — [`jira/fields.py`](jira/fields.py).

---

## Настройки (`Settings`)

См. [`core/config.py`](../core/config.py): `jira_base_url`, `jira_personal_access_token`, `jira_project_key`, `jira_board_id`, `jira_webhook_secret`, лимиты поиска и debounce webhook.

Интеграция **выключена**, если не заданы URL и PAT (`jira_enabled` → `503 ServiceUnavailableError`).

### Переменные окружения

| Переменная | Обязательность | Описание |
|------------|----------------|----------|
| `JIRA_BASE_URL` | для prod/staging | Базовый URL Jira |
| `JIRA_PERSONAL_ACCESS_TOKEN` | для prod/staging | PAT (только env, не в git) |
| `JIRA_PROJECT_KEY` | опционально | По умолчанию `BASE` |
| `JIRA_BOARD_ID` | опционально | ID доски (rapidView), по умолчанию `68` |
| `JIRA_WEBHOOK_SECRET` | для webhook | Секрет в заголовке webhook |
| `JIRA_SEARCH_RATE_LIMIT` | опционально | По умолчанию `30` запросов |
| `JIRA_SEARCH_RATE_WINDOW_SECONDS` | опционально | По умолчанию `60` с |
| `JIRA_WEBHOOK_DEBOUNCE_SECONDS` | опционально | По умолчанию `20` с |

Для staging/production ключи `JIRA_*` уже в [`deploy/ci-upload-env.sh`](../../deploy/ci-upload-env.sh). Примеры — `.env.staging.example`, `.env.production.example`.

---

## Безопасность

- **RBAC:** все эндпоинты карточки — `is_manager_or_admin`; мутации — `_require_write_access` (IDOR по `specialist_sub`).
- **Привязка 1:1:** уникальный индекс `portal_specialist_profile.jira_issue_key`; конфликт → `409`.
- **Проект:** link/sync принимают только issue из `jira_project_key`.
- **JQL:** пользовательский ввод экранируется (`escape_jql_text`).
- **Webhook:** без секрета → `403`; debounce по `issue_key` в Redis.
- **Rate limit:** поиск Jira — Redis, ключ `jira:search:{user.sub}`.
- **Ошибки Jira:** наружу — `ServiceUnavailableError` / `NotFoundError`, без тела ответа Jira.

---

## Миграции

| Ревизия | Изменения |
|---------|-----------|
| `0067_specialist_jira` | `jira_issue_key`, `jira_synced_at`, `jira_fields`; `portal_specialist_column.jira_status_id` |
| `0068_spec_profile_direction` | `portal_specialist_profile.direction` |

> **Alembic:** `version_num` ограничен `VARCHAR(32)` — id ревизий не длиннее 32 символов.

---

## Тесты

- [`tests/portal_specialists/test_jira_integration.py`](../../tests/portal_specialists/test_jira_integration.py) — normalize, API link/sync, RBAC, webhook, column sync.
- Мок Jira через `unittest.mock` / фикстуры в `tests/portal_specialists/conftest.py`.

Запуск: `make test-backend` (или точечно `pytest tests/portal_specialists/test_jira_integration.py`).

---

## Выгрузка бенча для RAG

`GET /api/v1/integrations/bench` отдаёт CSV (UTF-8 с BOM, разделитель `;`) из HTML-таблицы документа «Бенч». Это **не** дашборд `portal_bench`.

Авторизация — service token в `Authorization: Bearer`, не JWT пользователя. Id документа только из `BENCH_EXPORT_DOCUMENT_ID` (не из query). Пустой `BENCH_EXPORT_SERVICE_TOKEN` → 503.

Эндпоинт рассчитан на **production** (`https://atrium.example.com`). На staging токен не пробрасывается — ответ 503.

Пример (токен не коммитить, подставить из секретов RAG):

```bash
curl -sS -D - \
  -H 'Authorization: Bearer <BENCH_EXPORT_SERVICE_TOKEN>' \
  'https://atrium.example.com/api/v1/integrations/bench' \
  -o bench.csv
```

Ожидаемые колонки: `name;experience;stack;grade;cv;location;status`.

---

## Фронтенд

- [`frontend/src/components/specialists/SpecialistJiraSection.tsx`](../../frontend/src/components/specialists/SpecialistJiraSection.tsx) — UI секции Jira в модалке специалиста.
- API: [`frontend/src/api/specialistsApi.ts`](../../frontend/src/api/specialistsApi.ts).

---

## Связанная документация

- Доска и RBAC специалистов: [`portal_specialists/README.md`](../portal_specialists/README.md)
- Карта модулей: [`MODULES.md`](../MODULES.md)
