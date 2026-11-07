# Фоновые задачи API (`app/jobs/`)

Лёгкие циклы внутри процесса FastAPI: **без** Celery/ARQ. Запуск и остановка — в `lifespan` (`app/main.py`): `asyncio.Event` + `asyncio.create_task`. Паттерн и запреты — **services.mdc**, раздел «Фоновые и периодические задачи».

Одноразовые CLI-утилиты сюда не класть: они живут в `backend/scripts/` (например `purge_orphan_chat_attachments.py`).

## Каталог

| Модуль | Что делает | Расписание | Флаги Settings |
|--------|------------|------------|----------------|
| [`document_trash_nightly.py`](document_trash_nightly.py) | Безвозвратно чистит корзину документов старше TTL (строки БД, избранное, эмбеддинги). Логика — `portal_documents.services.portal_document_trash` | раз в сутки, час UTC | `DOCUMENT_TRASH_PURGE_ENABLED`, `DOCUMENT_TRASH_PURGE_HOUR_UTC` (по умолчанию 03:00) |
| [`chat_orphan_attachments_nightly.py`](chat_orphan_attachments_nightly.py) | Удаляет вложения чата без `message_id` старше порога (БД + MinIO). Логика — `portal_chat.services.attachment` | раз в сутки, час UTC | `CHAT_ORPHAN_ATTACHMENT_PURGE_ENABLED`, `CHAT_ORPHAN_ATTACHMENT_PURGE_HOUR_UTC` (04:00), `CHAT_ORPHAN_ATTACHMENT_PURGE_MIN_AGE_HOURS` (48) |
| [`calendar_reminders.py`](calendar_reminders.py) | Отправляет due-напоминания календаря (in-app / Telegram). Логика — `portal_calendar.services._reminders` | интервал, не реже 15 с | `CALENDAR_REMINDERS_ENABLED`, `CALENDAR_REMINDERS_INTERVAL_SECONDS` (60) |
| [`calendar_facts.py`](calendar_facts.py) | Читает факт календаря из Kafka и создаёт колокол. Повтор fact_id молчит. Логика — `portal_calendar.services._facts` | сразу, пока процесс жив | `CALENDAR_FACTS_ENABLED`, `CALENDAR_KAFKA_BOOTSTRAP_SERVERS` (пусто — не запускается), `CALENDAR_KAFKA_TOPIC`, `CALENDAR_KAFKA_GROUP` |
| [`task_due_reminders.py`](task_due_reminders.py) | Уведомления исполнителю за 2 дня до срока и в день просрочки. Логика — `portal_collab.services._task_due_reminders` | интервал, не реже 15 с | `TASK_DUE_REMINDERS_ENABLED`, `TASK_DUE_REMINDERS_INTERVAL_SECONDS` (60) |
| [`bench_sheets_sync.py`](bench_sheets_sync.py) | Тянет сводные листы Google Таблицы в `portal_bench_year_snapshot` (2025 frozen не затирает). Логика — `portal_bench.services._sync` | сразу и интервал ≥ 60 с | `GOOGLE_SHEETS_SYNC_ENABLED`, `GOOGLE_SHEETS_SYNC_INTERVAL_SECONDS` (60), `GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON` |

Общий хелпер окна суток — `seconds_until_next_run_utc` в `document_trash_nightly.py`; ночные циклы его переиспользуют.

## Как добавить задачу

1. Модуль с `run_*_loop(stop_event, settings)` по образцу существующих.
2. Флаг включения и параметры расписания — поля `Settings`, не константы в job.
3. Регистрация в `lifespan` (`main.py`): task на старте; на стопе — `stop_event.set()` + `await task` (cancel только по таймауту).
4. Если настройка нужна на сервере — `KEYS` / `OPTIONAL_CI_KEYS` в `deploy/ci-upload-env.sh` (см. **deploy-ci-env.mdc**).
5. Тесты цикла — `backend/tests/jobs/`.
