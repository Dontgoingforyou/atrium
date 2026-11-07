import { PORTAL_HOME_QUERY_KEY } from '../../api/queryKeys'
import type { HomeDashboardListMode } from '../tasks/taskBackNav'

/** Префикс ключей главной — тот же, что PORTAL_HOME_QUERY_KEY, для инвалидации префиксом. */
export const HOME_ROOT_QUERY_KEY = PORTAL_HOME_QUERY_KEY

/** Лимит listTasks в drill-down (бэкенд le=500). */
export const HOME_ASSIGNEE_TASKS_LIMIT = 200

/** Сколько плиток нагрузки показываем; бэкенд отдаёт до 20. */
export const HOME_ASSIGNEE_TILE_LIMIT = 4

export const homeQueryKeys = {
  root: HOME_ROOT_QUERY_KEY,
  assignee: (sub: string) => [...HOME_ROOT_QUERY_KEY, 'assignee', sub] as const,
  assigneeTasks: (assigneeSub: string, statusKeys: string[], listMode: HomeDashboardListMode) =>
    [...HOME_ROOT_QUERY_KEY, 'assignee-tasks', assigneeSub, statusKeys, listMode] as const,
}
