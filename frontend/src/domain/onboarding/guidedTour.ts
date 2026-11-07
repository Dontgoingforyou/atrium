export type GuidedTourUserContext = {
  isPortalAdmin: boolean
  isManagerOrAdmin: boolean
  isTimesheetOnly: boolean
}

type GuidedTourCopy = string | ((ctx: GuidedTourUserContext) => string)

export type PopoverPlacementPrefer = 'top' | 'bottom' | 'left' | 'right'

export type GuidedTourStepDef = {
  id: string
  title: string
  body: string
  route?: string
  openFromSelector?: string
  selector?: string
  stageLabel?: string
  revealHover?: boolean
  /** Предпочтительная сторона плашки относительно якоря (если хватает места). */
  preferPlacement?: PopoverPlacementPrefer
  when?: (ctx: GuidedTourUserContext) => boolean
}

/** Исходное описание шага: title/body могут зависеть от роли. */
export type GuidedTourStepSource = Omit<GuidedTourStepDef, 'title' | 'body'> & {
  title: GuidedTourCopy
  body: GuidedTourCopy
}

export function tourAnchorSelector(anchorId: string): string {
  return `[data-tour="${anchorId}"]`
}

/** Короткие предлоги, союзы и частицы — не оставлять висящими в конце строки. */
const ORPHAN_WORDS = new Set([
  'и',
  'а',
  'но',
  'да',
  'по',
  'к',
  'ко',
  'в',
  'во',
  'с',
  'со',
  'у',
  'о',
  'об',
  'обо',
  'на',
  'над',
  'под',
  'из',
  'изо',
  'от',
  'ото',
  'до',
  'без',
  'для',
  'за',
  'при',
  'про',
  'через',
  'не',
  'или',
  'либо',
  'ни',
  'чтобы',
  'если',
  'же',
  'бы',
  'ли',
  'ещё',
  'еще',
])

/**
 * Вставляет неразрывные пробелы после коротких союзов/предлогов и в кавычках «По …» / «+ …».
 */
export function preventGuidedTourOrphans(text: string): string {
  const prepared = text.replace(/«По /g, '«По\u00a0').replace(/«\+ /g, '«+\u00a0')
  // Не regex с захватом пробела с обеих сторон: он съедает разделитель и пропускает следующее «и»/«над».
  const tokens = prepared.split(/(\s+)/)
  for (let i = 0; i < tokens.length - 2; i += 1) {
    if (ORPHAN_WORDS.has(tokens[i].toLowerCase()) && /^\s+$/.test(tokens[i + 1])) {
      tokens[i + 1] = '\u00a0'
    }
  }
  return tokens.join('')
}

function resolveCopy(copy: GuidedTourCopy, ctx: GuidedTourUserContext): string {
  const raw = typeof copy === 'function' ? copy(ctx) : copy
  return preventGuidedTourOrphans(raw)
}

export function filterGuidedTourSteps(
  steps: readonly GuidedTourStepSource[],
  ctx: GuidedTourUserContext,
): GuidedTourStepDef[] {
  return steps
    .filter((step) => (step.when ? step.when(ctx) : true))
    .map((step) => ({
      ...step,
      title: resolveCopy(step.title, ctx),
      body: resolveCopy(step.body, ctx),
    }))
}

export function shouldAutoStartGuidedTour(guidedTourCompleted: boolean): boolean {
  return !guidedTourCompleted
}

/** Менеджеры, администраторы и timesheet-only могут завершить весь тур сразу. */
export function canSkipEntireGuidedTour(
  ctx: Pick<GuidedTourUserContext, 'isManagerOrAdmin' | 'isTimesheetOnly'>,
): boolean {
  return ctx.isManagerOrAdmin || ctx.isTimesheetOnly
}

/** Подпись кнопки пропуска: весь тур или только текущий шаг. */
export function resolveGuidedTourSkipLabel(canSkipEntire: boolean): string {
  return canSkipEntire ? 'Пропустить обучение' : 'Пропустить шаг'
}

/** Закрыть контекстные плашки текущей страницы, не весь каталог. */
export function resolveGuidedTourHintDismissLabel(): string {
  return 'Закрыть'
}

/** Контекстные плашки после досрочного пропуска — только менеджер/админ, не AU. */
export function canShowContextualTourHints(
  ctx: Pick<GuidedTourUserContext, 'isManagerOrAdmin' | 'isTimesheetOnly'>,
): boolean {
  return ctx.isManagerOrAdmin && !ctx.isTimesheetOnly
}

export type GuidedTourPhase = 'idle' | 'welcome' | 'running' | 'done'

export type GuidedTourRuntimeState = {
  phase: GuidedTourPhase
  stepIndex: number
  steps: GuidedTourStepDef[]
}

export function advanceGuidedTourStep(state: GuidedTourRuntimeState): GuidedTourRuntimeState {
  if (state.phase !== 'running') return state
  const next = state.stepIndex + 1
  if (next >= state.steps.length) {
    return { ...state, phase: 'done', stepIndex: state.stepIndex }
  }
  return { ...state, stepIndex: next }
}

export function retreatGuidedTourStep(state: GuidedTourRuntimeState): GuidedTourRuntimeState {
  if (state.phase !== 'running') return state
  if (state.stepIndex <= 0) return state
  return { ...state, stepIndex: state.stepIndex - 1 }
}

export function skipGuidedTourStep(state: GuidedTourRuntimeState): GuidedTourRuntimeState {
  return advanceGuidedTourStep(state)
}

export type TourStepNavigationKind = 'demo-chat' | 'open-from-selector' | 'none'

