/** Навигация «назад» с карточки задачи на исходный экран. */

export const HOME_DASHBOARD_NAV_FROM = 'home-dashboard' as const
export const ANALYTICS_NAV_FROM = 'analytics' as const

export type HomeDashboardListMode = 'all' | 'open' | 'overdue'

export type HomeDashboardRestore = {
  homeAssigneeSub?: string
  homeScrollTop?: number
  homeListMode?: HomeDashboardListMode
  homeStatusKeys?: string[]
}

export type TaskBackNavState = {
  from?: typeof HOME_DASHBOARD_NAV_FROM | typeof ANALYTICS_NAV_FROM | string
  tasksReturnTo?: string
} & HomeDashboardRestore

export function homeDashboardNavState(
  restore?: HomeDashboardRestore,
): { from: typeof HOME_DASHBOARD_NAV_FROM } & HomeDashboardRestore {
  return {
    from: HOME_DASHBOARD_NAV_FROM,
    ...(restore?.homeAssigneeSub ? { homeAssigneeSub: restore.homeAssigneeSub } : {}),
    ...(typeof restore?.homeScrollTop === 'number' ? { homeScrollTop: restore.homeScrollTop } : {}),
    ...(restore?.homeListMode && restore.homeListMode !== 'all'
      ? { homeListMode: restore.homeListMode }
      : {}),
    ...(restore?.homeStatusKeys?.length ? { homeStatusKeys: restore.homeStatusKeys } : {}),
  }
}

export function analyticsNavState(): { from: typeof ANALYTICS_NAV_FROM } {
  return { from: ANALYTICS_NAV_FROM }
}

export function isHomeDashboardNav(state: unknown): boolean {
  if (typeof state !== 'object' || state === null) return false
  return (state as TaskBackNavState).from === HOME_DASHBOARD_NAV_FROM
}

export function isAnalyticsNav(state: unknown): boolean {
  if (typeof state !== 'object' || state === null) return false
  return (state as TaskBackNavState).from === ANALYTICS_NAV_FROM
}

export function getTasksReturnTo(state: unknown): string | undefined {
  if (typeof state !== 'object' || state === null) return undefined
  const raw = (state as TaskBackNavState).tasksReturnTo
  if (typeof raw !== 'string') return undefined
  if (!isSafeTasksReturnPath(raw)) return undefined
  return raw
}

/** Только `/tasks`, `/tasks?…` или `/tasks/…` — не `/taskscript`, не `..`, не `//`. */
function isSafeTasksReturnPath(raw: string): boolean {
  if (raw.includes('\\') || raw.includes('..')) return false
  if (raw === '/tasks') return true
  if (raw.startsWith('/tasks?') || raw.startsWith('/tasks/')) return true
  return false
}

export function getHomeDashboardRestore(state: unknown): HomeDashboardRestore | undefined {
  if (!isHomeDashboardNav(state)) return undefined
  const s = state as TaskBackNavState
  const out: HomeDashboardRestore = {}
  if (typeof s.homeAssigneeSub === 'string' && s.homeAssigneeSub) {
    out.homeAssigneeSub = s.homeAssigneeSub
  }
  if (typeof s.homeScrollTop === 'number' && Number.isFinite(s.homeScrollTop)) {
    out.homeScrollTop = s.homeScrollTop
  }
  if (s.homeListMode === 'open' || s.homeListMode === 'overdue' || s.homeListMode === 'all') {
    out.homeListMode = s.homeListMode
  }
  if (Array.isArray(s.homeStatusKeys) && s.homeStatusKeys.every((k) => typeof k === 'string')) {
    out.homeStatusKeys = s.homeStatusKeys
  }
  return out
}

export function pickTaskBackNavState(
  state: unknown,
): ReturnType<typeof homeDashboardNavState> | ReturnType<typeof analyticsNavState> | undefined {
  if (isHomeDashboardNav(state)) {
    return homeDashboardNavState(getHomeDashboardRestore(state))
  }
  if (isAnalyticsNav(state)) return analyticsNavState()
  return undefined
}

export function buildTaskOpenNavState(location: {
  pathname: string
  search: string
  state: unknown
}): TaskBackNavState | undefined {
  const picked = pickTaskBackNavState(location.state)
  const existingReturn = getTasksReturnTo(location.state)
  const onTasksList = location.pathname === '/tasks' || location.pathname === '/tasks/'
  const tasksReturnTo = onTasksList ? `/tasks${location.search}` : existingReturn

  if (!picked && !tasksReturnTo) return undefined
  return {
    ...(picked ?? {}),
    ...(tasksReturnTo ? { tasksReturnTo } : {}),
  }
}

export function resolveTaskBackNav(state: unknown): {
  label: string
  to: string
  state?: TaskBackNavState
} {
  const tasksReturnTo = getTasksReturnTo(state)
  if (tasksReturnTo) {
    return { label: '← Задачи', to: tasksReturnTo }
  }
  if (isHomeDashboardNav(state)) {
    return {
      label: '← Вернуться к дашборду',
      to: '/',
      state: homeDashboardNavState(getHomeDashboardRestore(state)),
    }
  }
  if (isAnalyticsNav(state)) {
    return { label: '← Вернуться в раздел аналитики', to: '/analytics/timesheets' }
  }
  return { label: '← Задачи', to: '/tasks' }
}

/** Текущий scroll основного контента layout (элемент `[data-portal-main]`). */
export function readPortalMainScrollTop(): number {
  if (typeof document === 'undefined') return 0
  const el = document.querySelector('[data-portal-main]')
  return el instanceof HTMLElement ? el.scrollTop : 0
}
