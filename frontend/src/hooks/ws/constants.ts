/** Exponential backoff для WebSocket-reconnect. */
export const WS_BASE_DELAY_MS = 1000
export const WS_MAX_DELAY_MS = 30_000

/** Доля случайного разброса вокруг текущего delay (защита от thundering herd при массовом reconnect). */
export const WS_JITTER_RATIO = 0.2
