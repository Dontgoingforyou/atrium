/**
 * Персональный канбан задач: скрытая колонка пропадает вместе с карточками.
 * Агрегатор «Прочие» здесь не используется — иначе задачи «переезжают» в чужую колонку (DEV-3406).
 * Временно вернуть скрытые колонки на места — «Показать скрытые колонки».
 */
import type { PortalTask, PortalTaskColumn, TaskBoardPref } from '../../types/task'
import { buildDisplayOrderWithOtherBucket, mergeOrderedKeys } from '../kanban/kanbanDisplayCommon'

function sortByPosition(a: PortalTask, b: PortalTask): number {
  return a.position - b.position
}

/** Порядок статусов: сохранённый порядок + недостающие ключи из колонок + статусы задач без колонки. */
export function mergeColumnStatusOrder(
  columns: PortalTaskColumn[],
  pref: TaskBoardPref | null | undefined,
  taskStatuses: string[],
): string[] {
  const colKeys = columns.map((c) => c.status_key)
  const positionByKey = new Map(columns.map((c) => [c.status_key, c.position]))
  return mergeOrderedKeys(colKeys, pref?.column_order, positionByKey, taskStatuses)
}

/** Подзадача показывается отдельной карточкой в колонке своего статуса, если родитель в другой колонке (или не найден). */
function isStandaloneSubtaskInColumn(
  t: PortalTask,
  columnStatus: string,
  taskById: Map<string, PortalTask>,
): boolean {
  if (!t.parent_task_id || t.status !== columnStatus) return false
  const p = taskById.get(t.parent_task_id)
  if (!p) return true
  if (p.status === columnStatus) return false
  return true
}

export function partitionParentSubtasks(
  children: PortalTask[],
  columnStatus: string,
): { inColumn: PortalTask[]; otherColumns: PortalTask[] } {
  const inColumn: PortalTask[] = []
  const otherColumns: PortalTask[] = []
  for (const child of children) {
    if (child.status === columnStatus) inColumn.push(child)
    else otherColumns.push(child)
  }
  return { inColumn, otherColumns }
}

export function computeKanbanDisplay(
  columns: PortalTaskColumn[],
  pref: TaskBoardPref | null | undefined,
  tasks: PortalTask[],
  showAllHiddenColumns: boolean,
): {
  statusOrder: string[]
  tasksForStatus: (status: string) => PortalTask[]
  titleOverrides: Record<string, string>
  subtasksFlat: boolean
  hideSubtasks: boolean
} {
  const hideSubtasks = pref?.hide_subtasks ?? false
  const subtasksFlat = hideSubtasks ? false : (pref?.subtasks_flat ?? false)
  const taskById = new Map(tasks.map((t) => [t.id, t]))
  const topLevel = tasks.filter((t) => !t.parent_task_id)
  const taskStatuses = [...new Set(tasks.map((t) => t.status))]
  const fullOrder = mergeColumnStatusOrder(columns, pref, taskStatuses)
  const hidden = new Set(pref?.hidden_status_keys ?? [])
  const statusOrder = buildDisplayOrderWithOtherBucket(fullOrder, hidden, showAllHiddenColumns, false)

  const tasksForStatus = (status: string): PortalTask[] => {
    if (hideSubtasks) {
      return topLevel.filter((t) => t.status === status).sort(sortByPosition)
    }
    if (subtasksFlat) {
      return tasks.filter((t) => t.status === status).sort(sortByPosition)
    }
    const roots = topLevel.filter((t) => t.status === status).sort(sortByPosition)
    const standalones = tasks
      .filter((t) => isStandaloneSubtaskInColumn(t, status, taskById))
      .sort(sortByPosition)
    return [...roots, ...standalones]
  }

  return {
    statusOrder,
    tasksForStatus,
    titleOverrides: pref?.title_overrides ?? {},
    subtasksFlat,
    hideSubtasks,
  }
}
