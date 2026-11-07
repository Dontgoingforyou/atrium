from __future__ import annotations

TG_BIND_REDIS_PREFIX = "tg_bind:"
TG_BIND_USER_REDIS_PREFIX = "tg_bind_user:"
TG_BIND_CODE_TTL_SECONDS = 600

# Не слать push в Telegram при большом хвосте непрочитанных (ЛС).
TELEGRAM_CHAT_INBOX_SUPPRESS_UNREAD_THRESHOLD = 3

# getUpdates timeout < HTTP-таймаут сессии, иначе long poll даёт Request timeout за SOCKS.
TELEGRAM_POLLING_TIMEOUT_SECONDS = 25
TELEGRAM_SESSION_TIMEOUT_SECONDS = 90.0
