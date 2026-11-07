/** Интервал подстраховки списка DM при потере WS */
export const CHATS_DM_SAFETY_REFETCH_MS = 8 * 60_000

export const CHAT_ID_FROM_URL_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/** Длительность анимации исчезновения строки сообщения при удалении (мс). */
export const MESSAGE_DELETE_EXIT_MS = 320
