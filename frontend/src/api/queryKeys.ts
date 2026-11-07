/**
 * Централизованные ключи React Query.
 *
 * Импортировать из этого файла вместо хардкода строковых массивов в компонентах.
 * Это гарантирует согласованную инвалидацию кэша по всему приложению.
 */

import { queryOptions, type QueryClient } from '@tanstack/react-query'
import { listPortalUsers, type PortalUser } from './usersApi'

/** Список пользователей портала (публичные профили). */
export const PORTAL_USERS_QUERY_KEY = ['portal', 'users'] as const

/** Список всех чатов текущего пользователя. */
export const PORTAL_CHATS_ALL_QUERY_KEY = ['portal', 'chats', 'all'] as const

/** Сообщения одного чата (префикс; /chats использует суффикс wide/default для deep-link). */
export function portalChatMessagesQueryKey(chatId: string) {
  return ['portal', 'messages', chatId] as const
}

/** Закреплённые сообщения чата (страница, виджет, бар, мутации). */
export function portalPinnedMessagesQueryKey(chatId: string) {
  return ['portal', 'pinned-messages', chatId] as const
}

/** Корень ключей задач (для инвалидации префиксом: списки, доски, детали). */
export const PORTAL_TASKS_ROOT_QUERY_KEY = ['portal', 'tasks'] as const

/** Корень ключей уведомлений (для инвалидации префиксом: list + unread-count). */
export const PORTAL_NOTIFICATIONS_ROOT_QUERY_KEY = ['portal', 'notifications'] as const

/** Список уведомлений текущего пользователя (колокол). */
export const PORTAL_NOTIFICATIONS_LIST_QUERY_KEY = ['portal', 'notifications', 'list'] as const

/** Счётчик непрочитанных уведомлений (колокол). */
export const PORTAL_NOTIFICATIONS_UNREAD_COUNT_QUERY_KEY = [
  'portal',
  'notifications',
  'unread-count',
] as const

/** Дерево навигации портала (кросс-доменное: используется страницами, навигацией, WS, онбордингом, корзиной). */
export const PORTAL_NAVIGATION_TREE_QUERY_KEY = ['portal', 'navigation-tree'] as const

/** Статус привязки Telegram текущего пользователя (страница аккаунта). */
export const TELEGRAM_BIND_STATUS_QUERY_KEY = ['telegram', 'bind-status'] as const

/** Список всех тегов портала (кросс-доменный: документы, задачи, поиск). */
export const PORTAL_TAGS_QUERY_KEY = ['portal', 'tags'] as const

/** Префикс всех ключей поиска (шапка + страница) — для инвалидации префиксом. */
export const PORTAL_SEARCH_QUERY_KEY_PREFIX = ['portal', 'search'] as const

/** Главная страница портала (KPI, превью задач, менеджерский блок, favorites). */
export const PORTAL_HOME_QUERY_KEY = ['portal', 'home'] as const

/** Колонки канбана задач (кросс-доменные: tasks, home, analytics, subtasks). */
export const PORTAL_TASK_COLUMNS_QUERY_KEY = ['portal', 'task-columns'] as const

/** Сводка по трудозатратам за период (кросс-доменная: analytics + timesheets). */
export function timeEntriesSummaryQueryKey(params: {
  dateFrom?: string
  dateTo?: string
  userSub?: string
  taskId?: string
}) {
  return ['portal', 'time-entries-summary', params] as const
}

/** Отчёт по трудозатратам (бакеты неделя/месяц) — кросс-доменный: analytics + timesheets. */
export function timeEntriesReportQueryKey(params: {
  groupBy?: 'week' | 'month'
  dateFrom?: string
  dateTo?: string
  userSub?: string
  taskId?: string
}) {
  return ['portal', 'time-entries-report', params] as const
}

/** Список записей трудозатрат за период — кросс-доменный (analytics/timesheets). */
export function timeEntriesQueryKey(params: {
  dateFrom?: string
  dateTo?: string
  userSub?: string
  month?: string
  taskId?: string
}) {
  return ['portal', 'time-entries', params] as const
}

/** Корень ключей трудозатрат — для инвалидации префиксом (list + summary + report). */
export const PORTAL_TIME_ENTRIES_ROOT_QUERY_KEY = ['portal', 'time-entries'] as const

/** Префикс ключей сводки по трудозатратам — для инвалидации префиксом (все периоды). */
export const PORTAL_TIME_ENTRIES_SUMMARY_ROOT_QUERY_KEY = ['portal', 'time-entries-summary'] as const

/** Префикс ключей отчёта по трудозатратам — для инвалидации префиксом. */
export const PORTAL_TIME_ENTRIES_REPORT_ROOT_QUERY_KEY = ['portal', 'time-entries-report'] as const

/** Список специалистов с месячной сводкой трудозатрат (менеджерский вид таймшитов). */
export function timeEntriesSpecialistsQueryKey(params: { month: string }) {
  return ['portal', 'time-entries-specialists', params] as const
}

/** Список избранного текущего пользователя (документы-звёзды). */
export const PORTAL_FAVORITES_QUERY_KEY = ['portal', 'favorites'] as const

/** Кто прочитал сообщение. */
export function messageReadersQueryKey(chatId: string, messageId: string) {
  return ['portal', 'message-readers', chatId, messageId] as const
}

/** Кто поставил реакцию (по emoji). */
export function messageReactorsQueryKey(chatId: string, messageId: string, emoji: string) {
  return ['portal', 'message-reactors', chatId, messageId, emoji] as const
}

/** Совпадает с `Settings.user_photo_url_ttl_seconds` (мс). */
export const PORTAL_USERS_STALE_TIME_MS = 60 * 60 * 1000

/**
 * Общие queryOptions для списка пользователей портала.
 *
 * staleTime = TTL HMAC photo URL: после истечения подписи proxy отдаёт 401.
 * refetchOnWindowFocus = false: список редко меняется между фокусами.
 */
export const portalUsersQueryOptions = (limit = 500) =>
  queryOptions({
    queryKey: PORTAL_USERS_QUERY_KEY,
    queryFn: () => listPortalUsers({ limit }),
    staleTime: PORTAL_USERS_STALE_TIME_MS,
    gcTime: PORTAL_USERS_STALE_TIME_MS + 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  })

/** Точечное обновление профиля в кэше без полного рефетча 500 пользователей. */
export function patchPortalUserInCache(
  qc: QueryClient,
  sub: string,
  patch: Partial<PortalUser>,
): void {
  qc.setQueryData<PortalUser[]>(PORTAL_USERS_QUERY_KEY, (prev) =>
    prev?.map((u) => (u.sub === sub ? { ...u, ...patch } : u)),
  )
}
