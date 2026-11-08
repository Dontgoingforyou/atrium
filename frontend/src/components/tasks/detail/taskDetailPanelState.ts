export type TaskDetailPanelId =
  | 'links' | 'subtasks' | 'history' | 'comments' | 'extLinks' | 'files'
  | 'modal-links' | 'modal-subtasks' | 'modal-history' | 'modal-comments' | 'modal-ext-links' | 'modal-files'
  | 'spec-profile' | 'spec-links' | 'spec-jira' | 'spec-comments' | 'spec-managers'
  | 'document-comments'

const PANEL_STORAGE = 'atrium.taskDetail.panelOpen.v1'

const DEFAULT_COLLAPSED_PANELS: ReadonlySet<TaskDetailPanelId> = new Set([
  'modal-history',
  'history',
])

/**
 * Панели, открытость которых задаётся только `contentCount` (пустые свёрнуты, непустые раскрыты).
 */
const CONTENT_DRIVEN_PANELS: ReadonlySet<TaskDetailPanelId> = new Set([
  'links',
  'subtasks',
  'comments',
  'extLinks',
  'files',
  'modal-links',
  'modal-subtasks',
  'modal-comments',
  'modal-ext-links',
  'modal-files',
  'spec-links',
  'spec-jira',
  'spec-comments',
  'spec-managers',
])

/** Панели без contentCount — всегда раскрыты по умолчанию (пока пользователь не свернул). */
const ALWAYS_OPEN_PANELS: ReadonlySet<TaskDetailPanelId> = new Set([
  'spec-profile',
  'document-comments',
])

export function isContentDrivenPanel(panelId: TaskDetailPanelId): boolean {
  return CONTENT_DRIVEN_PANELS.has(panelId)
}

/** Явный выбор пользователя для панели (localStorage), если он когда-либо переключал её. */
export function readStoredOpen(panelId: TaskDetailPanelId): boolean | undefined {
  if (CONTENT_DRIVEN_PANELS.has(panelId) || DEFAULT_COLLAPSED_PANELS.has(panelId)) {
    return undefined
  }
  try {
    const raw = localStorage.getItem(PANEL_STORAGE)
    if (!raw) return undefined
    const m = JSON.parse(raw) as Partial<Record<TaskDetailPanelId, boolean>>
    if (m && typeof m === 'object' && Object.hasOwn(m, panelId)) {
      return Boolean(m[panelId])
    }
  } catch {
    // ignore
  }
  return undefined
}

export function readInitialOpen(panelId: TaskDetailPanelId): boolean {
  const stored = readStoredOpen(panelId)
  if (stored !== undefined) return stored
  if (ALWAYS_OPEN_PANELS.has(panelId)) return true
  return false
}

/** Начальное состояние панели с учётом contentCount (если передан на первом рендере). */
export function computeInitialOpen(panelId: TaskDetailPanelId, contentCount?: number): boolean {
  if (DEFAULT_COLLAPSED_PANELS.has(panelId)) return false
  if (CONTENT_DRIVEN_PANELS.has(panelId)) {
    return contentCount !== undefined ? contentCount > 0 : false
  }
  const stored = readStoredOpen(panelId)
  if (stored !== undefined) return stored
  if (ALWAYS_OPEN_PANELS.has(panelId)) return true
  return false
}

export function persistOpen(panelId: TaskDetailPanelId, open: boolean) {
  if (CONTENT_DRIVEN_PANELS.has(panelId) || DEFAULT_COLLAPSED_PANELS.has(panelId)) {
    return
  }
  try {
    const raw = localStorage.getItem(PANEL_STORAGE)
    const m: Partial<Record<TaskDetailPanelId, boolean>> = raw
      ? (JSON.parse(raw) as Partial<Record<TaskDetailPanelId, boolean>>)
      : {}
    m[panelId] = open
    localStorage.setItem(PANEL_STORAGE, JSON.stringify(m))
  } catch {
    // ignore
  }
}

/**
 * Авто-состояние после загрузки contentCount.
 * Content-driven и history всегда возвращают явное значение (storage не перекрывает).
 * Для остальных — `undefined`, если есть сохранённый выбор пользователя.
 */
export function resolveAutoOpenState(panelId: TaskDetailPanelId, contentCount: number): boolean | undefined {
  if (DEFAULT_COLLAPSED_PANELS.has(panelId)) return false
  if (CONTENT_DRIVEN_PANELS.has(panelId)) return contentCount > 0
  if (readStoredOpen(panelId) !== undefined) return undefined
  if (ALWAYS_OPEN_PANELS.has(panelId)) return true
  return contentCount > 0
}
