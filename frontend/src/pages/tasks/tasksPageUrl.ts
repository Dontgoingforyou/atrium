/** Парсинг query и вывод «эффективной» области задач для страницы `/tasks`. */
import { parseRepeatedSearchParam } from '../../utils/searchParamsUtils'

export const TASK_ID_FROM_URL_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function parseTaskIdFromSearchParams(params: URLSearchParams): string | null {
  const raw = params.get('task')
  if (!raw || !TASK_ID_FROM_URL_RE.test(raw)) return null
  return raw
}

export function buildTasksPageUrlWithTask(taskId: string): string {
  return `/tasks/${encodeURIComponent(taskId)}`
}

export function buildTaskShortUrl(number: number): string {
  return `/tasks/task-${number}`
}

export type TasksView = 'kanban' | 'list'
export type TaskScope = 'my' | 'team'

export function parseTasksView(viewParam: string | null): TasksView {
  return viewParam === 'list' ? 'list' : 'kanban'
}

export function parseTaskScopeFromUrl(scopeParam: string | null): TaskScope {
  return scopeParam === 'team' ? 'team' : 'my'
}

export function parseAssigneeSubs(assigneeParam: string | null): string[] {
  const a = assigneeParam
  return a ? [a] : []
}

export function parseAssigneeSubsFromSearchParams(params: URLSearchParams): string[] {
  const repeated = parseRepeatedSearchParam(params, 'assignee_sub')
  return repeated.length > 0 ? repeated : parseAssigneeSubs(params.get('assignee'))
}

export function parseTaskStatusesFromSearchParams(params: URLSearchParams): string[] {
  return parseRepeatedSearchParam(params, 'status')
}

export function parseTaskTagIdsFromSearchParams(params: URLSearchParams): string[] {
  return parseRepeatedSearchParam(params, 'tag_id')
}

const VALID_PRIORITIES = new Set(['low', 'medium', 'high'])

export function parseTaskPrioritiesFromSearchParams(params: URLSearchParams): string[] {
  return parseRepeatedSearchParam(params, 'priority').filter((p) => VALID_PRIORITIES.has(p))
}

function parseTruthySearchParam(params: URLSearchParams, key: string): boolean {
  const raw = params.get(key)
  return raw === '1' || raw === 'true'
}

export function parseOverdueOnlyFromSearchParams(params: URLSearchParams): boolean {
  return parseTruthySearchParam(params, 'overdue')
}

export function parseDoneThisMonthFromSearchParams(params: URLSearchParams): boolean {
  return parseTruthySearchParam(params, 'done_this_month')
}

export function parseNoAssigneeFromSearchParams(params: URLSearchParams): boolean {
  return parseTruthySearchParam(params, 'no_assignee')
}

export function parseKpiOpenFromSearchParams(params: URLSearchParams): boolean {
  return parseTruthySearchParam(params, 'kpi_open')
}

export function setTruthySearchParam(
  params: URLSearchParams,
  key: string,
  next: boolean,
): URLSearchParams {
  const p = new URLSearchParams(params)
  if (next) p.set(key, '1')
  else p.delete(key)
  return p
}

/** Канбан команды только с просроченными (KPI «Просрочено» на главной). */
export function buildTeamOverdueTasksPath(): string {
  return '/tasks?scope=team&overdue=1'
}

/** Канбан «мои» только с просроченными (бейдж и кольцо на главной). */
export function buildMyOverdueTasksPath(): string {
  return '/tasks?overdue=1'
}

/** Канбан команды: просроченные одного исполнителя. */
export function buildTeamAssigneeOverdueTasksPath(assigneeSub: string): string {
  const p = new URLSearchParams()
  p.set('scope', 'team')
  p.set('overdue', '1')
  p.set('assignee', assigneeSub)
  return `/tasks?${p.toString()}`
}

/** Канбан команды по исполнителю; `status` — только если есть открытые колонки. */
export function buildTeamAssigneeOpenTasksPath(
  assigneeSub: string,
  openStatusKeys: string[],
): string {
  const p = new URLSearchParams()
  p.set('scope', 'team')
  p.set('assignee', assigneeSub)
  for (const key of openStatusKeys) {
    if (key) p.append('status', key)
  }
  return `/tasks?${p.toString()}`
}

/** Канбан команды: KPI-открытые (плашка «Открытых задач»). Без status= колонок. */
export function buildTeamOpenTasksPath(): string {
  return '/tasks?scope=team&kpi_open=1'
}

/** Канбан команды: закрытые в текущем месяце UTC (плашка «Закрыто в этом месяце»). */
export function buildTeamDoneThisMonthTasksPath(): string {
  return '/tasks?scope=team&done_this_month=1'
}

/** Канбан команды: без исполнителя (плашка «Без исполнителя»). */
export function buildTeamNoAssigneeTasksPath(): string {
  return '/tasks?scope=team&no_assignee=1'
}

/** `scope=team` в URL */
export function urlIndicatesTeamScope(scopeParam: string | null): boolean {
  return scopeParam === 'team'
}

/**
 * Команда видна только при `canUseTeamScope`; иначе всегда «мои».
 * Команда активна, если в URL team или локально выбран team (при праве на команду).
 */
export function computeEffectiveTaskScope(options: {
  urlTeam: boolean
  taskScope: TaskScope
  canUseTeamScope: boolean
}): TaskScope {
  const { urlTeam, taskScope, canUseTeamScope } = options
  if (!canUseTeamScope) return 'my'
  if (urlTeam || taskScope === 'team') return 'team'
  return 'my'
}
