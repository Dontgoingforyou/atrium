# `portal_chat` — чаты, вложения, инбокс

## Назначение

Пакет отвечает за **чаты** (прямой диалог, групповой чат), **вложения** (MinIO) и **инбокс пользователя** (DM-уведомления). WebSocket-инфраструктура (менеджеры подключений, топик-менеджер, инбокс-менеджер, одноразовые тикеты) вынесена в [`app.infrastructure.ws`](../infrastructure/ws/).

**Сквозная политика** — [../MODULES.md](../MODULES.md). WebSocket, Redis и переподключение описаны в коде роутов и `app/infrastructure/ws/`.

---

## HTTP-эндпоинты

Роутер: [`router.py`](router.py) подключает `routes/chats.py`, `routes/messages.py`, `routes/inbox.py`, `routes/push.py` с префиксом **`/portal`**.  
WS-тикеты: [`app.infrastructure.ws.tickets`](../infrastructure/ws/tickets.py).

**OpenAPI тег:** `Чаты`

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/portal/chats` | Список чатов пользователя (пагинация `skip`/`limit`) |
| POST | `/portal/chats` | Создать чат |
| POST | `/portal/chats/direct` | Получить или создать DM |
| PATCH | `/portal/chats/{id}` | Сменить название группового чата (только создатель) |
| POST | `/portal/chats/{id}/avatar` | Загрузить аватар группы (только создатель) |
| DELETE | `/portal/chats/{id}/avatar` | Удалить аватар группы (только создатель) |
| DELETE | `/portal/chats/{id}` | Удалить чат (DM — любой участник; группа — создатель) |
| POST | `/portal/chats/{id}/members` | Пригласить участника в группу (**любой участник**) |
| DELETE | `/portal/chats/{id}/members/{user_sub}` | Исключить участника или покинуть чат (создатель не может выйти сам) |
| GET | `/portal/chats/{id}/messages` | История сообщений |
| POST | `/portal/chats/{id}/messages` | Отправить сообщение (с опциональными вложениями и `reply_to_message_id`) |
| POST | `/portal/chats/{id}/messages/forward` | Переслать сообщение из другого чата |
| POST | `/portal/chats/{id}/messages/{msg_id}/reactions` | Добавить или снять реакцию (toggle), тело `{ "emoji": "…" }` |
| GET | `/portal/chats/{id}/messages/pinned` | Закреплённые сообщения |
| POST | `/portal/chats/{id}/messages/{msg_id}/pin` | Закрепить |
| DELETE | `/portal/chats/{id}/messages/{msg_id}/pin` | Открепить |
| GET | `/portal/chats/{id}/messages/{msg_id}/readers` | Кто прочитал |
| GET | `/portal/chats/{id}/messages/{msg_id}/reactions/reactors` | Кто поставил реакцию |
| PATCH | `/portal/chats/{id}/messages/{msg_id}` | Редактировать своё сообщение |
| DELETE | `/portal/chats/{id}/messages/{msg_id}` | Удалить (`?scope=me` или `scope=all`) |
| POST | `/portal/chats/{id}/read` | Отметить чат прочитанным |
| POST | `/portal/chats/{id}/ws-ticket` | Одноразовый тикет для WS чата |
| POST | `/portal/chats/{id}/attachments` | Загрузить вложение (до отправки сообщения) |
| GET | `/portal/chats/{id}/attachments` | Галерея вложений (`PagedResponse`) |
| GET | `/portal/chats/{id}/attachments/{att_id}/download` | Presigned URL / метаданные скачивания |
| POST | `/portal/chats/{id}/attachments/{att_id}/transcribe` | Транскрибация голосового (Whisper; таймаут `OPENAI_WHISPER_TIMEOUT_SECONDS`) |
| WS | `/portal/chats/{id}/ws` | Real-time события чата (`?ticket=...`) |
| POST | `/portal/inbox/ws-ticket` | Одноразовый тикет для WS инбокса |
| WS | `/portal/inbox/ws` | События инбокса (`?ticket=...`) |
| GET | `/portal/push/vapid-public-key` | Публичный VAPID (нужна сессия) |
| POST | `/portal/push/subscribe` | Сохранить Web Push подписку |
| POST | `/portal/push/unsubscribe` | Удалить Web Push подписку |

---

## WebSocket: чат

- **Endpoint:** `WS /api/v1/portal/chats/{chat_id}/ws`
- **Авторизация:** одноразовый `ticket` из `POST .../ws-ticket`; проверяется в [`infrastructure/ws/tickets.py`](../infrastructure/ws/tickets.py) (Redis, TTL 30 с, сверка `chat_id`). Не кладите access token в query string.
- **Keepalive:** сервер шлёт `{"type":"ping"}`; клиент отвечает `{"type":"pong"}` (общий хук `useReconnectingWebSocket`).
- **Доставка:** [`infrastructure/ws/managers.py`](../infrastructure/ws/managers.py) — pub/sub через Redis; см. `backend-websocket` rule.
- **Envelope:** `{"event": "message_created" | "message_updated" | "message_deleted", "message": { ... }}`, где `message` — тот же DTO, что в REST (`PortalChatMessageRead`); поля `reply_to`, `reactions` в DTO сообщения.
- `{"event": "message_reactions_updated", "message_id": "...", "reactions": [...]}` — обновить блок реакций у сообщения без перезагрузки всей истории.
- После `POST /chats/{id}/read` публикуется `{"event": "read_state_updated"}` (без `message`) — сигнал клиенту перезапросить историю для полей `receipt` у своих сообщений.
- Групповые чаты: после смены названия — `{"event": "chat_meta_updated", "chat_id": "...", "title": "..."}`; после изменения состава — `{"event": "members_updated", "chat_id": "..."}` (без `message`).

## WebSocket: инбокс

- **Endpoint:** `WS /api/v1/portal/inbox/ws`
- **Авторизация:** одноразовый `ticket` из `POST /portal/inbox/ws-ticket`.
- **Канал Redis:** `inbox:{user_sub}` через [`infrastructure/ws/inbox_manager.py`](../infrastructure/ws/inbox_manager.py).
- **События:**

| Событие | Данные | Назначение |
|---------|--------|------------|
| `dm_inbox_update` | `{"event", "chat_id", "kind"}` + опционально `author_sub`, `preview_text`, `is_direct`, `chat_title` | Обновить список чатов; `kind` — `dm` \| `group` (для UI звука в ЛС). Доп. поля — для тостов/уведомлений без лишнего REST. |
| `portal_notification_update` | `{"event": ...}` | Новое портальное уведомление |

Публикация в инбокс — через [`services/inbox_publish.py`](services/inbox_publish.py).

---

## Групповые чаты

- **Создание:** `POST /portal/chats` с непустым `title` и списком `member_subs` (плюс создатель — участник автоматически). Участники должны быть в портальном списке пользователей.
- **DM:** `POST /portal/chats/direct` или чат с заполненным `canonical_dm_key` в модели; в списке чатов «сиротские» не-DM без `title` скрыты (см. `_queries._exclude_orphan_non_dm_chats`).
- **Роль создателя:** `created_by_sub` — менять название (`PATCH`), аватар и исключать других (`DELETE .../members/{sub}`) может только создатель. **Приглашать** (`POST .../members`) — любой участник группы. Создатель **не может** покинуть чат через `DELETE .../members/{self}` (без передачи владения или удаления чата — вне текущего MVP).
- **portal_admin без членства:** может читать чат по UUID (история, галерея, download, pinned, readers/reactors, WS-слушатель). Писать и менять состав нельзя. Список чатов и поиск — только членство.
- **Инбокс:** при новом сообщении в группе участникам уходит `dm_inbox_update` с `kind: "group"`, чтобы обновить список чатов без звука «как в DM».

---

## Присутствие пользователей (онлайн / отошёл / не в сети)

Heartbeat и Redis-хранилище реализованы в [`../services/portal_presence.py`](../services/portal_presence.py). HTTP:

- `POST /api/v1/portal/users/me/presence` — тело `PortalPresenceUpdate` (`visible`, `active`), ответ `204`;
- `GET /api/v1/portal/users` — в каждой записи поле `presence` (`online` | `away` | `offline`), см. [`../api/v1/routes/portal_users.py`](../api/v1/routes/portal_users.py).

---

## Вложения

Двухфазный flow:

1. `POST /chats/{id}/attachments` — загружает файл в MinIO, создаёт строку `portal_chat_attachment` с `message_id = NULL`.
2. `POST /chats/{id}/messages` — вместе с текстом передаются `attachment_ids`; сервис вызывает `link_attachments_to_message`, привязывая вложения к сообщению.
3. `GET .../attachments/{att_id}/download` — возвращает presigned URL (MinIO) с TTL.

**Публичный endpoint MinIO:** presigned URL должен открываться в браузере пользователя. Задайте `MINIO_PUBLIC_ENDPOINT` и `MINIO_SECURE` (HTTPS для подписи URL за nginx). Запись в бакет идёт на `MINIO_ENDPOINT` из контейнера API: для `minio:9000` без TLS укажите `MINIO_INTERNAL_SECURE=false`, иначе SDK попытается HTTPS к plain HTTP и получите `SSL WRONG_VERSION_NUMBER`. См. `app.infrastructure.storage` и `docker-compose.*.yml`.

Вложения, загруженные, но не привязанные к сообщению (`message_id IS NULL`), удаляются фоновым job [`jobs/chat_orphan_attachments_nightly.py`](../jobs/chat_orphan_attachments_nightly.py) (`CHAT_ORPHAN_ATTACHMENT_PURGE_*` в настройках) и вручную скриптом:

```
backend/scripts/purge_orphan_chat_attachments.py --min-age-hours N
```

Удаление чата целиком (`DELETE /chats/{id}`) удаляет MinIO-объекты, строки в БД (CASCADE) и эмбеддинги всех сообщений чата.

---

## Удаление сообщений и файлов (MinIO)

| Действие | Сообщение в БД | Вложения в БД / MinIO |
|----------|----------------|-----------------------|
| **Удалить у меня** (`DELETE .../messages/{id}?scope=me`) | Строка остаётся; для пользователя запись в `portal_chat_message_hidden` | Не удаляются — у других участников сообщение и файлы по-прежнему доступны |
| **Удалить у всех** (`scope=all`, только автор) | Soft delete: `deleted_for_all_at`, текст очищается | После успешного удаления объектов в MinIO удаляются строки `portal_chat_attachment` |

Если MinIO недоступен при «удалить у всех», операция не завершается (503 `storage_unavailable`), soft delete не фиксируется — можно повторить запрос.

Эмбеддинги поиска для сообщения при `scope=all` удаляются в фоне (`delete_embedding`).

**Разовая уборка** (сообщения были soft-deleted, а вложения остались до внедрения очистки):

```
backend/scripts/purge_soft_deleted_chat_attachments.py
```

---

## Карта пакета

| Путь | Содержимое |
|------|------------|
| `routes/chats.py` | REST + WS чатов (список, группа, тикет, read) |
| `routes/messages.py` | Сообщения, реакции, pin, вложения, transcribe, readers |
| `routes/inbox.py` | WS инбокса, тикет инбокса |
| `routes/push.py` | VAPID и подписки Web Push |
| `services/chat.py` | Реэкспорт публичного API из `_queries` и `_mutations` |
| `services/_queries.py` | Маппинг сообщений, SQL-фильтры, проверки доступа, читающие операции |
| `services/_mutations.py` | Создание чатов/сообщений, редактирование, удаление, отметка прочитанным |
| `services/group_chat.py` | Группа: смена названия, приглашение, исключение / выход, WS-события состава |
| `services/attachment.py` | Загрузка/скачивание вложений (MinIO), `purge_*` |
| `services/inbox_publish.py` | Публикация `dm_inbox_update` / `portal_notification_update` в Redis |
| `schemas/chat.py` | Pydantic DTO (чаты, сообщения, вложения, тикеты) |
| `comment_thread_events.py` | Константы WS-событий: `COMMENT_THREAD_UPDATED_EVENT`, `DOCUMENT_UPDATED_EVENT` |

---

## Зависимости

- **`app.infrastructure.db.models`**: `portal_chat`, `portal_document`
- **Redis** — pub/sub для WS и хранение одноразовых тикетов реализованы в [`app.infrastructure.ws`](../infrastructure/ws/) (менеджеры, тикеты, инбокс); Redis-клиент — `app.infrastructure.cache.token_cache.get_redis_client`
- **MinIO / S3** — хранение файлов (через `app.infrastructure.storage.client`)
- **Кросс-импорт с `portal_collab`**: договорённости могут ссылаться на `portal_chat`; обратно `chat` смотрит на `PortalDocument`, не тянет тяжёлый `portal_collab` в горячем пути WS

---

## Тесты

[`../../tests/portal_chat/`](../../tests/portal_chat/) (отдельный `conftest` для сценариев чата, см. [../MODULES.md](../MODULES.md)).

---

## См. также

- [../MODULES.md](../MODULES.md) — индекс модулей, список пакетов, структура `tests/`.
- [../MODULES.md](../MODULES.md) (разделы *Политика доступа* и *Rate limiting*).
