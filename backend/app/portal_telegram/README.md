# `portal_telegram` — привязка аккаунта и доставка уведомлений в Telegram

## Назначение

Пакет связывает **учётную запись портала** (`user_sub`) с **личным чатом пользователя в Telegram** (`telegram_chat_id`) и отправляет туда:

- события **инбокса чатов** (новое сообщение / обновление списка чатов — см. `portal_chat.services.inbox_publish`);
- **портальные уведомления** (`portal_notification`): упоминания, назначение задачи, календарь, удаление документа в корзину и т.д.

Доставка в Telegram не дублирует бизнес-правил создания уведомлений: источник истины — домены `portal_collab` / `portal_chat` / `portal_calendar`. Домены только публикуют inbox-событие (`inbox_publish`); бот подписывается на Redis и форматирует текст.

**Конфиденциальность.** Текст задач, комментариев и превью чатов уходит на серверы Telegram. Пользователь включает доставку явно (привязка личного чата). Не привязывать бота в групповых чатах — команды принимаются только в private.

**Сквозные правила** — [../MODULES.md](../MODULES.md).

---

## HTTP (портал, авторизация JWT)

Роутер [`router.py`](router.py) подключён в [../api/v1/router.py](../api/v1/router.py) с префиксом **`/telegram`**.  
Базовый путь: **`/api/v1/telegram/...`**.

**OpenAPI тег:** `Telegram`

Реализация: [`routes/telegram.py`](routes/telegram.py).

| Метод | Путь | Назначение |
|-------|------|------------|
| POST | `/telegram/bind/init` | Выдать одноразовый код привязки и deep link `https://t.me/<bot>?start=<code>` |
| GET | `/telegram/bind/status` | Привязан ли аккаунт, дата создания записи |
| DELETE | `/telegram/bind` | Отвязать Telegram (удаление строки в БД) |

Без настроенного бота (`telegram_bot_token`), без Redis или до первого успешного `getMe` для username бота — **503** через единый `AppError` (`ServiceUnavailableError`). Без JWT — **401**; timesheet-only (developer) — **403**.

---

## Webhook бота (отдельно от `/api/v1`)

При **`telegram_use_polling = false`** в [../main.py](../main.py) монтируется роутер из [`webhook.py`](webhook.py): **POST** на путь из настроек `telegram_webhook_path`. Проверка заголовка **`X-Telegram-Bot-Api-Secret-Token`** (явный `telegram_webhook_secret` или производное от токена бота).

На **staging/production** задавать **`TELEGRAM_WEBHOOK_SECRET`** явно: fallback от `bot_token` означает, что утечка токена позволяет подделать вебхук. Неверный секрет логируется с IP клиента. Неожиданная ошибка `feed_update` — **200 OK** (чтобы Telegram не ретраил прикладной сбой).

Секрет и нормализация пути — единый источник [`webhook_config.py`](webhook_config.py) (`webhook_secret`, `normalize_webhook_path`): используется и здесь для проверки входящего запроса, и в `bot/runner.py` при регистрации `setWebhook` — иначе они могут разойтись.

При **`telegram_use_polling = true`** обновления обрабатывает **long polling** (`bot/runner.py`), webhook не используется.

Полный URL webhook задаётся **`telegram_webhook_base_url` + `telegram_webhook_path`**; при старте приложения вызывается `setWebhook`.

---

## Доставка сообщений пользователю

1. **Redis:** фоновая задача [`services/listener.py`](services/listener.py) подписывается на **`inbox:*`** (`INBOX_CHANNEL_PREFIX` / `inbox_channel_pattern()` в `app.infrastructure.ws.inbox_manager`).
2. При событии **`portal_notification_update`** обязателен **`notification_id`**. Без id listener **не** берёт «последнее» уведомление (skip + warning). Текст собирается в [`services/notification_message.py`](services/notification_message.py) (автор, контекст, превью комментария / описания задачи; для mention — разбор ведущего `@имени` по профилям из [`services/notification_fetch.py`](services/notification_fetch.py)).

   Поддерживаемые типы уведомлений в `notification_message.py`:

   | Тип | Описание | Emoji |
   |-----|----------|-------|
   | `task_assigned` | Назначение исполнителем задачи | 📋 |
   | `task_due_soon` / `task_overdue` | Срок задачи: за 2 дня и после дедлайна | ⏰ |
   | `task_mention` | Упоминание в комментарии к задаче | 📌 |
   | `document_mention` | Упоминание в комментарии к документу | 📌 |
   | `document_trashed` | Документ перемещён в корзину | 🗑 |
   | `calendar_invite` / `calendar_share` / `calendar_reminder` | Приглашение, шаринг, напоминание | 📅 |
   | `calendar_event_updated` / `calendar_event_cancelled` / `calendar_share_revoked` | Изменение, отмена, отзыв доступа | 📅 |

   Deep link для задач: **`/tasks?task={uuid}`**. Прямые ссылки `/tasks/{uuid}` не используются.
