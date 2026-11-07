import {
  isClosedColumnStatus,
  isKpiExcludedStatus,
  isTaskOverdue,
  sortedTaskColumns,
} from '../../domain/tasks/taskColumns'
import type { PortalTask, PortalTaskColumn } from '../../types/task'
import type { HomeDashboardListMode } from '../tasks/taskBackNav'

export function isKpiActiveOpenTask(task: PortalTask, columns: PortalTaskColumn[]): boolean {
  if (isKpiExcludedStatus(task.status, columns)) return false
  if (isClosedColumnStatus(task.status, columns)) return false
  return true
}

export function kpiActiveOpenStatusKeys(columns: PortalTaskColumn[]): string[] {
  return sortedTaskColumns(columns)
    .filter((col) => {
      if (isKpiExcludedStatus(col.status_key, columns)) return false
      if (isClosedColumnStatus(col.status_key, columns)) return false
      return true
    })
    .map((col) => col.status_key)
}

export function homeOnTrackCount(openCount: number, overdueCount: number): number {
  return Math.max(0, openCount - overdueCount)
}

export function hiddenCount(total: number, visibleLimit: number): number {
  return Math.max(0, total - visibleLimit)
}

export function visibleAssigneeLoadRows<T>(rows: T[], limit: number, expanded: boolean): T[] {
  if (expanded) return rows
  return rows.slice(0, limit)
}

export function extraAssigneeLoadRows<T>(rows: T[], limit: number): T[] {
  return rows.slice(limit)
}

export function filterHomeAssigneeTasks(
  rows: PortalTask[],
  columns: PortalTaskColumn[],
  listMode: HomeDashboardListMode,
): PortalTask[] {
  if (listMode === 'overdue') {
    return rows.filter((t) => isTaskOverdue(t, columns))
  }
  if (listMode === 'open') {
    return rows.filter((t) => isKpiActiveOpenTask(t, columns) && !isTaskOverdue(t, columns))
  }
  return rows
}

export function overduePreviewTasks(preview: PortalTask[], columns: PortalTaskColumn[]): PortalTask[] {
  return preview.filter((t) => isTaskOverdue(t, columns))
}