/** Как открывать шаг: демо-чат не должен блокировать openFromSelector документов. */
export function resolveTourStepNavigationKind(args: {
  hasDemoChatId: boolean
  needsChatHref: boolean
  hasOpenFromSelector: boolean
}): TourStepNavigationKind {
  if (args.hasDemoChatId && args.needsChatHref) return 'demo-chat'
  if (args.hasOpenFromSelector) return 'open-from-selector'
  return 'none'
}

const DOCUMENT_TOUR_STEP_IDS = new Set([
  'document-title',
  'document-tags',
  'document-body',
  'document-comments',
])

export function stepNeedsTourDocument(step: { id?: string }): boolean {
  return Boolean(step.id && DOCUMENT_TOUR_STEP_IDS.has(step.id))
}

/** Шаги, которым нужна учебная задача (форма создания, карточка канбана, секции детали). */
const TASK_DEMO_STEP_IDS = new Set([
  'tasks-create-form',
  'tasks-create-title',
  'tasks-create-assignees',
  'tasks-create-priority',
  'tasks-create-due',
  'tasks-create-tags',
  'tasks-create-description',
  'tasks-kanban-card',
  'tasks-detail-subtasks',
  'tasks-detail-comments',
  'tasks-detail-links',
  'tasks-detail-files',
])

export function stepNeedsTourDemoTask(step: { id?: string }): boolean {
  return Boolean(step.id && TASK_DEMO_STEP_IDS.has(step.id))
}

const TASK_CREATE_FORM_STEP_IDS = new Set([
  'tasks-create-form',
  'tasks-create-title',
  'tasks-create-assignees',
  'tasks-create-priority',
  'tasks-create-due',
  'tasks-create-tags',
  'tasks-create-description',
])

/** Шаг тура на /tasks/new с prefill (обзор формы или поле). */
export function stepNeedsTourCreateFormPage(step: { id?: string }): boolean {
  return Boolean(step.id && TASK_CREATE_FORM_STEP_IDS.has(step.id))
}

const TASK_DETAIL_SECTION_STEP_IDS = new Set([
  'tasks-detail-subtasks',
  'tasks-detail-comments',
  'tasks-detail-links',
  'tasks-detail-files',
])

/** Шаг тура на карточке учебной задачи (/tasks/{id}). */
export function stepNeedsTourTaskDetailPage(step: { id?: string }): boolean {
  return Boolean(step.id && TASK_DETAIL_SECTION_STEP_IDS.has(step.id))
}

/** data-tour якорь секции карточки для шага тура. */
export function tourTaskDetailAnchorForStep(stepId: string): string | null {
  switch (stepId) {
    case 'tasks-detail-subtasks':
      return 'task-detail-subtasks'
    case 'tasks-detail-comments':
      return 'task-detail-comments'
    case 'tasks-detail-links':
      return 'task-detail-links'
    case 'tasks-detail-files':
      return 'task-detail-files'
    default:
      return null
  }
}

const SPECIALIST_DEMO_STEP_IDS = new Set([
  'specialists-kanban',
  'specialists-kanban-column-header',
  'specialists-kanban-card',
  'specialists-detail',
])

export function stepNeedsTourDemoSpecialist(step: { id?: string }): boolean {
  return Boolean(step.id && SPECIALIST_DEMO_STEP_IDS.has(step.id))
}

const EVENT_DEMO_STEP_IDS = new Set([
  'calendar-event',
  'calendar-event-detail',
  'calendar-event-edit-form',
  'calendar-grid',
  'calendar-day-cell',
])

export function stepNeedsTourDemoEvent(step: { id?: string }): boolean {
  return Boolean(step.id && EVENT_DEMO_STEP_IDS.has(step.id))
}

const TIME_ENTRY_DEMO_STEP_IDS = new Set([
  'timesheets-summary',
  'timesheets-entries',
  'timesheets-report',
])

export function stepNeedsTourDemoTimeEntry(step: { id?: string }): boolean {
  return Boolean(step.id && TIME_ENTRY_DEMO_STEP_IDS.has(step.id))
}

const DOCUMENT_DEMO_STEP_IDS = new Set([
  'nav-documents',
  'document-title',
  'document-body',
  'document-comments',
])

export function stepNeedsTourDemoDocument(step: { id?: string }): boolean {
  return Boolean(step.id && DOCUMENT_DEMO_STEP_IDS.has(step.id))
}

const CHAT_ROW_SELECTOR = tourAnchorSelector('chats-row')
const CHAT_ROW_STEP_IDS = new Set([
  'chats-row',
  'chats-thread-header',
  'chats-messages',
  'chats-emoji-easter',
  'chats-composer',
])

export function stepNeedsTourChatRow(step: {
  selector?: string
  openFromSelector?: string
  id?: string
}): boolean {
  if (step.selector === CHAT_ROW_SELECTOR || step.openFromSelector === CHAT_ROW_SELECTOR) return true
  return Boolean(step.id && CHAT_ROW_STEP_IDS.has(step.id))
}

export function stepNeedsTourChatSeed(step: {
  selector?: string
  openFromSelector?: string
  id?: string
}): boolean {
  return step.id === 'chats-sidebar' || step.id === 'chats-new' || stepNeedsTourChatRow(step)
}

export function stepNeedsTourChatHref(step: { id?: string }): boolean {
  return (
    step.id === 'chats-thread-header' ||
    step.id === 'chats-messages' ||
    step.id === 'chats-emoji-easter' ||
    step.id === 'chats-composer'
  )
}