3. При **`dm_inbox_update`** формируется текст в [`services/chat_inbox_telegram.py`](services/chat_inbox_telegram.py): чат, последнее **видимое** для получателя сообщение (не удалено для всех, не скрыто в `portal_chat_message_hidden`), превью текста или подпись к вложениям.
4. Кнопка «Открыть…» — только для **https** URL ([`services/telegram_url_markup.py`](services/telegram_url_markup.py)); для **http** ссылка дублируется в тексте. Событие инбокса уходит в бот сразу, без окна по времени суток.

При **`TelegramForbiddenError`** (пользователь заблокировал бота) выполняется отвязка по `chat_id` ([`services/binding.py`](services/binding.py)).

---

## Привязка через бота

- Команды бота (`/start`, `/status`, `/unlink`, `/help`) принимаются **только в личном чате** (`private`).
- Один Telegram-чат = один портальный аккаунт: `telegram_chat_id` уникален; повторная привязка того же чата снимает старую строку.
- Одноразовый код в Redis (`constants.py`: префиксы `tg_bind:` / `tg_bind_user:`, TTL). На пользователя — один живой код (реверс-ключ); подтверждение — атомарный `GETDEL`.
- Подтверждение — обработчики aiogram в [`bot/handlers/start.py`](bot/handlers/start.py) и [`bot/handlers/common.py`](bot/handlers/common.py): запись в таблицу **`portal_telegram_binding`** ([`../infrastructure/db/models/portal_telegram_binding.py`](../infrastructure/db/models/portal_telegram_binding.py)).
- При purge специалиста привязка снимается в той же транзакции (`delete_binding_for_user`).

Синглтоны бота и диспетчера: [`bot/instance.py`](bot/instance.py). Инициализация и задачи (listener, polling / setWebhook): [`bot/runner.py`](bot/runner.py).

---

## Карта пакета

| Путь | Содержимое |
|------|------------|
| `router.py` | Корневой APIRouter модуля (`/telegram`) |
| `routes/telegram.py` | REST: init/status/unbind привязки |
| `webhook.py` | Фабрика роутера входящих обновлений Telegram |
| `webhook_config.py` | Единый источник секрета и нормализации пути вебхука (используют `webhook.py` и `bot/runner.py`) |
| `schemas/telegram.py` | Pydantic: ответы привязки |
| `constants.py` | Префикс Redis-ключей кода, TTL |
| `services/binding.py` | Код привязки в Redis, подтверждение, unlink |
| `services/listener.py` | Pub/sub `inbox:*` → `send_message` |
| `services/notification_fetch.py` | Уведомление по `notification_id` + `selectinload` контекста; лейблы для `@упоминаний` |
| `services/notification_message.py` | Текст портального уведомления для TG |
| `services/chat_inbox_telegram.py` | Текст события чата для TG |
| `services/telegram_text_preview.py` | Имя из профиля, snippet текста, разбор ведущего mention, «вложения» |
| `services/telegram_url_markup.py` | Inline-кнопка https и fallback текста со ссылкой |
| `bot/instance.py` | Bot + Dispatcher |
| `bot/runner.py` | lifespan: listener, polling или setWebhook |
| `bot/handlers/start.py`, `common.py` | Команды /start и привязка |

---

## Зависимости и настройки

- **Redis** — код привязки и каналы инбокса (`app.infrastructure.cache.token_cache`, `app.infrastructure.ws.inbox_manager`).
- **SQLAlchemy:** `PortalTelegramBinding`.
- **aiogram** — бот и webhook/polling.
- **Переменные окружения / Settings:** `telegram_bot_token`, `telegram_use_polling`, `telegram_webhook_base_url`, `telegram_webhook_path`, `telegram_webhook_secret`, `telegram_bot_username` (fallback для deep link, если `getMe` недоступен), `portal_public_url` — база ссылок в уведомлениях, `telegram_proxy_url` — на production `socks5://telegram-awg:1080` (sidecar AmneziaWG, см. [../../../deploy/awg/README.md](../../../deploy/awg/README.md)).

---

## Тесты

[`../../tests/portal_telegram/`](../../tests/portal_telegram/).

---

## См. также

- [../MODULES.md](../MODULES.md) — индекс модулей.
- [../portal_chat/README.md](../portal_chat/README.md) — инбокс, события `dm_inbox_update` / `portal_notification_update`.
- Redis и WebSocket для инбокса.
