import {
  stepNeedsTourDocument,
  stepNeedsTourTaskDetailPage,
  type GuidedTourPhase,
  type GuidedTourStepDef,
} from './guidedTour'

export type GuidedTourPageId =
  | 'home'
  | 'search'
  | 'tasks-kanban'
  | 'tasks-create'
  | 'tasks-detail'
  | 'specialists'
  | 'chats'
  | 'calendar'
  | 'tags'
  | 'analytics-timesheets'
  | 'analytics-reports'
  | 'trash'
  | 'document'
  | 'account'

export const ANALYTICS_TIMESHEETS_PATH = '/analytics/timesheets'

export function canonicalTourPathname(pathname: string): string {
  return pathname === '/analytics' ? ANALYTICS_TIMESHEETS_PATH : pathname
}

const ROUTE_PATH_TO_PAGE: Record<string, GuidedTourPageId> = {
  '/': 'home',
  '/search': 'search',
  '/tasks': 'tasks-kanban',
  '/tasks/new': 'tasks-create',
  '/specialists': 'specialists',
  '/chats': 'chats',
  '/calendar': 'calendar',
  '/tags': 'tags',
  [ANALYTICS_TIMESHEETS_PATH]: 'analytics-timesheets',
  '/analytics/reports': 'analytics-reports',
  '/p/trash': 'trash',
  '/account': 'account',
}

function routePath(route: string | undefined): string | null {
  if (!route) return null
  const path = route.split('?')[0] || null
  return path ? canonicalTourPathname(path) : null
}

export function resolveTourPageId(step: Pick<GuidedTourStepDef, 'id' | 'route'>): GuidedTourPageId | null {
  if (stepNeedsTourTaskDetailPage(step)) return 'tasks-detail'
  if (stepNeedsTourDocument(step)) return 'document'
  const path = routePath(step.route)
  if (!path) return null
  return ROUTE_PATH_TO_PAGE[path] ?? null
}

export function resolveLocationTourPageId(pathname: string, search: string): GuidedTourPageId | null {
  void search
  if (pathname === '/tasks/new') return 'tasks-create'
  if (pathname.startsWith('/tasks/') && pathname !== '/tasks/new') return 'tasks-detail'
  if (pathname.startsWith('/documents/')) return 'document'
  if (/^\/p\/[^/]+\/documents\//.test(pathname)) return 'document'
  return ROUTE_PATH_TO_PAGE[canonicalTourPathname(pathname)] ?? null
}

export function unseenStepsForPage(
  steps: readonly GuidedTourStepDef[],
  seenIds: ReadonlySet<string>,
  pageId: GuidedTourPageId,
): GuidedTourStepDef[] {
  return steps.filter((item) => resolveTourPageId(item) === pageId && !seenIds.has(item.id))
}

export function seenStepIdsAfterLinearSkip(
  steps: readonly Pick<GuidedTourStepDef, 'id'>[],
  phase: GuidedTourPhase,
  stepIndex: number,
): string[] {
  if (phase !== 'running') return []
  return steps.slice(0, stepIndex + 1).map((item) => item.id)
}

export function seenStepIdsAfterLinearComplete(steps: readonly Pick<GuidedTourStepDef, 'id'>[]): string[] {
  return steps.map((item) => item.id)
}

export function tourLocationKey(pathname: string, search: string): string {
  if (!search) return pathname
  return `${pathname}${search.startsWith('?') ? search : `?${search}`}`
}

export function shouldClearHintFreeze(
  frozenLocationKeys: readonly string[],
  locationKey: string,
): boolean {
  return frozenLocationKeys.length > 0 && !frozenLocationKeys.includes(locationKey)
}

export function shouldStartContextualHint(args: {
  tourCompleted: boolean
  canShowHints: boolean
  phase: GuidedTourPhase
  locationKey: string
  frozenLocationKeys: readonly string[]
  unseenCount: number
}): boolean {
  if (!args.tourCompleted || !args.canShowHints) return false
  if (args.phase !== 'idle') return false
  if (args.frozenLocationKeys.includes(args.locationKey)) return false
  return args.unseenCount > 0
}
