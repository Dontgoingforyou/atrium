import type { PortalTaskColumn, TaskStatus } from '../../types/task'
import { todayDateStr } from '../../utils/calendar/dayCalendarUtils'
import { KANBAN_OTHER_BUCKET } from '../kanban/kanbanDisplayCommon'
import { STATUS_COLOR, STATUS_LABELS } from './taskUi'

export function getTaskColumnTitle(
  status: string,
  columns: PortalTaskColumn[],
  titleOverrides?: Record<string, string>,
): string {
  if (status === KANBAN_OTHER_BUCKET) return 'Прочие (скрытые статусы)'
  const override = titleOverrides?.[status]
  if (override) return override
  const col = columns.find((c) => c.status_key === status)
  return col?.title ?? STATUS_LABELS[status as TaskStatus] ?? status
}

export function getTaskColumnColor(status: string, columns: PortalTaskColumn[]): string {
  if (status === KANBAN_OTHER_BUCKET) return 'var(--color-text-disabled)'
  const col = columns.find((c) => c.status_key === status)
  return col?.color ?? STATUS_COLOR[status as TaskStatus] ?? 'var(--color-border)'
}

export function isKpiExcludedStatus(status: string, columns: PortalTaskColumn[]): boolean {
  return columns.some((c) => c.status_key === status && c.exclude_from_kpi)
}

const CLOSED_TASK_STATUSES = new Set<string>(['done', 'cancelled'])

/** Одна пара с BE (`_task_home_common.py`); сверяет taskColumnTitlePatternsSync.test.ts. */
export const DONE_LIKE_COLUMN_TITLE_PATTERN =
  '^(готов[аоыея]*|завершен[аоыея]*|выполнен[аоыея]*|done|completed)$'
export const APPROVAL_LIKE_COLUMN_TITLE_PATTERN = String.raw`^(на\s+согласовании|согласован[аоыея]*)$`
export const CANCELLED_LIKE_COLUMN_TITLE_PATTERN = '^(отменен[аоыея]*|cancelled)$'

const DONE_LIKE_COLUMN_TITLE_RE = new RegExp(DONE_LIKE_COLUMN_TITLE_PATTERN, 'iu')
const APPROVAL_LIKE_COLUMN_TITLE_RE = new RegExp(APPROVAL_LIKE_COLUMN_TITLE_PATTERN, 'iu')
const CANCELLED_LIKE_COLUMN_TITLE_RE = new RegExp(CANCELLED_LIKE_COLUMN_TITLE_PATTERN, 'iu')

export function isClosedTaskStatus(status: string): boolean {
  return CLOSED_TASK_STATUSES.has(status)
}

export function isDoneLikeColumnTitle(title: string): boolean {
  return DONE_LIKE_COLUMN_TITLE_RE.test(title.trim())
}

export function isApprovalLikeColumnTitle(title: string): boolean {
  return APPROVAL_LIKE_COLUMN_TITLE_RE.test(title.trim())
}

export function isCancelledLikeColumnTitle(title: string): boolean {
  return CANCELLED_LIKE_COLUMN_TITLE_RE.test(title.trim())
}

export function isClosedColumnStatus(status: string, columns: PortalTaskColumn[]): boolean {
  const col = columns.find((c) => c.status_key === status)
  if (col) {
    return (
      isDoneLikeColumnTitle(col.title) ||
      isApprovalLikeColumnTitle(col.title) ||
      isCancelledLikeColumnTitle(col.title)
    )
  }
  return isClosedTaskStatus(status)
}

export function isSubtaskProgressDone(status: string, columns: PortalTaskColumn[]): boolean {
  const col = columns.find((c) => c.status_key === status)
  if (col) {
    if (isApprovalLikeColumnTitle(col.title)) return false
    return isDoneLikeColumnTitle(col.title) || isCancelledLikeColumnTitle(col.title)
  }
  return isClosedTaskStatus(status)
}

/** Success-звук только при входе в done-like, не при перестановке внутри колонки. */
export function shouldPlayTaskDoneSuccess(
  fromStatus: string,
  toStatus: string,
  columns: PortalTaskColumn[],
): boolean {
  if (fromStatus === toStatus) return false
  return !isSubtaskProgressDone(fromStatus, columns) && isSubtaskProgressDone(toStatus, columns)
}

export function dueAtToDateStr(dueAt: string): string {
  return dueAt.slice(0, 10)
}

/** Просрочена ли задача: срок раньше сегодняшней локальной календарной даты. */
export function isTaskOverdue(
  task: { status: string; due_at: string | null },
  columns: PortalTaskColumn[],
): boolean {
  if (!task.due_at) return false
  if (isKpiExcludedStatus(task.status, columns)) return false
  if (isClosedColumnStatus(task.status, columns)) return false
  return dueAtToDateStr(task.due_at) < todayDateStr()
}

export function sortedTaskColumns(columns: PortalTaskColumn[]): PortalTaskColumn[] {
  return [...columns].sort((a, b) => a.position - b.position)
}

/** Опции селекта статуса: колонки + текущий orphan-status, если его нет среди колонок. */
export function buildTaskStatusSelectOptions(
  columns: PortalTaskColumn[],
  currentStatus?: string,
): Array<{ value: string; label: string; color: string }> {
  const sorted = sortedTaskColumns(columns)
  const options = sorted.map((col) => ({
    value: col.status_key,
    label: col.title,
    color: col.color,
  }))
  if (currentStatus && !sorted.some((c) => c.status_key === currentStatus)) {
    options.push({
      value: currentStatus,
      label: getTaskColumnTitle(currentStatus, columns),
      color: getTaskColumnColor(currentStatus, columns),
    })
  }
  return options
}
