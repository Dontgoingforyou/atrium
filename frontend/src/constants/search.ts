import type { PortalSearchMode, SearchEntityType } from '../types/search'

/** Должно совпадать с `PORTAL_SEARCH_MIN_QUERY_LEN` в бэкенде; см. тест `tests/search/portalSearchMinQueryLenSync.test.ts`. */
export const PORTAL_SEARCH_MIN_QUERY_LEN = 2

export const GLOBAL_SEARCH_PREVIEW_LIMIT = 8

/** Размер страницы семантического поиска, отправляется как `limit` на бэкенд
 *  (GET /portal/search/semantic, max 100). Не зеркалирует бэкенд-дефолт —
 *  фронтенд шлёт явное значение; sync-теста нет, т.к. значение контролируется SPA. */
export const SEMANTIC_SEARCH_PAGE_SIZE = 20

export const SEARCH_ENTITY_LABELS: Record<SearchEntityType, string> = {
  document: 'Документ',
  chat_message: 'Сообщение',
  task: 'Задача',
  specialist: 'Специалист',
  learning_material: 'Обучение',
  specialist_note: 'Заметка о специалисте',
  calendar_event: 'Событие',
  agreement: 'Договорённость',
}

export const SEARCH_PAGE_ENTITY_TYPES: SearchEntityType[] = [
  'document',
  'chat_message',
  'task',
  'specialist',
  'calendar_event',
]

/**
 * Типы семантического поиска, отправляемые SPA на бэкенд.
 *
 * Соответствует `PORTAL_SEMANTIC_DEFAULT_TYPES` в `backend/app/core/portal_search_constants.py`.
 * `agreement` осознанно исключён (как и бэкенд-дефолт) — договорённости не входят
 * в семантический поиск по умолчанию, доступны только по явному `types=agreement`.
 */
export const SEMANTIC_SEARCH_ENTITY_TYPES: SearchEntityType[] = [
  'document',
  'chat_message',
  'task',
  'learning_material',
  'specialist',
  'specialist_note',
  'calendar_event',
]

export const PORTAL_SEARCH_MODE_LABELS: Record<PortalSearchMode, string> = {
  fulltext: 'По тексту',
  semantic: 'По смыслу',
}
