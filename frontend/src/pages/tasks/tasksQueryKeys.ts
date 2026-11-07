/**
 * Колоцированные query-ключи домена «задачи» (детальная карточка и список).
 *
 * Назначение: единый источник для инвалидации кэша, чтобы не плодить
 * строковые литералы вроде ['portal','task',taskId,'files'] по компонентам.
 */

import { PORTAL_TASKS_ROOT_QUERY_KEY } from '@/api/queryKeys'
import type { TaskScope } from './tasksPageUrl'

export { PORTAL_TASKS_ROOT_QUERY_KEY }

/** Личные настройки доски задач. */
export const TASK_BOARD_PREF_QUERY_KEY = ['portal', 'task-board-pref'] as const

export type TasksListQueryFilters = {
  filterStatuses: string[]
  filterTagIds: string[]
  filterPriorities: string[]
  assigneeSubs: string[]
  overdueOnly: boolean
  doneThisMonth: boolean
  noAssignee: boolean
  kpiOpenOnly: boolean
  taskScope: TaskScope
}

/** Список задач страницы `/tasks` (фильтры в ключе). */
export function tasksListQueryKey(filters: TasksListQueryFilters) {
  return [...PORTAL_TASKS_ROOT_QUERY_KEY, filters] as const
}

/** Резолв задачи по короткому номеру. */
export function taskByNumberQueryKey(number: number) {
  return ['portal', 'task-by-number', number] as const
}

/** Корень ключей одной задачи (для инвалидации префиксом: файлы/ссылки/комментарии/история). */
export const taskRootQueryKey = (taskId: string) => ['portal', 'task', taskId] as const

/** Файлы задачи. */
export const taskFilesQueryKey = (taskId: string) => ['portal', 'task', taskId, 'files'] as const

/** Ссылки задачи. */
export const taskLinksQueryKey = (taskId: string) => ['portal', 'task', taskId, 'links'] as const

/** Комментарии задачи. */
export const taskCommentsQueryKey = (taskId: string) => ['portal', 'task', taskId, 'comments'] as const

/** История изменений задачи (префикс для инвалидации всех limit). */
export const taskHistoryQueryKey = (taskId: string) => ['portal', 'task', taskId, 'history'] as const

/** История с конкретным limit (страница деталей). */
export function taskHistoryPageQueryKey(taskId: string, limit: number) {
  return [...taskHistoryQueryKey(taskId), { limit }] as const
}

/** Подзадачи одной задачи. */
export function taskSubtasksQueryKey(taskId: string) {
  return ['portal', 'task', taskId, 'subtasks'] as const
}

/** Контекстные ссылки задачи (редактор привязки документов). */
export const taskContextLinksQueryKey = (taskId: string) =>
  ['portal', 'documents', 'task-links', taskId, 'list'] as const

/** Поиск документов для привязки к задаче. */
export const taskContextLinksSearchQueryKey = (taskId: string, query: string) =>
  ['portal', 'search', 'task-document-link', taskId, query] as const

/** Короткий список задач для пикера родителя и подзадачи. */
export const taskLinkCandidatesQueryKey = (taskId: string) =>
  ['portal', 'tasks', 'link-candidates', taskId] as const

/** Поиск задач для пикера родителя или подзадачи. */
export const taskLinkCandidatesSearchQueryKey = (
  taskId: string,
  scope: 'parent' | 'subtask',
  query: string,
) => ['portal', 'search', 'task-link', taskId, scope, query] as const
