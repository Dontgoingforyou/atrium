"""Константы WebSocket-инфраструктуры."""

from __future__ import annotations

# Интервал между ping-сообщениями сервера (секунды).
# Используется в ws_keepalive для обнаружения «зависших» соединений.
WS_PING_INTERVAL: int = 30

# Сколько секунд ждать pong-ответа клиента после ping.
# Если за это время ответа нет — соединение считается мёртвым и закрывается.
WS_PING_TIMEOUT: int = 10

# Тип ping-сообщения (JSON). Клиент должен ответить {"type": "pong"}.
WS_PING_MESSAGE: str = '{"type":"ping"}'
WS_PONG_TYPE: str = "pong"
